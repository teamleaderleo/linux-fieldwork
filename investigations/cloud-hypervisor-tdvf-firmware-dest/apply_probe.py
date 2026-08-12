#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/vm.rs")
text = path.read_text()
marker = "tdvf_firmware_invalid_guest_address_panics_baseline"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = '''    #[cfg(feature = "tdx")]
    #[test]
    fn test_hob_memory_resources() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDX unit-test anchor count")

probe = r'''    #[cfg(feature = "tdx")]
    fn firmware_copy_fixture() -> File {
        use std::env::temp_dir;
        use std::fs::{OpenOptions, remove_file, write};
        use std::process::id;

        let path = temp_dir().join(format!("cloud-hypervisor-tdvf-firmware-dest-{}.fd", id()));
        write(&path, [0x5au8; 64]).unwrap();
        let file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();
        file
    }

    #[cfg(feature = "tdx")]
    fn current_tdvf_firmware_copy(
        mem: &GuestMemoryMmap,
        file: &mut File,
        address: u64,
        size: usize,
    ) -> usize {
        mem.read_volatile_from(GuestAddress(address), file, size)
            .unwrap()
    }

    #[cfg(feature = "tdx")]
    #[test]
    fn tdvf_firmware_valid_guest_address_control() {
        let mem = GuestMemoryMmap::from_ranges(&[(GuestAddress(0), 0x1000)]).unwrap();
        let mut file = firmware_copy_fixture();
        let copied = current_tdvf_firmware_copy(&mem, &mut file, 0x800, 16);
        let mut buf = [0u8; 16];
        mem.read_slice(&mut buf, GuestAddress(0x800)).unwrap();
        println!("TDVF_FIRMWARE_DEST_CONTROL copied={copied} bytes={buf:?}");
        assert_eq!(copied, 16);
        assert_eq!(buf, [0x5a; 16]);
    }

    #[cfg(feature = "tdx")]
    #[test]
    #[ignore]
    fn tdvf_firmware_invalid_guest_address_panics_baseline() {
        let mem = GuestMemoryMmap::from_ranges(&[(GuestAddress(0), 0x1000)]).unwrap();
        let mut file = firmware_copy_fixture();
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            current_tdvf_firmware_copy(&mem, &mut file, 0x2000, 16);
        }));
        println!("TDVF_FIRMWARE_DEST_BASELINE panicked={}", result.is_err());
        assert!(result.is_err());
    }

    #[cfg(feature = "tdx")]
    #[test]
    fn tdvf_firmware_invalid_guest_address_should_not_panic() {
        let mem = GuestMemoryMmap::from_ranges(&[(GuestAddress(0), 0x1000)]).unwrap();
        let mut file = firmware_copy_fixture();
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            current_tdvf_firmware_copy(&mem, &mut file, 0x2000, 16);
        }));
        println!("TDVF_FIRMWARE_DEST_INVARIANT panicked={}", result.is_err());
        assert!(
            result.is_ok(),
            "invalid BFV/CFV guest destination must not panic the VMM"
        );
    }

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
