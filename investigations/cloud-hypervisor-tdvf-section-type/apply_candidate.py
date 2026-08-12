#!/usr/bin/env python3
from pathlib import Path

path = Path("arch/src/x86_64/tdx/mod.rs")
text = path.read_text()
marker = "Unsupported TDVF section type"
if marker in text:
    raise SystemExit(f"candidate marker already present in {path}")

old_error = '''    #[error("Invalid descriptor version")]
    InvalidDescriptorVersion,
'''
new_error = old_error + '''    #[error("Unsupported TDVF section type {0:#x}")]
    InvalidSectionType(u32),
'''
if text.count(old_error) != 1:
    raise SystemExit("unexpected TDVF error anchor count")
text = text.replace(old_error, new_error, 1)

old_section = '''// TDVF_SECTION
#[repr(C, packed)]
#[derive(Clone, Copy, Default, Debug)]
pub struct TdvfSection {
    pub data_offset: u32,
    pub data_size: u32, // RawDataSize
    pub address: u64,   // MemoryAddress
    pub size: u64,      // MemoryDataSize
    pub r#type: TdvfSectionType,
    pub attributes: u32,
}

#[repr(u32)]
#[derive(Clone, Copy, Debug, Default)]
pub enum TdvfSectionType {
    Bfv,
    Cfv,
    TdHob,
    TempMem,
    PermMem,
    Payload,
    PayloadParam,
    #[default]
    Reserved = 0xffffffff,
}
'''
new_section = '''// TDVF_SECTION wire representation. Keep untrusted type bytes as an integer until validated.
#[repr(C, packed)]
#[derive(Clone, Copy, Default)]
struct RawTdvfSection {
    data_offset: u32,
    data_size: u32,
    address: u64,
    size: u64,
    r#type: u32,
    attributes: u32,
}

// Validated TDVF section used by the rest of the VMM.
#[repr(C, packed)]
#[derive(Clone, Copy, Default, Debug)]
pub struct TdvfSection {
    pub data_offset: u32,
    pub data_size: u32, // RawDataSize
    pub address: u64,   // MemoryAddress
    pub size: u64,      // MemoryDataSize
    pub r#type: TdvfSectionType,
    pub attributes: u32,
}

#[repr(u32)]
#[derive(Clone, Copy, Debug, Default)]
pub enum TdvfSectionType {
    Bfv,
    Cfv,
    TdHob,
    TempMem,
    PermMem,
    Payload,
    PayloadParam,
    #[default]
    Reserved = 0xffffffff,
}

impl TryFrom<u32> for TdvfSectionType {
    type Error = TdvfError;

    fn try_from(value: u32) -> Result<Self, Self::Error> {
        match value {
            0 => Ok(Self::Bfv),
            1 => Ok(Self::Cfv),
            2 => Ok(Self::TdHob),
            3 => Ok(Self::TempMem),
            4 => Ok(Self::PermMem),
            5 => Ok(Self::Payload),
            6 => Ok(Self::PayloadParam),
            0xffff_ffff => Ok(Self::Reserved),
            _ => Err(TdvfError::InvalidSectionType(value)),
        }
    }
}

impl TryFrom<RawTdvfSection> for TdvfSection {
    type Error = TdvfError;

    fn try_from(raw: RawTdvfSection) -> Result<Self, Self::Error> {
        let raw_type = raw.r#type;
        Ok(Self {
            data_offset: raw.data_offset,
            data_size: raw.data_size,
            address: raw.address,
            size: raw.size,
            r#type: TdvfSectionType::try_from(raw_type)?,
            attributes: raw.attributes,
        })
    }
}
'''
if text.count(old_section) != 1:
    raise SystemExit("unexpected TDVF section definition block count")
text = text.replace(old_section, new_section, 1)

old_parse = '''    let mut sections = Vec::new();
    sections.resize_with(descriptor.num_sections as usize, TdvfSection::default);

    // SAFETY: we read exactly the advertised sections
    file.read_exact(unsafe {
        slice::from_raw_parts_mut(
            sections.as_mut_ptr().cast(),
            descriptor.num_sections as usize * size_of::<TdvfSection>(),
        )
    })
    .map_err(TdvfError::ReadDescriptor)?;

    Ok((sections, guid_found))
'''
new_parse = '''    let mut raw_sections = Vec::new();
    raw_sections.resize_with(descriptor.num_sections as usize, RawTdvfSection::default);

    // SAFETY: RawTdvfSection contains only integer fields, so every fully initialized bit pattern
    // is a valid Rust value. The numeric section type is validated before constructing TdvfSection.
    file.read_exact(unsafe {
        slice::from_raw_parts_mut(
            raw_sections.as_mut_ptr().cast(),
            descriptor.num_sections as usize * size_of::<RawTdvfSection>(),
        )
    })
    .map_err(TdvfError::ReadDescriptor)?;

    let sections = raw_sections
        .into_iter()
        .map(TdvfSection::try_from)
        .collect::<Result<Vec<_>, _>>()?;

    Ok((sections, guid_found))
'''
if text.count(old_parse) != 1:
    raise SystemExit("unexpected TDVF section read block count")
text = text.replace(old_parse, new_parse, 1)

anchor = '''    #[test]
    #[ignore]
    fn test_parse_tdvf_sections() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDVF unit-test anchor count")

test = r'''    fn candidate_section_type_fixture(raw_type: u32) -> File {
        use std::env::temp_dir;
        use std::fs::{OpenOptions, remove_file, write};
        use std::process::id;

        const FILE_LEN: usize = 0x100;
        const SECTION_OFFSET: usize = 16;

        assert_eq!(size_of::<RawTdvfSection>(), size_of::<TdvfSection>());

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
        bytes[FILE_LEN - 0x20..FILE_LEN - 0x1c].copy_from_slice(&0u32.to_le_bytes());

        let path = temp_dir().join(format!(
            "cloud-hypervisor-tdvf-section-type-candidate-{}-{raw_type:x}.fd",
            id()
        ));
        write(&path, bytes).unwrap();
        let file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();
        file
    }

    #[test]
    fn tdvf_unknown_section_type_is_rejected() {
        let mut file = candidate_section_type_fixture(7);
        let err = parse_tdvf_sections(&mut file).unwrap_err();
        println!("TDVF_TYPE_CANDIDATE invalid_result={err:?}");
        assert!(matches!(err, TdvfError::InvalidSectionType(7)));
    }

    #[test]
    fn tdvf_known_and_reserved_section_types_are_validated() {
        for raw_type in [0u32, 1, 2, 3, 4, 5, 6, 0xffff_ffff] {
            let mut file = candidate_section_type_fixture(raw_type);
            let (sections, _) = parse_tdvf_sections(&mut file).unwrap();
            let section_type = sections[0].r#type;
            println!("TDVF_TYPE_CANDIDATE control raw_type={raw_type:#x} type={section_type:?}");
        }
    }

'''
text = text.replace(anchor, test + anchor, 1)

path.write_text(text)
