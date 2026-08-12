#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/vm.rs")
text = path.read_text()
marker = "tdvf_firmware_short_source_is_success_baseline"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = '''    #[cfg(feature = "tdx")]
    #[test]
    fn test_hob_memory_resources() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDX unit-test anchor count")

probe = r'''    #[cfg(feature = "tdx")]
    fn short_read_fixture(len: usize, byte: u8) -> File {
        use std::env::temp_dir;
        use std::fs::{OpenOptions, remove_file, write};
        use std::process::id;

        let path = temp_dir().join(format!(
            "cloud-hypervisor-tdvf-short-read-{}-{len}.fd",
            id()
        ));
        write(&path, vec![byte; len]).unwrap();
        let file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();
        file
    }

    #[cfg(feature = "tdx")]
    fn current_tdvf_nonexact_copy(
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
    fn tdvf_firmware_exact_length_control() {
        let mem = GuestMemoryMmap::from_ranges(&[(GuestAddress(0), 0x1000)]).unwrap();
        let mut file = short_read_fixture(16, 0x5a);
        let copied = current_tdvf_nonexact_copy(&mem, &mut file, 0x800, 16);
        let mut buf = [0u8; 16];
        mem.read_slice(&mut buf, GuestAddress(0x800)).unwrap();
        println!("TDVF_SHORT_READ_CONTROL requested=16 copied={copied} bytes={buf:?}");
        assert_eq!(copied, 16);
        assert_eq!(buf, [0x5a; 16]);
    }

    #[cfg(feature = "tdx")]
    #[test]
    #[ignore]
    fn tdvf_firmware_short_source_is_success_baseline() {
        let mem = GuestMemoryMmap::from_ranges(&[(GuestAddress(0), 0x1000)]).unwrap();
        let mut file = short_read_fixture(8, 0x5a);
        let copied = current_tdvf_nonexact_copy(&mem, &mut file, 0x800, 16);
        let mut buf = [0u8; 16];
        mem.read_slice(&mut buf, GuestAddress(0x800)).unwrap();
        println!("TDVF_SHORT_READ_BASELINE requested=16 copied={copied} bytes={buf:?}");
        assert_eq!(copied, 8);
        assert_eq!(&buf[..8], &[0x5a; 8]);
        assert_eq!(&buf[8..], &[0; 8]);
    }

    #[cfg(feature = "tdx")]
    #[test]
    fn tdvf_firmware_short_source_must_not_succeed_partially() {
        let mem = GuestMemoryMmap::from_ranges(&[(GuestAddress(0), 0x1000)]).unwrap();
        let mut file = short_read_fixture(8, 0x5a);
        let copied = current_tdvf_nonexact_copy(&mem, &mut file, 0x800, 16);
        println!("TDVF_SHORT_READ_INVARIANT requested=16 copied={copied}");
        assert_eq!(copied, 16, "BFV/CFV copy must not silently accept a short source");
    }

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
