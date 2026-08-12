#!/usr/bin/env python3
from pathlib import Path

path = Path("arch/src/x86_64/tdx/mod.rs")
text = path.read_text()
marker = "tdvf_giant_truncated_section_table_allocation_baseline"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = '''    #[test]
    #[ignore]
    fn test_parse_tdvf_sections() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDVF unit-test anchor count")

probe = r'''    fn truncated_section_table_fixture(num_sections: u32) -> File {
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
        // Deprecated metadata pointer lives 32 bytes from EOF; zero points at descriptor 0.
        bytes[FILE_LEN - 0x20..FILE_LEN - 0x1c].copy_from_slice(&0u32.to_le_bytes());

        let path = temp_dir().join(format!(
            "cloud-hypervisor-tdvf-allocation-{}-{num_sections}.fd",
            id()
        ));
        write(&path, bytes).unwrap();
        let file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();
        file
    }

    fn valid_single_section_fixture() -> File {
        use std::env::temp_dir;
        use std::fs::{OpenOptions, remove_file, write};
        use std::process::id;

        const FILE_LEN: usize = 0x100;
        let mut bytes = vec![0u8; FILE_LEN];
        bytes[0..4].copy_from_slice(b"TDVF");
        bytes[4..8].copy_from_slice(&(48u32).to_le_bytes());
        bytes[8..12].copy_from_slice(&(1u32).to_le_bytes());
        bytes[12..16].copy_from_slice(&(1u32).to_le_bytes());
        // One zero-filled section is a valid BFV record for parser-shape purposes.
        bytes[FILE_LEN - 0x20..FILE_LEN - 0x1c].copy_from_slice(&0u32.to_le_bytes());

        let path = temp_dir().join(format!("cloud-hypervisor-tdvf-allocation-control-{}.fd", id()));
        write(&path, bytes).unwrap();
        let file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();
        file
    }

    #[test]
    fn tdvf_section_table_in_file_control() {
        let mut file = valid_single_section_fixture();
        let (sections, _) = parse_tdvf_sections(&mut file).unwrap();
        println!("TDVF_ALLOC_CONTROL sections={}", sections.len());
        assert_eq!(sections.len(), 1);
    }

    #[test]
    fn tdvf_truncated_section_table_should_reject_before_read() {
        // 262,144 entries = 8 MiB of advertised table data, while the file is only 256 bytes.
        let mut file = truncated_section_table_fixture(262_144);
        let result = parse_tdvf_sections(&mut file);
        println!("TDVF_ALLOC_INVARIANT result={result:?}");
        assert!(
            !matches!(result, Err(TdvfError::ReadDescriptor(_))),
            "truncated section table must be rejected before allocating/reading advertised entries"
        );
        assert!(result.is_err());
    }

    #[test]
    #[ignore]
    fn tdvf_giant_truncated_section_table_allocation_baseline() {
        // 33,554,432 entries * 32 bytes = exactly 1 GiB. This test is only run in a
        // subprocess capped to 512 MiB virtual memory, so baseline allocation failure is bounded.
        let num_sections = 33_554_432u32;
        let section_bytes = u64::from(num_sections) * size_of::<TdvfSection>() as u64;
        println!(
            "TDVF_ALLOC_BASELINE_REQUEST num_sections={num_sections} section_bytes={section_bytes}"
        );
        let mut file = truncated_section_table_fixture(num_sections);
        let result = parse_tdvf_sections(&mut file);
        println!("TDVF_ALLOC_BASELINE_UNEXPECTED_RETURN result={result:?}");
        assert!(result.is_err());
    }

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
