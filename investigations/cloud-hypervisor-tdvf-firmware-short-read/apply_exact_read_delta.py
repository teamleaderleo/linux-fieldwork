#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/vm.rs")
text = path.read_text()
marker = "tdx_firmware_exact_read_rejects_partial_source"
if marker in text:
    raise SystemExit(f"exact-read marker already present in {path}")

old_helper = '''    #[cfg(feature = "tdx")]
    fn copy_tdx_firmware_section(
        mem: &GuestMemoryMmap,
        firmware_file: &mut File,
        address: u64,
        size: usize,
    ) -> Result<usize> {
        mem.read_volatile_from(GuestAddress(address), firmware_file, size)
            .map_err(Error::FirmwareLoad)
    }
'''
new_helper = '''    #[cfg(feature = "tdx")]
    fn copy_tdx_firmware_section(
        mem: &GuestMemoryMmap,
        firmware_file: &mut File,
        address: u64,
        size: usize,
    ) -> Result<()> {
        mem.read_exact_volatile_from(GuestAddress(address), firmware_file, size)
            .map_err(Error::FirmwareLoad)
    }
'''
if text.count(old_helper) != 1:
    raise SystemExit("expected exactly one R590D firmware-copy helper")
text = text.replace(old_helper, new_helper, 1)

old_control = '''        file.rewind().unwrap();
        let copied = Vm::copy_tdx_firmware_section(&mem, &mut file, 0x800, 16).unwrap();
        let mut buf = [0u8; 16];
        mem.read_slice(&mut buf, GuestAddress(0x800)).unwrap();
        println!("TDVF_FIRMWARE_DEST_CANDIDATE copied={copied} bytes={buf:?}");
        assert_eq!(copied, 16);
        assert_eq!(buf, [0x5a; 16]);
'''
new_control = '''        file.rewind().unwrap();
        Vm::copy_tdx_firmware_section(&mem, &mut file, 0x800, 16).unwrap();
        let mut buf = [0u8; 16];
        mem.read_slice(&mut buf, GuestAddress(0x800)).unwrap();
        println!("TDVF_FIRMWARE_DEST_CANDIDATE exact_bytes={buf:?}");
        assert_eq!(buf, [0x5a; 16]);
'''
if text.count(old_control) != 1:
    raise SystemExit("expected exactly one R590D successful-copy regression block")
text = text.replace(old_control, new_control, 1)

anchor = '''    #[cfg(feature = "tdx")]
    #[test]
    fn test_hob_memory_resources() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDX unit-test anchor count")

test = r'''    #[cfg(feature = "tdx")]
    #[test]
    fn tdx_firmware_exact_read_rejects_partial_source() {
        use std::env::temp_dir;
        use std::fs::{OpenOptions, remove_file, write};
        use std::process::id;

        let mem = GuestMemoryMmap::from_ranges(&[(GuestAddress(0), 0x1000)]).unwrap();
        let path = temp_dir().join(format!("cloud-hypervisor-tdvf-exact-read-{}.fd", id()));
        write(&path, [0x5au8; 8]).unwrap();
        let mut file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();

        let err = Vm::copy_tdx_firmware_section(&mem, &mut file, 0x800, 16).unwrap_err();
        println!("TDVF_SHORT_READ_CANDIDATE short_result={err:?}");
        assert!(matches!(
            err,
            Error::FirmwareLoad(vm_memory::GuestMemoryError::PartialBuffer {
                expected: 16,
                completed: 8,
            })
        ));

        let path = temp_dir().join(format!("cloud-hypervisor-tdvf-exact-control-{}.fd", id()));
        write(&path, [0x5au8; 16]).unwrap();
        let mut file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();
        Vm::copy_tdx_firmware_section(&mem, &mut file, 0x900, 16).unwrap();
        let mut buf = [0u8; 16];
        mem.read_slice(&mut buf, GuestAddress(0x900)).unwrap();
        println!("TDVF_SHORT_READ_CANDIDATE control_bytes={buf:?}");
        assert_eq!(buf, [0x5a; 16]);
    }

'''
text = text.replace(anchor, test + anchor, 1)
path.write_text(text)
