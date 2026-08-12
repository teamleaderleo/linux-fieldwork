#!/usr/bin/env python3
from pathlib import Path

path = Path("arch/src/x86_64/tdx/mod.rs")
text = path.read_text()
marker = "TDVF section table exceeds firmware file"
if marker in text:
    raise SystemExit(f"candidate marker already present in {path}")

old_error = '''    #[error("Invalid descriptor version")]
    InvalidDescriptorVersion,
'''
new_error = old_error + '''    #[error(
        "TDVF section table exceeds firmware file: table_end={table_end:#x}, file_len={file_len:#x}"
    )]
    InvalidDescriptorRange { table_end: u64, file_len: u64 },
'''
if text.count(old_error) != 1:
    raise SystemExit("unexpected TDVF error anchor count")
text = text.replace(old_error, new_error, 1)

old_alloc = '''    let mut sections = Vec::new();
    sections.resize_with(
        descriptor.num_sections as usize,
        TdvfSection::default,
    );
'''
# Exact source currently formats resize_with on one line; accept either shape deterministically.
if old_alloc not in text:
    old_alloc = '''    let mut sections = Vec::new();
    sections.resize_with(descriptor.num_sections as usize, TdvfSection::default);
'''
if text.count(old_alloc) != 1:
    raise SystemExit("unexpected TDVF section allocation block count")
new_alloc = '''    let section_table_start = file.stream_position().map_err(TdvfError::ReadDescriptor)?;
    let file_len = file
        .metadata()
        .map_err(TdvfError::ReadDescriptor)?
        .len();
    let section_table_size = u64::from(descriptor.length) - size_of::<TdvfDescriptor>() as u64;
    let table_end = section_table_start
        .checked_add(section_table_size)
        .ok_or(TdvfError::InvalidDescriptorSize)?;
    if table_end > file_len {
        return Err(TdvfError::InvalidDescriptorRange {
            table_end,
            file_len,
        });
    }

    let mut sections = Vec::new();
    sections.resize_with(descriptor.num_sections as usize, TdvfSection::default);
'''
text = text.replace(old_alloc, new_alloc, 1)

anchor = '''    #[test]
    #[ignore]
    fn test_parse_tdvf_sections() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDVF unit-test anchor count")

test = r'''    fn candidate_truncated_section_table_fixture(num_sections: u32) -> File {
        use std::env::temp_dir;
        use std::fs::{OpenOptions, remove_file, write};
        use std::process::id;

        const FILE_LEN: usize = 0x100;
        let section_bytes = u64::from(num_sections) * size_of::<TdvfSection>() as u64;
        let descriptor_len = size_of::<TdvfDescriptor>() as u64 + section_bytes;
        assert!(descriptor_len <= u64::from(u32::MAX));

        let mut bytes = vec![0u8; FILE_LEN];
        bytes[0..4].copy_from_slice(b"TDVF");
        bytes[4..8].copy_from_slice(&(descriptor_len as u32).to_le_bytes());
        bytes[8..12].copy_from_slice(&(1u32).to_le_bytes());
        bytes[12..16].copy_from_slice(&num_sections.to_le_bytes());
        bytes[FILE_LEN - 0x20..FILE_LEN - 0x1c].copy_from_slice(&0u32.to_le_bytes());

        let path = temp_dir().join(format!(
            "cloud-hypervisor-tdvf-allocation-candidate-{}-{num_sections}.fd",
            id()
        ));
        write(&path, bytes).unwrap();
        let file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();
        file
    }

    #[test]
    fn tdvf_truncated_section_table_rejected_before_allocation() {
        let mut file = candidate_truncated_section_table_fixture(33_554_432);
        let err = parse_tdvf_sections(&mut file).unwrap_err();
        println!("TDVF_ALLOC_CANDIDATE invalid_result={err:?}");
        assert!(matches!(
            err,
            TdvfError::InvalidDescriptorRange {
                table_end: 0x4000_0010,
                file_len: 0x100,
            }
        ));
    }

'''
text = text.replace(anchor, test + anchor, 1)
path.write_text(text)
