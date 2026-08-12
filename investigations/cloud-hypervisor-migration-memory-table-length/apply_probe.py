#!/usr/bin/env python3
from pathlib import Path

path = Path("vm-migration/src/protocol.rs")
text = path.read_text()
marker = "malformed_memory_range_table_length_returns_error_without_panic"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = "    #[test]\n    fn test_start_request_ignores_residual_command_headers_bytes() {"
if text.count(anchor) != 1:
    raise SystemExit(f"expected exactly one protocol unit-test anchor in {path}")

probe = r'''    #[test]
    fn malformed_memory_range_table_length_returns_error_without_panic() {
        let malformed = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            let mut cursor = Cursor::new(Vec::new());
            MemoryRangeTable::read_from(&mut cursor, 1)
        }));
        assert!(
            malformed.is_ok(),
            "malformed migration table framing must return an error instead of panicking"
        );
        assert!(malformed.unwrap().is_err());

        let mut empty = Cursor::new(Vec::new());
        assert!(
            MemoryRangeTable::read_from(&mut empty, 0)
                .unwrap()
                .is_empty()
        );

        let range = MemoryRange {
            gpa: 0x4000,
            length: 0x1000,
        };
        let mut encoded = Vec::new();
        range.write_to(&mut encoded).unwrap();
        let mut cursor = Cursor::new(encoded);
        let table =
            MemoryRangeTable::read_from(&mut cursor, std::mem::size_of::<MemoryRange>() as u64)
                .unwrap();
        assert_eq!(table.regions(), &[range]);
    }

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
