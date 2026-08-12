#!/usr/bin/env python3
from pathlib import Path

path = Path("arch/src/x86_64/tdx/mod.rs")
text = path.read_text()
marker = "TDVF raw section range exceeds firmware file"
if marker in text:
    raise SystemExit(f"candidate marker already present in {path}")

old_error = '''    #[error("Failed read TDVF descriptor")]
    ReadDescriptor(#[source] io::Error),
'''
new_error = old_error + '''    #[error("Failed to read TDVF firmware file metadata")]
    ReadFileMetadata(#[source] io::Error),
    #[error(
        "TDVF raw section range exceeds firmware file: offset={offset:#x}, size={size:#x}, file_len={file_len:#x}"
    )]
    InvalidSectionFileRange {
        offset: u64,
        size: u64,
        file_len: u64,
    },
'''
if text.count(old_error) != 1:
    raise SystemExit("unexpected ReadDescriptor error block count")
text = text.replace(old_error, new_error, 1)

old_return = '''    file.read_exact(unsafe {
        slice::from_raw_parts_mut(
            sections.as_mut_ptr().cast(),
            descriptor.num_sections as usize * size_of::<TdvfSection>(),
        )
    })
    .map_err(TdvfError::ReadDescriptor)?;

    Ok((sections, guid_found))
'''
new_return = '''    file.read_exact(unsafe {
        slice::from_raw_parts_mut(
            sections.as_mut_ptr().cast(),
            descriptor.num_sections as usize * size_of::<TdvfSection>(),
        )
    })
    .map_err(TdvfError::ReadDescriptor)?;

    let file_len = file
        .metadata()
        .map_err(TdvfError::ReadFileMetadata)?
        .len();
    for section in &sections {
        if matches!(section.r#type, TdvfSectionType::Bfv | TdvfSectionType::Cfv) {
            let offset = u64::from(section.data_offset);
            let size = u64::from(section.data_size);
            if offset + size > file_len {
                return Err(TdvfError::InvalidSectionFileRange {
                    offset,
                    size,
                    file_len,
                });
            }
        }
    }

    Ok((sections, guid_found))
'''
if text.count(old_return) != 1:
    raise SystemExit("unexpected TDVF section read/return block count")
text = text.replace(old_return, new_return, 1)

anchor = '''    #[test]
    #[ignore]
    fn test_parse_tdvf_sections() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected existing TDX test anchor count")

test = r'''    #[test]
    fn raw_bfv_section_must_fit_in_firmware_file() {
        use std::fs::{OpenOptions, remove_file};

        let mut bytes = vec![0u8; 0x100];
        bytes[0..4].copy_from_slice(b"TDVF");
        bytes[4..8].copy_from_slice(&(48u32).to_le_bytes());
        bytes[8..12].copy_from_slice(&(1u32).to_le_bytes());
        bytes[12..16].copy_from_slice(&(1u32).to_le_bytes());
        bytes[16..20].copy_from_slice(&(0x180u32).to_le_bytes());
        bytes[20..24].copy_from_slice(&(0x20u32).to_le_bytes());
        bytes[24..32].copy_from_slice(&(0x1000u64).to_le_bytes());
        bytes[32..40].copy_from_slice(&(0x20u64).to_le_bytes());
        // Bfv type and attributes are both zero.
        bytes[0xe0..0xe4].copy_from_slice(&0u32.to_le_bytes());

        let path = std::env::temp_dir().join(format!(
            "cloud-hypervisor-tdvf-candidate-{}.fd",
            std::process::id()
        ));
        std::fs::write(&path, bytes).unwrap();
        let mut file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();

        let err = parse_tdvf_sections(&mut file).unwrap_err();
        assert!(matches!(
            err,
            TdvfError::InvalidSectionFileRange {
                offset: 0x180,
                size: 0x20,
                file_len: 0x100,
            }
        ));
    }

'''
text = text.replace(anchor, test + anchor, 1)
path.write_text(text)
