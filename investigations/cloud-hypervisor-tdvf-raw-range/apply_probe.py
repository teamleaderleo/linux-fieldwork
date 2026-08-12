#!/usr/bin/env python3
from pathlib import Path

path = Path("arch/src/x86_64/tdx/mod.rs")
text = path.read_text()
marker = "tdvf_bfv_range_past_eof_is_accepted_baseline"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = "#[cfg(test)]\nmod unit_tests {"
if text.count(anchor) != 1:
    raise SystemExit(f"expected exactly one TDX unit-test anchor in {path}")

probe = r'''#[cfg(test)]
mod raw_range_probe_tests {
    use std::fs::{OpenOptions, remove_file};

    use super::*;

    const FILE_LEN: usize = 0x100;
    const DESCRIPTOR_OFFSET: usize = 0;
    const SECTION_OFFSET: usize = 16;

    fn fixture(data_offset: u32, data_size: u32) -> File {
        assert_eq!(size_of::<TdvfDescriptor>(), 16);
        assert_eq!(size_of::<TdvfSection>(), 32);

        let mut bytes = vec![0u8; FILE_LEN];
        bytes[DESCRIPTOR_OFFSET..DESCRIPTOR_OFFSET + 4].copy_from_slice(b"TDVF");
        bytes[DESCRIPTOR_OFFSET + 4..DESCRIPTOR_OFFSET + 8]
            .copy_from_slice(&(48u32).to_le_bytes());
        bytes[DESCRIPTOR_OFFSET + 8..DESCRIPTOR_OFFSET + 12]
            .copy_from_slice(&(1u32).to_le_bytes());
        bytes[DESCRIPTOR_OFFSET + 12..DESCRIPTOR_OFFSET + 16]
            .copy_from_slice(&(1u32).to_le_bytes());

        bytes[SECTION_OFFSET..SECTION_OFFSET + 4].copy_from_slice(&data_offset.to_le_bytes());
        bytes[SECTION_OFFSET + 4..SECTION_OFFSET + 8].copy_from_slice(&data_size.to_le_bytes());
        bytes[SECTION_OFFSET + 8..SECTION_OFFSET + 16]
            .copy_from_slice(&(0x1000u64).to_le_bytes());
        bytes[SECTION_OFFSET + 16..SECTION_OFFSET + 24]
            .copy_from_slice(&(data_size as u64).to_le_bytes());
        // TdvfSectionType::Bfv == 0, attributes == 0; zero-filled bytes already encode both.

        // Deprecated metadata pointer lives 32 bytes from EOF. Zero points at our descriptor.
        let pointer_offset = FILE_LEN - 0x20;
        bytes[pointer_offset..pointer_offset + 4].copy_from_slice(&0u32.to_le_bytes());

        let path = std::env::temp_dir().join(format!(
            "cloud-hypervisor-tdvf-range-{}-{data_offset:x}-{data_size:x}.fd",
            std::process::id()
        ));
        std::fs::write(&path, bytes).unwrap();
        let file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();
        file
    }

    #[test]
    #[ignore]
    fn tdvf_bfv_range_past_eof_is_accepted_baseline() {
        let mut file = fixture(0x180, 0x20);
        let (sections, guid_found) = parse_tdvf_sections(&mut file).unwrap();
        let data_offset = sections[0].data_offset;
        let data_size = sections[0].data_size;
        let section_type = sections[0].r#type;
        println!(
            "TDVF_RAW_BASELINE file_len=0x{FILE_LEN:x} data_offset=0x{data_offset:x} data_size=0x{data_size:x} guid_found={guid_found}"
        );
        assert_eq!(sections.len(), 1);
        assert!(matches!(section_type, TdvfSectionType::Bfv));
        assert_eq!(data_offset, 0x180);
        assert_eq!(data_size, 0x20);
    }

    #[test]
    fn tdvf_bfv_range_past_eof_is_rejected() {
        let mut file = fixture(0x180, 0x20);
        let result = parse_tdvf_sections(&mut file);
        println!("TDVF_RAW_INVARIANT result={result:?}");
        assert!(result.is_err(), "BFV raw range past EOF must be rejected");
    }

    #[test]
    fn tdvf_bfv_range_inside_file_is_valid() {
        let mut file = fixture(0x40, 0x20);
        let (sections, _) = parse_tdvf_sections(&mut file).unwrap();
        let data_offset = sections[0].data_offset;
        let data_size = sections[0].data_size;
        let section_type = sections[0].r#type;
        println!(
            "TDVF_RAW_CONTROL file_len=0x{FILE_LEN:x} data_offset=0x{data_offset:x} data_size=0x{data_size:x}"
        );
        assert_eq!(sections.len(), 1);
        assert!(matches!(section_type, TdvfSectionType::Bfv));
    }
}

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
