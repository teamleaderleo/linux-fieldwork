#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/vm.rs")
text = path.read_text()
marker = "tdx_payload_truncated_setup_is_accepted_baseline"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = '''    #[cfg(feature = "tdx")]
    #[test]
    fn test_hob_memory_resources() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDX unit-test anchor count")

probe = r'''    #[cfg(feature = "tdx")]
    fn tdx_setup_size_fixture(len: usize) -> File {
        use std::env::temp_dir;
        use std::fs::{OpenOptions, remove_file, write};
        use std::process::id;

        assert!(len >= 0x212);
        let mut bytes = vec![0u8; len];
        bytes[0x1f1] = 0; // Protocol default: 4 setup sectors.
        bytes[0x202..0x206].copy_from_slice(&0x5372_6448u32.to_le_bytes());
        bytes[0x206..0x208].copy_from_slice(&0x0200u16.to_le_bytes());
        bytes[0x211] = 1; // LOAD_HIGH.

        let path = temp_dir().join(format!(
            "cloud-hypervisor-tdx-payload-setup-size-{}-{len:x}.bin",
            id()
        ));
        write(&path, bytes).unwrap();
        let file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();
        file
    }

    #[cfg(feature = "tdx")]
    fn current_tdx_payload_header_accepts(payload_file: &mut File) -> bool {
        payload_file.seek(SeekFrom::Start(0x1f1)).unwrap();
        let mut payload_header = bootparam::setup_header::default();
        payload_file
            .read_volatile(&mut payload_header.as_bytes())
            .unwrap();
        payload_header.header == 0x5372_6448
            && payload_header.version >= 0x0200
            && (payload_header.loadflags & 0x1) != 0
    }

    #[cfg(feature = "tdx")]
    fn protocol_setup_size(setup_sects: u8) -> u64 {
        let sectors = if setup_sects == 0 {
            4
        } else {
            u64::from(setup_sects)
        };
        (sectors + 1) * 512
    }

    #[cfg(feature = "tdx")]
    #[test]
    #[ignore]
    fn tdx_payload_truncated_setup_is_accepted_baseline() {
        let mut file = tdx_setup_size_fixture(0x212);
        let payload_size = file.seek(SeekFrom::End(0)).unwrap();
        let accepted = current_tdx_payload_header_accepts(&mut file);
        let setup_size = protocol_setup_size(0);
        println!(
            "TDX_PAYLOAD_SETUP_BASELINE payload_size=0x{payload_size:x} setup_size=0x{setup_size:x} accepted={accepted}"
        );
        assert!(accepted);
        assert!(payload_size < setup_size);
    }

    #[cfg(feature = "tdx")]
    #[test]
    fn pinned_linux_loader_rejects_truncated_setup_control() {
        use linux_loader::loader::KernelLoader;
        use linux_loader::loader::bzimage::{BzImage, Error as BzImageError};
        use linux_loader::loader::Error as LoaderError;

        let mem = GuestMemoryMmap::from_ranges(&[(GuestAddress(0), 0x20_0000)]).unwrap();
        let mut file = tdx_setup_size_fixture(0x212);
        let err = BzImage::load(
            &mem,
            Some(GuestAddress(0x10_0000)),
            &mut file,
            None,
        )
        .unwrap_err();
        println!("TDX_PAYLOAD_SETUP_CONTROL linux_loader_result={err:?}");
        assert_eq!(err, LoaderError::Bzimage(BzImageError::Underflow));
    }

    #[cfg(feature = "tdx")]
    #[test]
    fn tdx_payload_valid_setup_size_control() {
        let mut file = tdx_setup_size_fixture(0xa00);
        let payload_size = file.seek(SeekFrom::End(0)).unwrap();
        let accepted = current_tdx_payload_header_accepts(&mut file);
        let setup_size = protocol_setup_size(0);
        println!(
            "TDX_PAYLOAD_SETUP_CONTROL payload_size=0x{payload_size:x} setup_size=0x{setup_size:x} accepted={accepted}"
        );
        assert!(accepted);
        assert_eq!(payload_size, setup_size);
    }

    #[cfg(feature = "tdx")]
    #[test]
    fn tdx_payload_setup_area_must_fit_file() {
        let mut file = tdx_setup_size_fixture(0x212);
        let payload_size = file.seek(SeekFrom::End(0)).unwrap();
        let accepted = current_tdx_payload_header_accepts(&mut file);
        let setup_size = protocol_setup_size(0);
        println!(
            "TDX_PAYLOAD_SETUP_INVARIANT payload_size=0x{payload_size:x} setup_size=0x{setup_size:x} accepted={accepted}"
        );
        assert!(
            !accepted || payload_size >= setup_size,
            "TDX bzImage payload must not pass header checks when its setup area is truncated"
        );
    }

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
