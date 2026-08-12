#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/migration/transport.rs")
text = path.read_text()
marker = "wait_for_pending_data_worker_error_does_not_block_gate_enqueue"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = "#[cfg(test)]\nmod tests {"
if text.count(anchor) != 1:
    raise SystemExit(f"expected exactly one transport test-module anchor in {path}")

probe = r'''#[cfg(test)]
mod sender_gate_liveness_tests {
    use std::sync::Arc;
    use std::sync::atomic::AtomicBool;
    use std::sync::mpsc::{channel, sync_channel};
    use std::thread;
    use std::time::Duration;

    use anyhow::anyhow;
    use vm_migration::MigratableError;
    use vm_migration::protocol::MemoryRangeTable;

    use super::{
        GuestAddress, GuestMemoryAtomic, GuestMemoryMmap, SendAdditionalConnections,
        SendMemoryThreadMessage, SendMemoryThreadNotify,
    };

    fn guest_memory() -> GuestMemoryAtomic<GuestMemoryMmap> {
        GuestMemoryAtomic::new(
            GuestMemoryMmap::from_ranges(&[(GuestAddress(0), 0x1000)]).unwrap(),
        )
    }

    #[test]
    fn wait_for_pending_data_full_queue_healthy_worker_completes() {
        let (message_tx, message_rx) = sync_channel(1);
        message_tx
            .send(SendMemoryThreadMessage::Memory(MemoryRangeTable::default()))
            .unwrap();
        let (notify_tx, notify_rx) = channel();
        let worker = thread::spawn(move || -> Result<(), MigratableError> {
            thread::sleep(Duration::from_millis(20));
            assert!(matches!(
                message_rx.recv().unwrap(),
                SendMemoryThreadMessage::Memory(_)
            ));
            match message_rx.recv().unwrap() {
                SendMemoryThreadMessage::Gate(gate) => {
                    notify_tx.send(SendMemoryThreadNotify::Gate).unwrap();
                    gate.wait();
                }
                _ => panic!("expected Gate after queued Memory"),
            }
            Ok(())
        });

        let mut connections = SendAdditionalConnections {
            guest_memory: guest_memory(),
            threads: vec![worker],
            message_tx,
            worker_error: Arc::new(AtomicBool::new(false)),
            notify_rx,
        };

        connections.wait_for_pending_data().unwrap();
        connections.cleanup().unwrap();
    }

    #[test]
    fn wait_for_pending_data_worker_error_does_not_block_gate_enqueue() {
        let (message_tx, message_rx) = sync_channel(1);
        message_tx
            .send(SendMemoryThreadMessage::Memory(MemoryRangeTable::default()))
            .unwrap();
        let (_notify_tx, notify_rx) = channel();
        let worker_error = Arc::new(AtomicBool::new(true));
        let worker = thread::spawn(|| -> Result<(), MigratableError> {
            Err(MigratableError::MigrateSend(anyhow!("injected worker failure")))
        });

        let mut connections = SendAdditionalConnections {
            guest_memory: guest_memory(),
            threads: vec![worker],
            message_tx,
            worker_error,
            notify_rx,
        };

        // Keep the receiver alive but deliberately unable to drain the full queue.
        let _message_rx = message_rx;
        let err = connections.wait_for_pending_data().unwrap_err();
        assert!(err.to_string().contains("injected worker failure"));
    }
}

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
