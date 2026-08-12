#!/usr/bin/env python3
from pathlib import Path

path = Path("vm-migration/src/protocol.rs")
text = path.read_text()
marker = "test_memory_range_table_non_4k_page_size"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = "    #[test]\n    fn test_memory_range_table_partition() {"
if text.count(anchor) != 1:
    raise SystemExit(f"expected exactly one MemoryRangeTable test anchor in {path}")

probe = r'''    #[test]
    fn test_memory_range_table_non_4k_page_size() {
        let base = 0x4000_0000;
        let page_size = 16 * 1024;

        let one = MemoryRangeTable::from_dirty_bitmap([0b10], base, page_size);
        assert_eq!(
            one.regions(),
            &[MemoryRange {
                gpa: base + page_size,
                length: page_size,
            }]
        );

        let adjacent = MemoryRangeTable::from_dirty_bitmap([0b110], base, page_size);
        assert_eq!(
            adjacent.regions(),
            &[MemoryRange {
                gpa: base + page_size,
                length: 2 * page_size,
            }]
        );
    }

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
