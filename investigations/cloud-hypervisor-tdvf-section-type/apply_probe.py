#!/usr/bin/env python3
from pathlib import Path

path = Path("arch/src/x86_64/tdx/mod.rs")
text = path.read_text()
marker = "tdvf_unknown_section_type_miri_baseline"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = '''    #[test]
    #[ignore]
    fn test_parse_tdvf_sections() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDVF unit-test anchor count")

probe = r'''    fn section_type_fixture(raw_type: u32) -> File {
        use std::env::temp_dir;
        use std::fs::{OpenOptions, remove_file, write};
        use std::process::id;

        const FILE_LEN: usize = 0x100;
        const SECTION_OFFSET: usize = 16;

        assert_eq!(size_of::<TdvfDescriptor>(), 16);
        assert_eq!(size_of::<TdvfSection>(), 32);

        let mut bytes = vec![0u8; FILE_LEN];
        bytes[0..4].copy_from_slice(b"TDVF");
        bytes[4..8].copy_from_slice(&(48u32).to_le_bytes());
        bytes[8..12].copy_from_slice(&(1u32).to_le_bytes());
        bytes[12..16].copy_from_slice(&(1u32).to_le_bytes());

        bytes[SECTION_OFFSET..SECTION_OFFSET + 4].copy_from_slice(&(0x40u32).to_le_bytes());
        bytes[SECTION_OFFSET + 4..SECTION_OFFSET + 8].copy_from_slice(&(0x20u32).to_le_bytes());
        bytes[SECTION_OFFSET + 8..SECTION_OFFSET + 16].copy_from_slice(&(0x1000u64).to_le_bytes());
        bytes[SECTION_OFFSET + 16..SECTION_OFFSET + 24]
            .copy_from_slice(&(0x1000u64).to_le_bytes());
        bytes[SECTION_OFFSET + 24..SECTION_OFFSET + 28].copy_from_slice(&raw_type.to_le_bytes());
        bytes[SECTION_OFFSET + 28..SECTION_OFFSET + 32].copy_from_slice(&0u32.to_le_bytes());

        // Deprecated metadata pointer lives 32 bytes from EOF. Zero points to the descriptor.
        bytes[FILE_LEN - 0x20..FILE_LEN - 0x1c].copy_from_slice(&0u32.to_le_bytes());

        let path = temp_dir().join(format!(
            "cloud-hypervisor-tdvf-section-type-{}-{raw_type:x}.fd",
            id()
        ));
        write(&path, bytes).unwrap();
        let file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();
        file
    }

    #[test]
    fn tdvf_known_section_type_control() {
        let mut file = section_type_fixture(0);
        let (sections, _) = parse_tdvf_sections(&mut file).unwrap();
        let section_type = sections[0].r#type;
        println!("TDVF_TYPE_CONTROL section_type={section_type:?}");
        assert!(matches!(section_type, TdvfSectionType::Bfv));
    }

    // This test must only be executed under Miri. Exact-current parse_tdvf_sections() writes
    // untrusted bytes directly over TdvfSection, whose type field is a Rust enum. A normal
    // execution with an unknown discriminant would itself invoke undefined behavior.
    #[test]
    #[ignore]
    fn tdvf_unknown_section_type_miri_baseline() {
        let raw_type = 7u32;
        println!("TDVF_TYPE_MIRI_INPUT raw_type={raw_type}");
        let mut file = section_type_fixture(raw_type);
        let (sections, _) = parse_tdvf_sections(&mut file).unwrap();
        let section_type = sections[0].r#type;
        std::hint::black_box(section_type);
        panic!("Miri should reject the invalid enum discriminant before this point");
    }

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
