#!/usr/bin/env python3
from pathlib import Path

path = Path("arch/src/x86_64/tdx/mod.rs")
text = path.read_text()
marker = "tdvf_guid_table_too_small_panics_baseline"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = '''    #[test]
    #[ignore]
    fn test_parse_tdvf_sections() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDVF unit-test anchor count")

probe = r'''    fn guid_table_fixture(table_size: u16, entry_size: Option<u16>) -> File {
        use std::env::temp_dir;
        use std::fs::{OpenOptions, remove_file, write};
        use std::process::id;

        const FILE_LEN: usize = 0x100;
        const FOOTER_GUID_LE: [u8; 16] = [
            0xde, 0x82, 0xb5, 0x96, 0xb2, 0x1f, 0xf7, 0x45, 0xba, 0xea, 0xa3, 0x66,
            0xc5, 0x5a, 0x08, 0x2d,
        ];

        let mut bytes = vec![0u8; FILE_LEN];
        let table_size_pos = FILE_LEN - 0x32;
        let footer_pos = FILE_LEN - 0x30;
        bytes[table_size_pos..table_size_pos + 2].copy_from_slice(&table_size.to_le_bytes());
        bytes[footer_pos..footer_pos + 16].copy_from_slice(&FOOTER_GUID_LE);
        // Deprecated metadata pointer at EOF-0x20 remains zero for the fallback control.

        if let Some(entry_size) = entry_size {
            assert!(table_size >= 40);
            let table_start = FILE_LEN - (usize::from(table_size) + 0x20);
            let offset = usize::from(table_size) - 18;
            assert_eq!(offset, 22, "fixture currently models one 22-byte entry");
            bytes[table_start + offset - 18..table_start + offset - 16]
                .copy_from_slice(&entry_size.to_le_bytes());
            // The following 16 zero bytes are an ordinary non-matching UUID.
        }

        let path = temp_dir().join(format!(
            "cloud-hypervisor-tdvf-guid-table-{}-{table_size}-{}.fd",
            id(),
            entry_size.unwrap_or(0)
        ));
        write(&path, bytes).unwrap();
        let file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();
        file
    }

    #[test]
    fn tdvf_guid_table_minimum_footer_control() {
        let mut file = guid_table_fixture(18, None);
        let (offset, guid_found) = tdvf_descriptor_offset(&mut file).unwrap();
        println!("TDVF_GUID_CONTROL offset={offset:?} guid_found={guid_found}");
        assert!(matches!(offset, SeekFrom::Start(0)));
        assert!(!guid_found);
    }

    #[test]
    #[ignore]
    fn tdvf_guid_table_too_small_panics_baseline() {
        let mut file = guid_table_fixture(0, None);
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            tdvf_descriptor_offset(&mut file)
        }));
        println!("TDVF_GUID_SMALL_BASELINE panicked={}", result.is_err());
        assert!(result.is_err());
    }

    #[test]
    fn tdvf_guid_table_too_small_should_not_panic() {
        let mut file = guid_table_fixture(0, None);
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            tdvf_descriptor_offset(&mut file)
        }));
        println!("TDVF_GUID_SMALL_INVARIANT panicked={}", result.is_err());
        assert!(result.is_ok(), "GUID table size below footer size must not panic");
        assert!(result.unwrap().is_err());
    }

    #[test]
    #[ignore]
    fn tdvf_guid_entry_too_large_panics_baseline() {
        let mut file = guid_table_fixture(40, Some(23));
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            tdvf_descriptor_offset(&mut file)
        }));
        println!("TDVF_GUID_ENTRY_BASELINE panicked={}", result.is_err());
        assert!(result.is_err());
    }

    #[test]
    fn tdvf_guid_entry_too_large_should_not_panic() {
        let mut file = guid_table_fixture(40, Some(23));
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            tdvf_descriptor_offset(&mut file)
        }));
        println!("TDVF_GUID_ENTRY_INVARIANT panicked={}", result.is_err());
        assert!(result.is_ok(), "oversized GUID entry must not underflow table offset");
        assert!(result.unwrap().is_err());
    }

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
