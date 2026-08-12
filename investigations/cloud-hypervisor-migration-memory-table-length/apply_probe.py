#!/usr/bin/env python3
from pathlib import Path

path = Path("vm-migration/src/protocol.rs")
text = path.read_text()
marker = "malformed_memory_range_table_length_returns_error"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

probe = r'''

#[cfg(test)]
mod malformed_memory_range_table_length_tests {
    use super::*;
    use std::io::Cursor;
    use std::panic::{AssertUnwindSafe, catch_unwind};

    #[test]
    #[ignore = "baseline witness intentionally exercises current panic"]
    fn malformed_memory_range_table_length_panics_baseline() {
        let mut cursor = Cursor::new(Vec::<u8>::new());
        let caught = catch_unwind(AssertUnwindSafe(|| {
            MemoryRangeTable::read_from(&mut cursor, 1)
        }));
        eprintln!("MALFORMED_TABLE_BASELINE panicked={}", caught.is_err());
        assert!(caught.is_err(), "current baseline must panic on malformed length");
    }

    #[test]
    fn malformed_memory_range_table_length_returns_error() {
        let mut cursor = Cursor::new(Vec::<u8>::new());
        let caught = catch_unwind(AssertUnwindSafe(|| {
            MemoryRangeTable::read_from(&mut cursor, 1)
        }));
        assert!(caught.is_ok(), "malformed peer length must not panic");
        let result = caught.unwrap();
        assert!(
            matches!(result, Err(MigratableError::MigrateReceive(_))),
            "malformed peer length must return MigrateReceive"
        );
    }

    #[test]
    fn empty_memory_range_table_length_is_valid() {
        let mut cursor = Cursor::new(Vec::<u8>::new());
        let table = MemoryRangeTable::read_from(&mut cursor, 0).unwrap();
        assert!(table.data.is_empty());
    }

    #[test]
    fn complete_memory_range_record_decodes() {
        let expected = MemoryRange {
            gpa: 0x1234_5000,
            length: 0x6000,
        };
        let mut encoded = Vec::new();
        expected.write_to(&mut encoded).unwrap();
        assert_eq!(encoded.len(), size_of::<MemoryRange>());

        let mut cursor = Cursor::new(encoded);
        let table = MemoryRangeTable::read_from(
            &mut cursor,
            size_of::<MemoryRange>() as u64,
        )
        .unwrap();
        assert_eq!(table.data, vec![expected]);
    }
}
'''

path.write_text(text + probe)
