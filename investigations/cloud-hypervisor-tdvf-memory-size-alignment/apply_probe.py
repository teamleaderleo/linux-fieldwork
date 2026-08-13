#!/usr/bin/env python3
from pathlib import Path

path = Path("arch/src/x86_64/tdx/mod.rs")
text = path.read_text()
marker = "tdvf_unaligned_memory_size_is_accepted_baseline"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = "#[cfg(test)]\nmod unit_tests {"
if text.count(anchor) != 1:
    raise SystemExit(f"expected exactly one TDX unit-test anchor in {path}")

probe = r'''#[cfg(test)]
mod memory_size_alignment_probe_tests {
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
        // TdvfSectionType::Bfv == 0, attributes == 0.

        bytes[0x1000..0x2000].fill(0x5a);
        let pointer_offset = FILE_LEN - 0x20;
        bytes[pointer_offset..pointer_offset + 4].copy_from_slice(&0u32.to_le_bytes());

        let path = temp_dir().join(format!(
            "cloud-hypervisor-tdvf-memory-align-{}-{memory_size:x}.fd",
            id()
        ));
        write(&path, bytes).unwrap();
        let file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();
        file
    }

    #[test]
    #[ignore]
    fn tdvf_unaligned_memory_size_is_accepted_baseline() {
        let mut file = fixture(0x1800);
        let (sections, _) = parse_tdvf_sections(&mut file).unwrap();
        let section = sections[0];
        let memory_size = section.size;
        let backend_pages = memory_size / 4096;
        let backend_bytes = backend_pages * 4096;
        let dropped = memory_size - backend_bytes;
        println!(
            "TDVF_MEMORY_ALIGN_BASELINE memory_size=0x{memory_size:x} backend_pages={backend_pages} backend_bytes=0x{backend_bytes:x} dropped=0x{dropped:x}"
        );
        assert_eq!(memory_size, 0x1800);
        assert_eq!(backend_pages, 1);
        assert_eq!(backend_bytes, 0x1000);
        assert_eq!(dropped, 0x800);
    }

    #[test]
    fn tdvf_memory_size_must_be_page_aligned() {
        let mut file = fixture(0x1800);
        let result = parse_tdvf_sections(&mut file);
        println!("TDVF_MEMORY_ALIGN_INVARIANT result={result:?}");
        assert!(
            result.is_err(),
            "TDVF MemoryDataSize must be 4 KiB aligned"
        );
    }

    #[test]
    fn tdvf_page_aligned_memory_size_is_valid() {
        let mut file = fixture(0x2000);
        let (sections, _) = parse_tdvf_sections(&mut file).unwrap();
        let memory_size = sections[0].size;
        println!("TDVF_MEMORY_ALIGN_CONTROL memory_size=0x{memory_size:x}");
        assert_eq!(memory_size, 0x2000);
    }
}

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
