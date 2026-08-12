#!/usr/bin/env python3
from pathlib import Path

path = Path("vm-migration/src/protocol.rs")
text = path.read_text()
marker = "invalid memory range table length"
if marker in text:
    raise SystemExit(f"candidate marker already present in {path}")

old = '''    pub fn read_from(fd: &mut dyn Read, length: u64) -> Result<MemoryRangeTable, MigratableError> {
        assert!((length as usize).is_multiple_of(size_of::<MemoryRange>()));

        let mut data: Vec<MemoryRange> =
            vec![MemoryRange::default(); length as usize / size_of::<MemoryRange>()];

        fd.read_exact(data.as_mut_bytes())
            .map_err(MigratableError::MigrateSocket)?;

        Ok(Self { data })
    }
'''
new = '''    pub fn read_from(fd: &mut dyn Read, length: u64) -> Result<MemoryRangeTable, MigratableError> {
        let length = usize::try_from(length).map_err(|_| {
            MigratableError::MigrateReceive(anyhow!(
                "invalid memory range table length: {length} does not fit in usize"
            ))
        })?;
        if !length.is_multiple_of(size_of::<MemoryRange>()) {
            return Err(MigratableError::MigrateReceive(anyhow!(
                "invalid memory range table length: {length} is not a multiple of {}",
                size_of::<MemoryRange>()
            )));
        }

        let mut data: Vec<MemoryRange> =
            vec![MemoryRange::default(); length / size_of::<MemoryRange>()];

        fd.read_exact(data.as_mut_bytes())
            .map_err(MigratableError::MigrateSocket)?;

        Ok(Self { data })
    }
'''

count = text.count(old)
if count != 1:
    raise SystemExit(f"expected exactly one MemoryRangeTable::read_from body, found {count}")
path.write_text(text.replace(old, new, 1))
