#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/vm.rs")
text = path.read_text()
marker = "tdvf_payload_param_invalid_guest_address_panics_baseline"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = '''    #[cfg(feature = "tdx")]
    #[test]
    fn test_hob_memory_resources() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDX unit-test anchor count")

probe = r'''    #[cfg(feature = "tdx")]
    fn current_payload_param_write(mem: &GuestMemoryMmap, address: u64) {
        mem.write_slice(b"console=ttyS0\0", GuestAddress(address))
            .unwrap();
    }

    #[cfg(feature = "tdx")]
    fn payload_param_test_memory() -> GuestMemoryMmap {
        GuestMemoryMmap::from_ranges(&[(GuestAddress(0), 0x1000)]).unwrap()
    }

    #[cfg(feature = "tdx")]
    #[test]
    fn tdvf_payload_param_valid_guest_address_control() {
        let mem = payload_param_test_memory();
        current_payload_param_write(&mem, 0x800);
        let mut buf = [0u8; 14];
        mem.read_slice(&mut buf, GuestAddress(0x800)).unwrap();
        println!("TDVF_PAYLOAD_PARAM_CONTROL bytes={buf:?}");
        assert_eq!(&buf, b"console=ttyS0\0");
    }

    #[cfg(feature = "tdx")]
    #[test]
    #[ignore]
    fn tdvf_payload_param_invalid_guest_address_panics_baseline() {
        let mem = payload_param_test_memory();
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            current_payload_param_write(&mem, 0x2000);
        }));
        println!("TDVF_PAYLOAD_PARAM_BASELINE panicked={}", result.is_err());
        assert!(result.is_err());
    }

    #[cfg(feature = "tdx")]
    #[test]
    fn tdvf_payload_param_invalid_guest_address_should_not_panic() {
        let mem = payload_param_test_memory();
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            current_payload_param_write(&mem, 0x2000);
        }));
        println!("TDVF_PAYLOAD_PARAM_INVARIANT panicked={}", result.is_err());
        assert!(result.is_ok(), "invalid PayloadParam destination must not panic the VMM");
    }

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
