#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/migration/transport.rs")
text = path.read_text()
marker = "let mut disconnect = SendMemoryThreadMessage::Disconnect;"
if marker in text:
    raise SystemExit(f"cleanup candidate marker already present in {path}")

old = '''        // Send disconnect messages to all workers.
        for _ in 0..self.threads.len() {
            // All threads may have terminated, leading to a dropped receiver. Thus we ignore
            // errors here.
            self.message_tx
                .try_send(SendMemoryThreadMessage::Disconnect)
                .ok();
        }
'''
new = '''        // Send disconnect messages to all workers. The work queue can still be full when
        // cleanup follows a worker error, so retry without blocking until each terminal
        // message is accepted or all receivers have disappeared.
        for _ in 0..self.threads.len() {
            let mut disconnect = SendMemoryThreadMessage::Disconnect;
            loop {
                match self.message_tx.try_send(disconnect) {
                    Ok(()) => break,
                    Err(TrySendError::Full(unsent_message)) => {
                        thread::sleep(Duration::from_millis(10));
                        disconnect = unsent_message;
                    }
                    Err(TrySendError::Disconnected(_)) => break,
                }
            }
        }
'''

if text.count(old) != 1:
    raise SystemExit(f"expected exactly one cleanup disconnect loop in {path}")
path.write_text(text.replace(old, new, 1))
