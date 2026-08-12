#!/usr/bin/env python3
from pathlib import Path

path = Path("vm-migration/src/protocol.rs")
text = path.read_text()
marker = "migration memory range table length does not fit usize"
if marker in text:
    raise SystemExit(f"candidate marker already present in {path}")

old = '''    pub fn read_from(fd: &mut dyn Read, length: u64) -> Result<MemoryRangeTable, MigratableError> {
        assert!((length as usize).is_multiple_of(size_of::<MemoryRange>()));

        let mut data: Vec<MemoryRange> =
            vec![MemoryRange::default(); length as usize / size_of::<MemoryRange>()];
'''
new = '''    pub fn read_from(fd: &mut dyn Read, length: u64) -> Result<MemoryRangeTable, MigratableError> {
        let length = usize::try_from(length).map_err(|_| {
            MigratableError::MigrateReceive(anyhow!(
                "migration memory range table length does not fit usize: {length}"
            ))
        })?;
        if !length.is_multiple_of(size_of::<MemoryRange>()) {
            return Err(MigratableError::MigrateReceive(anyhow!(
                "migration memory range table length is not a whole number of records: {length}"
            )));
        }

        let mut data: Vec<MemoryRange> =
            vec![MemoryRange::default(); length / size_of::<MemoryRange>()];
'''

if text.count(old) != 1:
    raise SystemExit(f"expected exactly one MemoryRangeTable::read_from owner in {path}")
path.write_text(text.replace(old, new, 1))
