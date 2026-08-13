#!/usr/bin/env python3
from pathlib import Path

path = Path("arch/src/x86_64/tdx/mod.rs")
text = path.read_text()
marker = "InvalidSectionMemorySize"
if marker in text:
    raise SystemExit(f"candidate marker already present in {path}")

old_error = '''    #[error("Invalid descriptor version")]
    InvalidDescriptorVersion,
'''
new_error = '''    #[error("Invalid descriptor version")]
    InvalidDescriptorVersion,
    #[error(
        "TDVF section raw data size 0x{data_size:x} exceeds memory data size 0x{memory_size:x}"
    )]
    InvalidSectionMemorySize { data_size: u32, memory_size: u64 },
'''
if text.count(old_error) != 1:
    raise SystemExit("unexpected TdvfError anchor count")
text = text.replace(old_error, new_error, 1)

old_return = '''    .map_err(TdvfError::ReadDescriptor)?;

    Ok((sections, guid_found))
}
'''
new_return = '''    .map_err(TdvfError::ReadDescriptor)?;

    for section in &sections {
        let data_size = section.data_size;
        let memory_size = section.size;
        if memory_size < u64::from(data_size) {
            return Err(TdvfError::InvalidSectionMemorySize {
                data_size,
                memory_size,
            });
        }
    }

    Ok((sections, guid_found))
}
'''
if text.count(old_return) != 1:
    raise SystemExit("unexpected parse_tdvf_sections return anchor count")
text = text.replace(old_return, new_return, 1)

anchor = "#[cfg(test)]\nmod unit_tests {"
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDX unit-test anchor count")

tests = r'''#[cfg(test)]
mod data_memory_size_candidate_tests {
    use std::env::temp_dir;
    use std::fs::{OpenOptions, remove_file, write};
    use std::process::id;

    use super::*;

    const FILE_LEN: usize = 0x4000;
    const SECTION_OFFSET: usize = 16;

    fn fixture(data_size: u32, memory_size: u64) -> File {
        let mut bytes = vec![0u8; FILE_LEN];
        bytes[0..4].copy_from_slice(b"TDVF");
        bytes[4..8].copy_from_slice(&(48u32).to_le_bytes());
        bytes[8..12].copy_from_slice(&(1u32).to_le_bytes());
        bytes[12..16].copy_from_slice(&(1u32).to_le_bytes());

        bytes[SECTION_OFFSET..SECTION_OFFSET + 4].copy_from_slice(&(0x1000u32).to_le_bytes());
        bytes[SECTION_OFFSET + 4..SECTION_OFFSET + 8].copy_from_slice(&data_size.to_le_bytes());
        bytes[SECTION_OFFSET + 8..SECTION_OFFSET + 16]
            .copy_from_slice(&(0x10_0000u64).to_le_bytes());
        bytes[SECTION_OFFSET + 16..SECTION_OFFSET + 24]
            .copy_from_slice(&memory_size.to_le_bytes());
        // TdvfSectionType::Bfv == 0, attributes == 0.

        let pointer_offset = FILE_LEN - 0x20;
        bytes[pointer_offset..pointer_offset + 4].copy_from_slice(&0u32.to_le_bytes());

        let path = temp_dir().join(format!(
            "cloud-hypervisor-tdvf-data-memory-candidate-{}-{data_size:x}-{memory_size:x}.fd",
            id()
        ));
        write(&path, bytes).unwrap();
        let file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();
        file
    }

    #[test]
    fn tdvf_raw_data_larger_than_memory_is_typed_error() {
        let mut file = fixture(0x2000, 0x1000);
        let result = parse_tdvf_sections(&mut file);
        println!("TDVF_DATA_MEMORY_CANDIDATE malformed_result={result:?}");
        assert!(matches!(
            result,
            Err(TdvfError::InvalidSectionMemorySize {
                data_size: 0x2000,
                memory_size: 0x1000,
            })
        ));
    }

    #[test]
    fn tdvf_raw_data_smaller_than_memory_remains_valid() {
        let mut file = fixture(0x2000, 0x3000);
        let (sections, _) = parse_tdvf_sections(&mut file).unwrap();
        let section = sections[0];
        let data_size = section.data_size;
        let memory_size = section.size;
        println!(
            "TDVF_DATA_MEMORY_CANDIDATE control data_size=0x{data_size:x} memory_size=0x{memory_size:x}"
        );
        assert_eq!(data_size, 0x2000);
        assert_eq!(memory_size, 0x3000);
    }
}

'''

path.write_text(text.replace(anchor, tests + anchor, 1))
