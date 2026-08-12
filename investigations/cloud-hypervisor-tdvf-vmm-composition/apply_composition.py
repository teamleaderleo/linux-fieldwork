#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/vm.rs")
text = path.read_text()
marker = "tdx_vmm_composition_preserves_typed_boundaries"
if marker in text:
    raise SystemExit(f"composition marker already present in {path}")

# R590P: typed PayloadParam guest-memory write failure.
old = '''    #[cfg(feature = "tdx")]
    #[error("Error performing I/O on the TDX payload file")]
    LoadPayload(#[source] io::Error),
'''
new = old + '''
    #[cfg(feature = "tdx")]
    #[error("Failed to copy TDX payload parameters to guest memory")]
    LoadPayloadParam(#[source] vm_memory::GuestMemoryError),
'''
if text.count(old) != 1:
    raise SystemExit("unexpected LoadPayload error anchor count")
text = text.replace(old, new, 1)

# R590H: typed missing TdHob failure.
old = '''    #[cfg(feature = "tdx")]
    #[error("TDX firmware missing")]
    TdxFirmwareMissing,
'''
new = old + '''
    #[cfg(feature = "tdx")]
    #[error("TDX firmware missing TD HOB section")]
    TdxHobMissing,
'''
if text.count(old) != 1:
    raise SystemExit("unexpected TdxFirmwareMissing error anchor count")
text = text.replace(old, new, 1)

# R590D/P/H helpers remain separate so each owner is reviewable in the combined diff.
old = '''    #[cfg(feature = "tdx")]
    fn populate_tdx_sections(
'''
new = '''    #[cfg(feature = "tdx")]
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
    fn write_tdx_payload_param(
        mem: &GuestMemoryMmap,
        data: &[u8],
        address: u64,
    ) -> Result<()> {
        mem.write_slice(data, GuestAddress(address))
            .map_err(Error::LoadPayloadParam)
    }

    #[cfg(feature = "tdx")]
    fn required_tdx_hob_offset(hob_offset: Option<u64>) -> Result<u64> {
        hob_offset.ok_or(Error::TdxHobMissing)
    }

    #[cfg(feature = "tdx")]
    fn populate_tdx_sections(
'''
if text.count(old) != 1:
    raise SystemExit("unexpected populate_tdx_sections anchor count")
text = text.replace(old, new, 1)

# R590D production call.
old = '''                    mem.read_volatile_from(
                        GuestAddress(section.address),
                        &mut firmware_file,
                        section.data_size as usize,
                    )
                    .unwrap();
'''
new = '''                    Self::copy_tdx_firmware_section(
                        &mem,
                        &mut firmware_file,
                        section.address,
                        section.data_size as usize,
                    )?;
'''
if text.count(old) != 1:
    raise SystemExit("unexpected BFV/CFV copy boundary count")
text = text.replace(old, new, 1)

# R590P production call.
old = '''                    mem.write_slice(
                        cmdline.as_cstring().unwrap().as_bytes_with_nul(),
                        GuestAddress(section.address),
                    )
                    .unwrap();
'''
new = '''                    Self::write_tdx_payload_param(
                        &mem,
                        cmdline.as_cstring().unwrap().as_bytes_with_nul(),
                        section.address,
                    )?;
'''
if text.count(old) != 1:
    raise SystemExit("unexpected PayloadParam write boundary count")
text = text.replace(old, new, 1)

# R590H production call while preserving the original Option<u64> return value.
old = '''        // Generate HOB
        let mut hob = TdHob::start(hob_offset.unwrap());
'''
new = '''        // Generate HOB
        let hob_start = Self::required_tdx_hob_offset(hob_offset)?;
        let mut hob = TdHob::start(hob_start);
'''
if text.count(old) != 1:
    raise SystemExit("unexpected TD HOB unwrap boundary count")
text = text.replace(old, new, 1)

anchor = '''    #[cfg(feature = "tdx")]
    #[test]
    fn test_hob_memory_resources() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDX unit-test anchor count")

test = r'''    #[cfg(feature = "tdx")]
    #[test]
    fn tdx_vmm_composition_preserves_typed_boundaries() {
        use std::env::temp_dir;
        use std::fs::{OpenOptions, remove_file, write};
        use std::process::id;

        let mem = GuestMemoryMmap::from_ranges(&[(GuestAddress(0), 0x1000)]).unwrap();

        // R590D: invalid BFV/CFV destination propagates existing FirmwareLoad.
        let path = temp_dir().join(format!("cloud-hypervisor-tdvf-vmm-composition-{}.fd", id()));
        write(&path, [0x5au8; 64]).unwrap();
        let mut file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();
        let dest_err = Vm::copy_tdx_firmware_section(&mem, &mut file, 0x2000, 16).unwrap_err();
        println!("TDVF_VMM_COMPOSITION firmware_invalid={dest_err:?}");
        assert!(matches!(dest_err, Error::FirmwareLoad(_)));

        file.rewind().unwrap();
        let copied = Vm::copy_tdx_firmware_section(&mem, &mut file, 0x800, 16).unwrap();
        let mut firmware_buf = [0u8; 16];
        mem.read_slice(&mut firmware_buf, GuestAddress(0x800)).unwrap();
        println!("TDVF_VMM_COMPOSITION firmware_control copied={copied} bytes={firmware_buf:?}");
        assert_eq!(copied, 16);
        assert_eq!(firmware_buf, [0x5a; 16]);

        // R590P: invalid PayloadParam destination propagates LoadPayloadParam.
        let payload_err =
            Vm::write_tdx_payload_param(&mem, b"console=ttyS0\0", 0x2000).unwrap_err();
        println!("TDVF_VMM_COMPOSITION payload_param_invalid={payload_err:?}");
        assert!(matches!(payload_err, Error::LoadPayloadParam(_)));

        Vm::write_tdx_payload_param(&mem, b"console=ttyS0\0", 0x900).unwrap();
        let mut payload_buf = [0u8; 14];
        mem.read_slice(&mut payload_buf, GuestAddress(0x900)).unwrap();
        println!("TDVF_VMM_COMPOSITION payload_param_control bytes={payload_buf:?}");
        assert_eq!(&payload_buf, b"console=ttyS0\0");

        // R590H: missing HOB is typed; present HOB offset remains unchanged.
        let hob_err = Vm::required_tdx_hob_offset(None).unwrap_err();
        println!("TDVF_VMM_COMPOSITION hob_missing={hob_err:?}");
        assert!(matches!(hob_err, Error::TdxHobMissing));
        let hob_start = Vm::required_tdx_hob_offset(Some(0x4000)).unwrap();
        println!("TDVF_VMM_COMPOSITION hob_control=0x{hob_start:x}");
        assert_eq!(hob_start, 0x4000);
    }

'''
text = text.replace(anchor, test + anchor, 1)
path.write_text(text)
