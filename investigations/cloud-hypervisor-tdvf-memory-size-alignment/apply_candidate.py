#!/usr/bin/env python3
from pathlib import Path

path = Path("arch/src/x86_64/tdx/mod.rs")
text = path.read_text()
marker = "InvalidSectionMemorySizeAlignment"
if marker in text:
    raise SystemExit(f"candidate marker already present in {path}")

old_error = '''    #[error("Invalid descriptor version")]
    InvalidDescriptorVersion,
'''
new_error = '''    #[error("Invalid descriptor version")]
    InvalidDescriptorVersion,
    #[error("TDVF section memory data size 0x{memory_size:x} is not 4 KiB aligned")]
    InvalidSectionMemorySizeAlignment { memory_size: u64 },
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
        let memory_size = section.size;
        if memory_size % 4096 != 0 {
            return Err(TdvfError::InvalidSectionMemorySizeAlignment { memory_size });
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
mod memory_size_alignment_candidate_tests {
    use std::env::temp_dir;
    use std::fs::{OpenOptions, remove_file, write};
    use std::process::id;

    use super::*;

    const FILE_LEN: usize = 0x3000;
    const SECTION_OFFSET: usize = 16;

    fn fixture(memory_size: u64) -> File {
        let mut bytes = vec![0u8; FILE_LEN];
        bytes[0..4].copy_from_slice(b"TDVF");
        bytes[4..8].copy_from_slice(&(48u32).to_le_bytes());
        bytes[8..12].copy_from_slice(&(1u32).to_le_bytes());
        bytes[12..16].copy_from_slice(&(1u32).to_le_bytes());

        bytes[SECTION_OFFSET..SECTION_OFFSET + 4].copy_from_slice(&(0x1000u32).to_le_bytes());
        bytes[SECTION_OFFSET + 4..SECTION_OFFSET + 8]
            .copy_from_slice(&(0x1000u32).to_le_bytes());
        bytes[SECTION_OFFSET + 8..SECTION_OFFSET + 16]
            .copy_from_slice(&(0x10_0000u64).to_le_bytes());
        bytes[SECTION_OFFSET + 16..SECTION_OFFSET + 24]
            .copy_from_slice(&memory_size.to_le_bytes());

        let pointer_offset = FILE_LEN - 0x20;
        bytes[pointer_offset..pointer_offset + 4].copy_from_slice(&0u32.to_le_bytes());

        let path = temp_dir().join(format!(
            "cloud-hypervisor-tdvf-memory-align-candidate-{}-{memory_size:x}.fd",
            id()
        ));
        write(&path, bytes).unwrap();
        let file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();
        file
    }

    #[test]
    fn tdvf_unaligned_memory_size_is_typed_error() {
        let mut file = fixture(0x1800);
        let result = parse_tdvf_sections(&mut file);
        println!("TDVF_MEMORY_ALIGN_CANDIDATE malformed_result={result:?}");
        assert!(matches!(
            result,
            Err(TdvfError::InvalidSectionMemorySizeAlignment {
                memory_size: 0x1800,
            })
        ));
    }

    #[test]
    fn tdvf_page_aligned_memory_size_remains_valid() {
        let mut file = fixture(0x2000);
        let (sections, _) = parse_tdvf_sections(&mut file).unwrap();
        let memory_size = sections[0].size;
        println!("TDVF_MEMORY_ALIGN_CANDIDATE control memory_size=0x{memory_size:x}");
        assert_eq!(memory_size, 0x2000);
    }
}

'''

path.write_text(text.replace(anchor, tests + anchor, 1))
