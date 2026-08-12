#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/vm.rs")
text = path.read_text()
marker = "Invalid TDX memory range"
if marker in text:
    raise SystemExit(f"candidate marker already present in {path}")

old_error = '''    #[cfg(feature = "tdx")]
    #[error("Error allocating TDVF memory")]
    AllocatingTdvfMemory(#[source] memory_manager::Error),
'''
new_error = old_error + '''
    #[cfg(feature = "tdx")]
    #[error("Invalid TDX memory range: address={address:#x}, size={size:#x}")]
    InvalidTdxMemoryRange { address: u64, size: usize },
'''
if text.count(old_error) != 1:
    raise SystemExit("unexpected TDX allocation error anchor count")
text = text.replace(old_error, new_error, 1)

old_fn = '''    #[cfg(feature = "tdx")]
    fn init_tdx_memory(&mut self, sections: &[arch::x86_64::tdx::TdvfSection]) -> Result<()> {
'''
new_fn = '''    #[cfg(feature = "tdx")]
    fn tdx_host_address_range(
        mem: &GuestMemoryMmap,
        address: u64,
        size: usize,
    ) -> Result<*mut u8> {
        virtio_devices::get_host_address_range(mem, GuestAddress(address), size)
            .ok_or(Error::InvalidTdxMemoryRange { address, size })
    }

    #[cfg(feature = "tdx")]
    fn init_tdx_memory(&mut self, sections: &[arch::x86_64::tdx::TdvfSection]) -> Result<()> {
'''
if text.count(old_fn) != 1:
    raise SystemExit("unexpected init_tdx_memory anchor count")
text = text.replace(old_fn, new_fn, 1)

old_range = '''                    virtio_devices::get_host_address_range(
                        &*mem,
                        GuestAddress(section.address),
                        size,
                    )
                    .unwrap(),
'''
new_range = '''                    Self::tdx_host_address_range(&mem, section.address, size)?,
'''
if text.count(old_range) != 1:
    raise SystemExit("unexpected init_tdx_memory host-range unwrap count")
text = text.replace(old_range, new_range, 1)

anchor = '''    #[cfg(feature = "tdx")]
    #[test]
    fn test_hob_memory_resources() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDX unit-test anchor count")

test = r'''    #[cfg(feature = "tdx")]
    #[test]
    fn tdx_host_address_range_returns_typed_error() {
        let mem = GuestMemoryMmap::from_ranges(&[(GuestAddress(0), 0x1000)]).unwrap();

        let err = Vm::tdx_host_address_range(&mem, 0xf80, 0x100).unwrap_err();
        println!("TDVF_INIT_HOST_RANGE_CANDIDATE invalid_result={err:?}");
        assert!(matches!(
            err,
            Error::InvalidTdxMemoryRange {
                address: 0xf80,
                size: 0x100,
            }
        ));

        let expected = virtio_devices::get_host_address_range(&mem, GuestAddress(0x800), 0x100)
            .unwrap();
        let actual = Vm::tdx_host_address_range(&mem, 0x800, 0x100).unwrap();
        println!("TDVF_INIT_HOST_RANGE_CANDIDATE control expected={expected:p} actual={actual:p}");
        assert_eq!(actual, expected);
    }

'''
text = text.replace(anchor, test + anchor, 1)
path.write_text(text)
