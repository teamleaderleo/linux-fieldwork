#!/usr/bin/env python3
from pathlib import Path

path = Path("arch/src/x86_64/tdx/mod.rs")
text = path.read_text()
marker = "tdvf_raw_data_larger_than_memory_is_accepted_baseline"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = "#[cfg(test)]\nmod unit_tests {"
if text.count(anchor) != 1:
    raise SystemExit(f"expected exactly one TDX unit-test anchor in {path}")

probe = r'''#[cfg(test)]
mod data_memory_size_probe_tests {
    use std::env::temp_dir;
    use std::fs::{OpenOptions, remove_file, write};
    use std::process::id;

    use super::*;

    const FILE_LEN: usize = 0x4000;
    const SECTION_OFFSET: usize = 16;
    const DATA_OFFSET: u32 = 0x1000;
    const DATA_SIZE: u32 = 0x2000;
    const ADDRESS: u64 = 0x10_0000;

    fn fixture(memory_size: u64) -> File {
        assert_eq!(size_of::<TdvfDescriptor>(), 16);
        assert_eq!(size_of::<TdvfSection>(), 32);

        let mut bytes = vec![0u8; FILE_LEN];
        bytes[0..4].copy_from_slice(b"TDVF");
        bytes[4..8].copy_from_slice(&(48u32).to_le_bytes());
        bytes[8..12].copy_from_slice(&(1u32).to_le_bytes());
        bytes[12..16].copy_from_slice(&(1u32).to_le_bytes());

        bytes[SECTION_OFFSET..SECTION_OFFSET + 4].copy_from_slice(&DATA_OFFSET.to_le_bytes());
        bytes[SECTION_OFFSET + 4..SECTION_OFFSET + 8].copy_from_slice(&DATA_SIZE.to_le_bytes());
        bytes[SECTION_OFFSET + 8..SECTION_OFFSET + 16].copy_from_slice(&ADDRESS.to_le_bytes());
        bytes[SECTION_OFFSET + 16..SECTION_OFFSET + 24]
            .copy_from_slice(&memory_size.to_le_bytes());
        // TdvfSectionType::Bfv == 0, attributes == 0.

        let data_start = DATA_OFFSET as usize;
        let data_end = data_start + DATA_SIZE as usize;
        bytes[data_start..data_end].fill(0x5a);

        // Deprecated metadata pointer 32 bytes from EOF points to descriptor at offset 0.
        let pointer_offset = FILE_LEN - 0x20;
        bytes[pointer_offset..pointer_offset + 4].copy_from_slice(&0u32.to_le_bytes());

        let path = temp_dir().join(format!(
            "cloud-hypervisor-tdvf-data-memory-{}-{memory_size:x}.fd",
            id()
        ));
        write(&path, bytes).unwrap();
        let file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();
        file
    }

    #[test]
    #[ignore]
    fn tdvf_raw_data_larger_than_memory_is_accepted_baseline() {
        let mut file = fixture(0x1000);
        let (sections, _) = parse_tdvf_sections(&mut file).unwrap();
        let section = sections[0];
        let data_size = section.data_size;
        let memory_size = section.size;
        let address = section.address;
        let data_offset = section.data_offset;
        println!(
            "TDVF_DATA_MEMORY_BASELINE data_size=0x{data_size:x} memory_size=0x{memory_size:x}"
        );
        assert_eq!(data_size, DATA_SIZE);
        assert_eq!(memory_size, 0x1000);

        let mem = GuestMemoryMmap::from_ranges(&[(GuestAddress(address), 0x4000)]).unwrap();
        file.seek(SeekFrom::Start(data_offset as u64)).unwrap();
        let copied = mem
            .read_volatile_from(GuestAddress(address), &mut file, data_size as usize)
            .unwrap();
        let beyond_declared: u8 = mem
            .read_obj(GuestAddress(address + memory_size))
            .unwrap();
        println!(
            "TDVF_DATA_MEMORY_BASELINE copied=0x{copied:x} byte_at_declared_end=0x{beyond_declared:02x}"
        );
        assert_eq!(copied, DATA_SIZE as usize);
        assert_eq!(beyond_declared, 0x5a);
    }

    #[test]
    fn tdvf_raw_data_must_fit_declared_memory() {
        let mut file = fixture(0x1000);
        let result = parse_tdvf_sections(&mut file);
        println!("TDVF_DATA_MEMORY_INVARIANT result={result:?}");
        assert!(
            result.is_err(),
            "TDVF RawDataSize larger than MemoryDataSize must be rejected"
        );
    }

    #[test]
    fn tdvf_raw_data_smaller_than_memory_is_valid() {
        let mut file = fixture(0x3000);
        let (sections, _) = parse_tdvf_sections(&mut file).unwrap();
        let section = sections[0];
        let data_size = section.data_size;
        let memory_size = section.size;
        println!(
            "TDVF_DATA_MEMORY_CONTROL data_size=0x{data_size:x} memory_size=0x{memory_size:x}"
        );
        assert_eq!(data_size, DATA_SIZE);
        assert_eq!(memory_size, 0x3000);
    }
}

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
