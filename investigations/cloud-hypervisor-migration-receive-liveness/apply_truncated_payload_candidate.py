#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/migration/transport.rs")
text = path.read_text()
old = '''            let bytes_read = mem
                .read_volatile_from(
                    GuestAddress(range.gpa + offset),
                    socket,
                    (range.length - offset) as usize,
                )
                .context("Error receiving memory from socket")
                .map_err(MigratableError::MigrateReceive)?;
            offset += bytes_read as u64;
'''
new = '''            let bytes_read = mem
                .read_volatile_from(
                    GuestAddress(range.gpa + offset),
                    socket,
                    (range.length - offset) as usize,
                )
                .context("Error receiving memory from socket")
                .map_err(MigratableError::MigrateReceive)?;
            if bytes_read == 0 {
                return Err(MigratableError::MigrateSocket(io::Error::new(
                    ErrorKind::UnexpectedEof,
                    "migration peer closed while receiving memory payload",
                )));
            }
            offset += bytes_read as u64;
'''

count = text.count(old)
if count != 1:
    raise SystemExit(f"expected exactly one receive loop owner in {path}, found {count}")
path.write_text(text.replace(old, new, 1))
