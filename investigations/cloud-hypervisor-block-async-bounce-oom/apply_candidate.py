#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/io/async_io/owned_io_buffer.rs")
text = path.read_text()
old = '''        if alignment <= 1 {
            return Ok(Self::Vec(vec![0; len]));
        }
'''
new = '''        if alignment <= 1 {
            let mut buf = Vec::new();
            buf.try_reserve_exact(len)
                .map_err(|e| io::Error::new(io::ErrorKind::OutOfMemory, e.to_string()))?;
            buf.resize(len, 0);
            return Ok(Self::Vec(buf));
        }
'''
if text.count(old) != 1:
    raise SystemExit("unexpected ordinary Vec allocation anchor count")
path.write_text(text.replace(old, new, 1))
