#!/usr/bin/env python3
from pathlib import Path

path = Path("arch/src/x86_64/tdx/mod.rs")
text = path.read_text()
marker = "tdvf_embedded_payload_metadata_and_bytes_are_accepted"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = "#[cfg(test)]\nmod unit_tests {"
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDX unit-test anchor count")

probe = r'''#[cfg(test)]
mod embedded_payload_probe_tests {
    use std::env::temp_dir;
    use std::fs::{OpenOptions, remove_file, write};
    use std::io::{Read, Seek, SeekFrom};
    use std::process::id;

    use super::*;

    const FILE_LEN: usize = 0x2000;
    const SECTION_OFFSET: usize = 16;
    const DATA_OFFSET: u32 = 0x1000;
    const DATA_SIZE: u32 = 0x10;
    const ADDRESS: u64 = 0x20_0000;
    const MEMORY_SIZE: u64 = 0x1000;

    fn fixture() -> File {
        let mut bytes = vec![0u8; FILE_LEN];
        bytes[0..4].copy_from_slice(b"TDVF");
        bytes[4..8].copy_from_slice(&(48u32).to_le_bytes());
        bytes[8..12].copy_from_slice(&(1u32).to_le_bytes());
        bytes[12..16].copy_from_slice(&(1u32).to_le_bytes());

        bytes[SECTION_OFFSET..SECTION_OFFSET + 4].copy_from_slice(&DATA_OFFSET.to_le_bytes());
        bytes[SECTION_OFFSET + 4..SECTION_OFFSET + 8].copy_from_slice(&DATA_SIZE.to_le_bytes());
        bytes[SECTION_OFFSET + 8..SECTION_OFFSET + 16].copy_from_slice(&ADDRESS.to_le_bytes());
        bytes[SECTION_OFFSET + 16..SECTION_OFFSET + 24]
            .copy_from_slice(&MEMORY_SIZE.to_le_bytes());
        bytes[SECTION_OFFSET + 24..SECTION_OFFSET + 28].copy_from_slice(&(5u32).to_le_bytes());
        bytes[SECTION_OFFSET + 28..SECTION_OFFSET + 32].copy_from_slice(&(0u32).to_le_bytes());

        bytes[DATA_OFFSET as usize..DATA_OFFSET as usize + DATA_SIZE as usize].fill(0x7c);

        let pointer_offset = FILE_LEN - 0x20;
        bytes[pointer_offset..pointer_offset + 4].copy_from_slice(&0u32.to_le_bytes());

        let path = temp_dir().join(format!("cloud-hypervisor-embedded-payload-{}.fd", id()));
        write(&path, bytes).unwrap();
        let file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();
        file
    }

    #[test]
    fn tdvf_embedded_payload_metadata_and_bytes_are_accepted() {
        let mut file = fixture();
        let (sections, _) = parse_tdvf_sections(&mut file).unwrap();
        assert_eq!(sections.len(), 1);
        let section = sections[0];
        let data_offset = section.data_offset;
        let data_size = section.data_size;
        let address = section.address;
        let memory_size = section.size;
        let section_type = section.r#type;
        println!(
            "TDVF_EMBEDDED_PAYLOAD_PARSE offset=0x{data_offset:x} raw=0x{data_size:x} address=0x{address:x} memory=0x{memory_size:x} type={section_type:?}"
        );
        assert!(matches!(section_type, TdvfSectionType::Payload));
        assert_eq!(data_offset, DATA_OFFSET);
        assert_eq!(data_size, DATA_SIZE);
        assert_eq!(address, ADDRESS);
        assert_eq!(memory_size, MEMORY_SIZE);

        file.seek(SeekFrom::Start(u64::from(data_offset))).unwrap();
        let mut raw = vec![0u8; data_size as usize];
        file.read_exact(&mut raw).unwrap();
        println!("TDVF_EMBEDDED_PAYLOAD_BYTES len={} first=0x{:02x} last=0x{:02x}", raw.len(), raw[0], raw[raw.len() - 1]);
        assert_eq!(raw, vec![0x7c; DATA_SIZE as usize]);
    }
}

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
