#!/usr/bin/env python3
from pathlib import Path

path = Path("arch/src/x86_64/tdx/mod.rs")
text = path.read_text()
marker = "Invalid GUID table size"
if marker in text:
    raise SystemExit(f"candidate marker already present in {path}")

old_error = '''    #[error("Failed read GUID table")]
    ReadGuidTable(#[source] io::Error),
'''
new_error = old_error + '''    #[error("Invalid GUID table size {0}")]
    InvalidGuidTableSize(usize),
    #[error("Invalid GUID table entry size {entry_size} with {remaining} bytes remaining")]
    InvalidGuidTableEntrySize { entry_size: usize, remaining: usize },
'''
if text.count(old_error) != 1:
    raise SystemExit("unexpected ReadGuidTable error anchor count")
text = text.replace(old_error, new_error, 1)

old_table_size = '''        let table_size = u16::from_le_bytes(table_size) as usize;
        let mut table: Vec<u8> = vec![0; table_size];
'''
new_table_size = '''        let table_size = u16::from_le_bytes(table_size) as usize;
        if table_size < 18 {
            return Err(TdvfError::InvalidGuidTableSize(table_size));
        }
        let mut table: Vec<u8> = vec![0; table_size];
'''
if text.count(old_table_size) != 1:
    raise SystemExit("unexpected GUID table size anchor count")
text = text.replace(old_table_size, new_table_size, 1)

old_entry = '''            // Avoid going through an infinite loop if the entry size is 0
            if entry_size == 0 {
                break;
            }

            offset -= entry_size;
'''
new_entry = '''            // Avoid going through an infinite loop if the entry size is 0.
            if entry_size == 0 {
                break;
            }
            if entry_size < 18 || entry_size > offset {
                return Err(TdvfError::InvalidGuidTableEntrySize {
                    entry_size,
                    remaining: offset,
                });
            }

            offset -= entry_size;
'''
if text.count(old_entry) != 1:
    raise SystemExit("unexpected GUID entry subtraction anchor count")
text = text.replace(old_entry, new_entry, 1)

anchor = '''    #[test]
    #[ignore]
    fn test_parse_tdvf_sections() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDVF unit-test anchor count")

test = r'''    fn candidate_guid_table_fixture(table_size: u16, entry_size: Option<u16>) -> File {
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

        if let Some(entry_size) = entry_size {
            assert_eq!(table_size, 40);
            let table_start = FILE_LEN - (usize::from(table_size) + 0x20);
            let offset = usize::from(table_size) - 18;
            bytes[table_start + offset - 18..table_start + offset - 16]
                .copy_from_slice(&entry_size.to_le_bytes());
        }

        let path = temp_dir().join(format!(
            "cloud-hypervisor-tdvf-guid-candidate-{}-{table_size}-{}.fd",
            id(),
            entry_size.unwrap_or(0)
        ));
        write(&path, bytes).unwrap();
        let file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();
        file
    }

    #[test]
    fn tdvf_guid_table_structural_bounds_are_typed() {
        let mut too_small = candidate_guid_table_fixture(0, None);
        let small_err = tdvf_descriptor_offset(&mut too_small).unwrap_err();
        println!("TDVF_GUID_CANDIDATE small_result={small_err:?}");
        assert!(matches!(small_err, TdvfError::InvalidGuidTableSize(0)));

        let mut oversized_entry = candidate_guid_table_fixture(40, Some(23));
        let entry_err = tdvf_descriptor_offset(&mut oversized_entry).unwrap_err();
        println!("TDVF_GUID_CANDIDATE entry_result={entry_err:?}");
        assert!(matches!(
            entry_err,
            TdvfError::InvalidGuidTableEntrySize {
                entry_size: 23,
                remaining: 22,
            }
        ));
    }

    #[test]
    fn tdvf_guid_table_minimum_footer_is_valid() {
        let mut file = candidate_guid_table_fixture(18, None);
        let (offset, guid_found) = tdvf_descriptor_offset(&mut file).unwrap();
        println!("TDVF_GUID_CANDIDATE control_offset={offset:?} guid_found={guid_found}");
        assert!(matches!(offset, SeekFrom::Start(0)));
        assert!(!guid_found);
    }

'''
text = text.replace(anchor, test + anchor, 1)
path.write_text(text)
