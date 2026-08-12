#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/vm.rs")
text = path.read_text()
marker = "copy_tdx_firmware_section"
if marker in text:
    raise SystemExit(f"candidate marker already present in {path}")

old_fn = '''    #[cfg(feature = "tdx")]
    fn populate_tdx_sections(
'''
new_fn = '''    #[cfg(feature = "tdx")]
    fn copy_tdx_firmware_section(
        mem: &GuestMemoryMmap,
        firmware_file: &mut File,
        address: u64,
        size: usize,
    ) -> Result<usize> {
        mem.read_volatile_from(GuestAddress(address), firmware_file, size)
            .map_err(Error::FirmwareLoad)
    }

    #[cfg(feature = "tdx")]
    fn populate_tdx_sections(
'''
if text.count(old_fn) != 1:
    raise SystemExit("unexpected populate_tdx_sections anchor count")
text = text.replace(old_fn, new_fn, 1)

old_copy = '''                    mem.read_volatile_from(
                        GuestAddress(section.address),
                        &mut firmware_file,
                        section.data_size as usize,
                    )
                    .unwrap();
'''
new_copy = '''                    Self::copy_tdx_firmware_section(
                        &mem,
                        &mut firmware_file,
                        section.address,
                        section.data_size as usize,
                    )?;
'''
if text.count(old_copy) != 1:
    raise SystemExit("unexpected BFV/CFV copy boundary count")
text = text.replace(old_copy, new_copy, 1)

anchor = '''    #[cfg(feature = "tdx")]
    #[test]
    fn test_hob_memory_resources() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDX unit-test anchor count")

test = r'''    #[cfg(feature = "tdx")]
    #[test]
    fn tdx_firmware_copy_propagates_guest_memory_error() {
        use std::env::temp_dir;
        use std::fs::{OpenOptions, remove_file, write};
        use std::process::id;

        let path = temp_dir().join(format!("cloud-hypervisor-tdvf-firmware-candidate-{}.fd", id()));
        write(&path, [0x5au8; 64]).unwrap();
        let mut file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();

        let mem = GuestMemoryMmap::from_ranges(&[(GuestAddress(0), 0x1000)]).unwrap();
        let err = Vm::copy_tdx_firmware_section(&mem, &mut file, 0x2000, 16).unwrap_err();
        println!("TDVF_FIRMWARE_DEST_CANDIDATE invalid_result={err:?}");
        assert!(matches!(err, Error::FirmwareLoad(_)));

        file.rewind().unwrap();
        let copied = Vm::copy_tdx_firmware_section(&mem, &mut file, 0x800, 16).unwrap();
        let mut buf = [0u8; 16];
        mem.read_slice(&mut buf, GuestAddress(0x800)).unwrap();
        println!("TDVF_FIRMWARE_DEST_CANDIDATE copied={copied} bytes={buf:?}");
        assert_eq!(copied, 16);
        assert_eq!(buf, [0x5a; 16]);
    }

'''
text = text.replace(anchor, test + anchor, 1)
path.write_text(text)
