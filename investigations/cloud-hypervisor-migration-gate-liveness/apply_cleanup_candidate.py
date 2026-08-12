#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/migration/transport.rs")
text = path.read_text()
marker = "let message_tx = mem::replace(&mut self.message_tx, closed_tx);"
if marker in text:
    raise SystemExit(f"cleanup candidate marker already present in {path}")

old_import = "use std::io::{self, ErrorKind, Read, Write};\n"
new_import = old_import + "use std::mem;\n"
if text.count(old_import) != 1:
    raise SystemExit("unexpected std::io import count")
text = text.replace(old_import, new_import, 1)

old_recv = '''            let message = message_rx
                .lock()
                .map_err(|_| MigratableError::MigrateSend(anyhow!("message_rx mutex is poisoned")))
                .inspect_err(|_| {
                    worker_error.store(true, Ordering::Relaxed);
                    // We ignore errors during error handling.
                    notify_tx.send(SendMemoryThreadNotify::Error).ok();
                })?
                .recv()
                .context("Error receiving message from main thread")
                .map_err(MigratableError::MigrateSend)
                .inspect_err(|_| {
                    worker_error.store(true, Ordering::Relaxed);
                    notify_tx.send(SendMemoryThreadNotify::Error).ok();
                })?;
'''
new_recv = '''            let message_rx = message_rx
                .lock()
                .map_err(|_| MigratableError::MigrateSend(anyhow!("message_rx mutex is poisoned")))
                .inspect_err(|_| {
                    worker_error.store(true, Ordering::Relaxed);
                    // We ignore errors during error handling.
                    notify_tx.send(SendMemoryThreadNotify::Error).ok();
                })?;
            let message = match message_rx.recv() {
                Ok(message) => message,
                // The main thread closes the work channel as the guaranteed terminal
                // condition during cleanup. Queued work is drained before this point.
                Err(_) => return Ok(()),
            };
'''
if text.count(old_recv) != 1:
    raise SystemExit("unexpected worker receive block count")
text = text.replace(old_recv, new_recv, 1)

old_cleanup = '''        // Send disconnect messages to all workers.
        for _ in 0..self.threads.len() {
            // All threads may have terminated, leading to a dropped receiver. Thus we ignore
            // errors here.
            self.message_tx
                .try_send(SendMemoryThreadMessage::Disconnect)
                .ok();
        }
'''
new_cleanup = '''        // Closing the work channel is independent of bounded-queue capacity. Workers
        // drain already queued work and then receive the terminal disconnect state.
        let (closed_tx, closed_rx) = sync_channel(0);
        drop(closed_rx);
        let message_tx = mem::replace(&mut self.message_tx, closed_tx);
        drop(message_tx);
'''
if text.count(old_cleanup) != 1:
    raise SystemExit("unexpected cleanup disconnect block count")
text = text.replace(old_cleanup, new_cleanup, 1)

path.write_text(text)
