#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/vm.rs")
text = path.read_text()
marker = "Failed to copy TDX payload parameters to guest memory"
if marker in text:
    raise SystemExit(f"candidate marker already present in {path}")

old_error = '''    #[cfg(feature = "tdx")]
    #[error("Error performing I/O on the TDX payload file")]
    LoadPayload(#[source] io::Error),
'''
new_error = old_error + '''
    #[cfg(feature = "tdx")]
    #[error("Failed to copy TDX payload parameters to guest memory")]
    LoadPayloadParam(#[source] vm_memory::GuestMemoryError),
'''
if text.count(old_error) != 1:
    raise SystemExit("unexpected LoadPayload error anchor count")
text = text.replace(old_error, new_error, 1)

old_fn = '''    #[cfg(feature = "tdx")]
    fn populate_tdx_sections(
'''
new_fn = '''    #[cfg(feature = "tdx")]
    fn write_tdx_payload_param(
        mem: &GuestMemoryMmap,
        data: &[u8],
        address: u64,
    ) -> Result<()> {
        mem.write_slice(data, GuestAddress(address))
            .map_err(Error::LoadPayloadParam)
    }

    #[cfg(feature = "tdx")]
    fn populate_tdx_sections(
'''
if text.count(old_fn) != 1:
    raise SystemExit("unexpected populate_tdx_sections anchor count")
text = text.replace(old_fn, new_fn, 1)

old_write = '''                    mem.write_slice(
                        cmdline.as_cstring().unwrap().as_bytes_with_nul(),
                        GuestAddress(section.address),
                    )
                    .unwrap();
'''
new_write = '''                    Self::write_tdx_payload_param(
                        &mem,
                        cmdline.as_cstring().unwrap().as_bytes_with_nul(),
                        section.address,
                    )?;
'''
if text.count(old_write) != 1:
    raise SystemExit("unexpected PayloadParam write boundary count")
text = text.replace(old_write, new_write, 1)

anchor = '''    #[cfg(feature = "tdx")]
    #[test]
    fn test_hob_memory_resources() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDX unit-test anchor count")

test = r'''    #[cfg(feature = "tdx")]
    #[test]
    fn tdx_payload_param_write_propagates_guest_memory_error() {
        let mem = GuestMemoryMmap::from_ranges(&[(GuestAddress(0), 0x1000)]).unwrap();

        let err = Vm::write_tdx_payload_param(&mem, b"console=ttyS0\0", 0x2000).unwrap_err();
        println!("TDVF_PAYLOAD_PARAM_CANDIDATE invalid_result={err:?}");
        assert!(matches!(err, Error::LoadPayloadParam(_)));

        Vm::write_tdx_payload_param(&mem, b"console=ttyS0\0", 0x800).unwrap();
        let mut buf = [0u8; 14];
        mem.read_slice(&mut buf, GuestAddress(0x800)).unwrap();
        println!("TDVF_PAYLOAD_PARAM_CANDIDATE control_bytes={buf:?}");
        assert_eq!(&buf, b"console=ttyS0\0");
    }

'''
text = text.replace(anchor, test + anchor, 1)

path.write_text(text)
