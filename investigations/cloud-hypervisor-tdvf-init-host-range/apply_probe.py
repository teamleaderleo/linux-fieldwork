#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/vm.rs")
text = path.read_text()
marker = "tdvf_init_host_range_crosses_region_panics_baseline"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = '''    #[cfg(feature = "tdx")]
    #[test]
    fn test_hob_memory_resources() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDX unit-test anchor count")

probe = r'''    #[cfg(feature = "tdx")]
    fn current_tdvf_host_range_unwrap(
        mem: &GuestMemoryMmap,
        address: u64,
        size: usize,
    ) -> *mut u8 {
        virtio_devices::get_host_address_range(mem, GuestAddress(address), size).unwrap()
    }

    #[cfg(feature = "tdx")]
    #[test]
    fn tdvf_init_host_range_valid_control() {
        let mem = GuestMemoryMmap::from_ranges(&[(GuestAddress(0), 0x1000)]).unwrap();
        let expected = virtio_devices::get_host_address_range(&mem, GuestAddress(0x800), 0x100)
            .unwrap();
        let actual = current_tdvf_host_range_unwrap(&mem, 0x800, 0x100);
        println!("TDVF_INIT_HOST_RANGE_CONTROL expected={expected:p} actual={actual:p}");
        assert_eq!(actual, expected);
    }

    #[cfg(feature = "tdx")]
    #[test]
    #[ignore]
    fn tdvf_init_host_range_crosses_region_panics_baseline() {
        let mem = GuestMemoryMmap::from_ranges(&[(GuestAddress(0), 0x1000)]).unwrap();
        let outcome = std::panic::catch_unwind(|| {
            let _ = current_tdvf_host_range_unwrap(&mem, 0xf80, 0x100);
        });
        println!("TDVF_INIT_HOST_RANGE_BASELINE panicked={}", outcome.is_err());
        assert!(outcome.is_err());
    }

    #[cfg(feature = "tdx")]
    #[test]
    fn tdvf_init_host_range_crosses_region_should_not_panic() {
        let mem = GuestMemoryMmap::from_ranges(&[(GuestAddress(0), 0x1000)]).unwrap();
        let outcome = std::panic::catch_unwind(|| {
            let _ = current_tdvf_host_range_unwrap(&mem, 0xf80, 0x100);
        });
        println!("TDVF_INIT_HOST_RANGE_INVARIANT panicked={}", outcome.is_err());
        assert!(outcome.is_ok(), "invalid TDVF host range must not panic the VMM");
    }

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
