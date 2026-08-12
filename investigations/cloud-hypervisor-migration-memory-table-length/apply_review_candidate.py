#!/usr/bin/env python3
from pathlib import Path

path = Path("vm-migration/src/protocol.rs")
text = path.read_text()
marker = "test_memory_range_table_rejects_unaligned_length"
if marker in text:
    raise SystemExit(f"review candidate marker already present in {path}")

old_fn = '''    pub fn read_from(fd: &mut dyn Read, length: u64) -> Result<MemoryRangeTable, MigratableError> {
        assert!((length as usize).is_multiple_of(size_of::<MemoryRange>()));

        let mut data: Vec<MemoryRange> =
            vec![MemoryRange::default(); length as usize / size_of::<MemoryRange>()];

        fd.read_exact(data.as_mut_bytes())
            .map_err(MigratableError::MigrateSocket)?;

        Ok(Self { data })
    }
'''
new_fn = '''    pub fn read_from(fd: &mut dyn Read, length: u64) -> Result<MemoryRangeTable, MigratableError> {
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

anchor = '''    #[test]
    fn test_memory_range_table_from_dirty_ranges_iter() {
'''
test = '''    #[test]
    fn test_memory_range_table_rejects_unaligned_length() {
        let mut cursor = Cursor::new(Vec::<u8>::new());
        let err = MemoryRangeTable::read_from(&mut cursor, 1).unwrap_err();
        assert!(matches!(err, crate::MigratableError::MigrateReceive(_)));
    }

'''

if text.count(old_fn) != 1:
    raise SystemExit(f"expected exactly one MemoryRangeTable::read_from body, found {text.count(old_fn)}")
if text.count(anchor) != 1:
    raise SystemExit(f"expected exactly one unit-test anchor, found {text.count(anchor)}")
text = text.replace(old_fn, new_fn, 1)
text = text.replace(anchor, test + anchor, 1)
path.write_text(text)
