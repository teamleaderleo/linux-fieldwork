#!/usr/bin/env python3
from pathlib import Path

path = Path("pci/src/vfio.rs")
text = path.read_text()
marker = "vfio_sparse_crossing_range_must_return_error"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

probe = r'''

#[cfg(test)]
mod sparse_dma_map_probe_tests {
    use std::env::temp_dir;
    use std::fs::{OpenOptions, remove_file};
    use std::os::fd::AsFd;
    use std::panic::{AssertUnwindSafe, catch_unwind};
    use std::process::id;

    use super::*;

    fn sparse_mmio_regions() -> Vec<MmioRegion> {
        let path = temp_dir().join(format!("cloud-hypervisor-vfio-sparse-{id}", id = id()));
        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(true)
            .open(&path)
            .unwrap();
        file.set_len(0x2000).unwrap();

        let mapping_a = Arc::new(
            MmapRegion::mmap(
                0x1000,
                libc::PROT_READ | libc::PROT_WRITE,
                file.as_fd(),
                0,
                0,
            )
            .unwrap(),
        );
        let mapping_b = Arc::new(
            MmapRegion::mmap(
                0x1000,
                libc::PROT_READ | libc::PROT_WRITE,
                file.as_fd(),
                0x1000,
                0,
            )
            .unwrap(),
        );
        remove_file(path).unwrap();

        vec![MmioRegion {
            start: GuestAddress(0x1000),
            length: 0x4000,
            type_: PciBarRegionType::Memory32BitRegion,
            index: 0,
            user_memory_regions: vec![
                UserMemoryRegion {
                    slot: 0,
                    start: 0x1000,
                    mapping: mapping_a,
                },
                UserMemoryRegion {
                    slot: 1,
                    start: 0x3000,
                    mapping: mapping_b,
                },
            ],
        }]
    }

    #[test]
    fn vfio_sparse_in_subregion_control() {
        let regions = sparse_mmio_regions();
        assert!(regions.check_range(0x1800, 0x800));
        let result = regions.find_user_address(0x1800, 0x800);
        println!(
            "VFIO_SPARSE_DMA_CONTROL in_subregion_result={}",
            if result.is_ok() { "ok" } else { "err" }
        );
        match result {
            Ok(pointer) => assert!(!pointer.is_null()),
            Err(error) => panic!("in-subregion lookup failed: {error}"),
        }
    }

    #[test]
    fn vfio_sparse_hole_control() {
        let regions = sparse_mmio_regions();
        assert!(regions.check_range(0x2800, 0x100));
        let result = regions.find_user_address(0x2800, 0x100);
        println!(
            "VFIO_SPARSE_DMA_CONTROL hole_result={}",
            if result.is_err() { "err" } else { "ok" }
        );
        match result {
            Err(_) => {}
            Ok(_) => panic!("hole lookup unexpectedly returned a host pointer"),
        }
    }

    #[test]
    #[ignore]
    fn vfio_sparse_crossing_range_panics_baseline() {
        let regions = sparse_mmio_regions();
        assert!(regions.check_range(0x1800, 0x1000));
        let panicked = catch_unwind(AssertUnwindSafe(|| {
            let _ = regions.find_user_address(0x1800, 0x1000);
        }))
        .is_err();
        println!("VFIO_SPARSE_DMA_BASELINE crossing_panicked={panicked}");
        assert!(panicked, "current sparse-subregion boundary no longer panics");
    }

    #[test]
    fn vfio_sparse_crossing_range_must_return_error() {
        let regions = sparse_mmio_regions();
        assert!(regions.check_range(0x1800, 0x1000));
        let outcome = catch_unwind(AssertUnwindSafe(|| {
            regions.find_user_address(0x1800, 0x1000)
        }));
        match outcome {
            Ok(Err(error)) => {
                println!("VFIO_SPARSE_DMA_INVARIANT crossing_result=err error={error}");
            }
            Ok(Ok(_)) => panic!("crossing sparse range unexpectedly returned a host pointer"),
            Err(_) => panic!("guest-controlled sparse VFIO DMA range must not panic the VMM"),
        }
    }
}
'''

path.write_text(text + probe)
