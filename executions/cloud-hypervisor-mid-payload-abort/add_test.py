from pathlib import Path
import sys

p = Path(sys.argv[1])
text = p.read_text()
marker = 'fn test_memory_worker_abort_interrupts_stalled_payload()'
if marker in text:
    raise SystemExit('test already present')
text += r'''

#[cfg(test)]
mod fieldwork_liveness_tests {
    use std::io::Write;
    use std::os::unix::net::UnixStream;
    use std::sync::mpsc;
    use std::thread;
    use std::time::Duration;

    use vm_memory::{GuestAddress, GuestMemoryAtomic};
    use vm_migration::protocol::{MemoryRange, MemoryRangeTable, Request};
    use vmm_sys_util::eventfd::EventFd;

    use super::{ReceiveAdditionalConnections, SocketStream};
    use crate::GuestMemoryMmap;

    #[test]
    fn test_memory_worker_abort_interrupts_stalled_payload() {
        let memory = GuestMemoryMmap::from_ranges(&[(GuestAddress(0), 0x1000)]).unwrap();
        let guest_memory = GuestMemoryAtomic::new(memory);
        let kill_evt = EventFd::new(0).unwrap();
        let worker_kill_evt = kill_evt.try_clone().unwrap();
        let (mut sender, receiver) = UnixStream::pair().unwrap();
        let (done_tx, done_rx) = mpsc::channel();

        thread::spawn(move || {
            let mut socket = SocketStream::Unix(receiver);
            let result = ReceiveAdditionalConnections::worker_receive_memory(
                &mut socket,
                &worker_kill_evt,
                &guest_memory,
            );
            let _ = done_tx.send(result);
        });

        let mut ranges = MemoryRangeTable::default();
        ranges.push(MemoryRange {
            gpa: 0,
            length: 0x1000,
        });
        Request::memory(ranges.length())
            .write_to(&mut sender)
            .unwrap();
        ranges.write_to(&mut sender).unwrap();
        sender.write_all(&[0x5a]).unwrap();

        thread::sleep(Duration::from_millis(100));
        kill_evt.write(1).unwrap();

        let result = done_rx
            .recv_timeout(Duration::from_millis(750))
            .expect("memory worker did not stop after kill event while payload was stalled");
        assert!(result.is_ok(), "memory worker returned {result:?}");
    }
}
'''
p.write_text(text)
