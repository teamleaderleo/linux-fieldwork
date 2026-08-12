#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/migration/transport.rs")
text = path.read_text()
marker = "let mut message = SendMemoryThreadMessage::Gate(gate.clone());"
if marker in text:
    raise SystemExit(f"candidate marker already present in {path}")

old = '''        for _ in 0..self.threads.len() {
            self.message_tx
                .send(SendMemoryThreadMessage::Gate(gate.clone()))
                .context("Error sending gate message to workers")
                .map_err(MigratableError::MigrateSend)?;
        }
'''
new = '''        for _ in 0..self.threads.len() {
            let mut message = SendMemoryThreadMessage::Gate(gate.clone());
            loop {
                if self.worker_error.load(Ordering::Relaxed) {
                    gate.open();
                    return self.cleanup();
                }

                match self.message_tx.try_send(message) {
                    Ok(()) => break,
                    Err(TrySendError::Full(unsent_message)) => {
                        thread::sleep(Duration::from_millis(10));
                        message = unsent_message;
                    }
                    Err(TrySendError::Disconnected(_)) => {
                        gate.open();
                        return Err(self.cleanup().err().unwrap_or(
                            MigratableError::MigrateSend(anyhow!(
                                "All sending threads disconnected while enqueueing a gate"
                            )),
                        ));
                    }
                }
            }
        }
'''

if text.count(old) != 1:
    raise SystemExit(f"expected exactly one wait_for_pending_data gate enqueue block in {path}")
path.write_text(text.replace(old, new, 1))
