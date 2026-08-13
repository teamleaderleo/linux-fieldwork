#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/vm.rs")
text = path.read_text()
marker = "tdx_payload_header_directory_read_panics_baseline"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = '''    #[cfg(feature = "tdx")]
    #[test]
    fn test_hob_memory_resources() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDX unit-test anchor count")

probe = r'''    #[cfg(feature = "tdx")]
    fn current_tdx_payload_header_read(payload_file: &mut File) -> bootparam::setup_header {
        payload_file.seek(SeekFrom::Start(0x1f1)).unwrap();
        let mut payload_header = bootparam::setup_header::default();
        payload_file
            .read_volatile(&mut payload_header.as_bytes())
            .unwrap();
        payload_header
    }

    #[cfg(feature = "tdx")]
    fn payload_header_regular_file() -> File {
        use std::env::temp_dir;
        use std::fs::{OpenOptions, remove_file, write};
        use std::process::id;

        let len = 0x1f1 + std::mem::size_of::<bootparam::setup_header>() + 16;
        let path = temp_dir().join(format!("cloud-hypervisor-tdx-payload-header-{}.bin", id()));
        write(&path, vec![0u8; len]).unwrap();
        let file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();
        file
    }

    #[cfg(feature = "tdx")]
    #[test]
    fn tdx_payload_header_regular_file_control() {
        let mut file = payload_header_regular_file();
        let _header = current_tdx_payload_header_read(&mut file);
        println!("TDX_PAYLOAD_HEADER_CONTROL regular_file_read=ok");
    }

    #[cfg(feature = "tdx")]
    #[test]
    #[ignore]
    fn tdx_payload_header_directory_read_panics_baseline() {
        use std::env::temp_dir;
        use std::fs::{File, create_dir, remove_dir};
        use std::process::id;

        let path = temp_dir().join(format!("cloud-hypervisor-tdx-payload-header-dir-{}", id()));
        create_dir(&path).unwrap();
        let mut file = File::open(&path).unwrap();
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            let _ = current_tdx_payload_header_read(&mut file);
        }));
        remove_dir(path).unwrap();
        println!("TDX_PAYLOAD_HEADER_BASELINE panicked={}", result.is_err());
        assert!(result.is_err());
    }

    #[cfg(feature = "tdx")]
    #[test]
    fn tdx_payload_header_directory_read_must_not_panic() {
        use std::env::temp_dir;
        use std::fs::{File, create_dir, remove_dir};
        use std::process::id;

        let path = temp_dir().join(format!("cloud-hypervisor-tdx-payload-header-invariant-{}", id()));
        create_dir(&path).unwrap();
        let mut file = File::open(&path).unwrap();
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            let _ = current_tdx_payload_header_read(&mut file);
        }));
        remove_dir(path).unwrap();
        println!("TDX_PAYLOAD_HEADER_INVARIANT panicked={}", result.is_err());
        assert!(
            result.is_ok(),
            "TDX Payload setup-header read error must not panic the VMM"
        );
    }

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
