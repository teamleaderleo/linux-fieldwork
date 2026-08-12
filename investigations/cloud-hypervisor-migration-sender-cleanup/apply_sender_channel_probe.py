#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/migration/transport.rs")
text = path.read_text()
marker = "full_queue_loses_cleanup_disconnect_while_sender_stays_alive"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = "#[cfg(test)]\nmod tests {"
if text.count(anchor) != 1:
    raise SystemExit(f"expected exactly one existing transport test module anchor in {path}")

probe = r'''#[cfg(test)]
mod sender_channel_liveness_tests {
    use std::sync::Arc;
    use std::sync::atomic::AtomicBool;
    use std::sync::mpsc::{RecvTimeoutError, TrySendError, channel, sync_channel};
    use std::thread;
    use std::time::Duration;

    use vm_migration::MigratableError;
    use vm_migration::protocol::MemoryRangeTable;

    use super::{
        GuestAddress, GuestMemoryAtomic, GuestMemoryMmap, SendAdditionalConnections,
        SendMemoryThreadMessage,
    };

    #[test]
    fn full_queue_loses_cleanup_disconnect_while_sender_stays_alive() {
        let (message_tx, message_rx) = sync_channel(1);
        message_tx
            .send(SendMemoryThreadMessage::Memory(MemoryRangeTable::default()))
            .unwrap();

        let disconnect = message_tx.try_send(SendMemoryThreadMessage::Disconnect);
        assert!(matches!(
            disconnect,
            Err(TrySendError::Full(SendMemoryThreadMessage::Disconnect))
        ));

        assert!(matches!(
            message_rx.recv().unwrap(),
            SendMemoryThreadMessage::Memory(_)
        ));
        assert!(matches!(
            message_rx.recv_timeout(Duration::from_millis(20)),
            Err(RecvTimeoutError::Timeout)
        ));

        drop(message_tx);
        message_rx.recv().unwrap_err();
    }

    #[test]
    fn wait_for_pending_data_observes_worker_error_before_blocking_gate_send() {
        let guest_memory = GuestMemoryAtomic::new(
            GuestMemoryMmap::from_ranges(&[(GuestAddress(0), 0x1000)]).unwrap(),
        );
        let (message_tx, message_rx) = sync_channel(1);
        message_tx
            .send(SendMemoryThreadMessage::Memory(MemoryRangeTable::default()))
            .unwrap();
        let (_notify_tx, notify_rx) = channel();
        let worker_error = Arc::new(AtomicBool::new(true));
        let worker = thread::spawn(|| -> Result<(), MigratableError> { Ok(()) });

        let mut connections = SendAdditionalConnections {
            guest_memory,
            threads: vec![worker],
            message_tx,
            worker_error,
            notify_rx,
        };

        // Keep the receiver alive but deliberately unable to drain the full queue.
        let _message_rx = message_rx;
        let _ = connections.wait_for_pending_data();
    }
}

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
