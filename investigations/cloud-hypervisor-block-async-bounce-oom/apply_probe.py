#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/io/async_io/owned_io_buffer.rs")
text = path.read_text()
marker = "guest_oom_huge_buffer_must_fail_fallibly"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

probe = r'''

#[cfg(test)]
mod guest_oom_probe_tests {
    use super::*;

    const DATA_DESC_COUNT: usize = 32_766;
    const PER_DESC_LEN: usize = 131_064;
    const GUEST_SHAPED_DATA_LEN: usize = DATA_DESC_COUNT * PER_DESC_LEN;

    #[test]
    fn guest_oom_small_buffer_control() {
        let buffer = OwnedIoBuffer::new(4096, 0).unwrap();
        println!(
            "BLOCK_BOUNCE_OOM_CONTROL small_len={} total_len={}",
            buffer.as_slice().len(),
            buffer.total_len()
        );
        assert_eq!(buffer.as_slice().len(), 4096);
        assert_eq!(buffer.total_len(), 4096);
    }

    #[test]
    #[ignore]
    fn guest_oom_huge_aligned_returns_error_control() {
        println!(
            "BLOCK_BOUNCE_OOM_ALIGNED_REQUEST requested={} alignment=512",
            GUEST_SHAPED_DATA_LEN
        );
        match OwnedIoBuffer::new(GUEST_SHAPED_DATA_LEN, 512) {
            Err(error) => {
                println!(
                    "BLOCK_BOUNCE_OOM_ALIGNED_RESULT error_kind={:?}",
                    error.kind()
                );
                assert_eq!(error.kind(), io::ErrorKind::OutOfMemory);
            }
            Ok(_) => panic!("huge aligned allocation unexpectedly succeeded"),
        }
    }

    #[test]
    #[ignore]
    fn guest_oom_huge_buffer_must_fail_fallibly() {
        println!(
            "BLOCK_BOUNCE_OOM_REQUEST requested={} alignment=0",
            GUEST_SHAPED_DATA_LEN
        );
        match OwnedIoBuffer::new(GUEST_SHAPED_DATA_LEN, 0) {
            Err(error) => {
                println!(
                    "BLOCK_BOUNCE_OOM_RESULT error_kind={:?}",
                    error.kind()
                );
                assert_eq!(error.kind(), io::ErrorKind::OutOfMemory);
            }
            Ok(_) => panic!("guest-sized buffered bounce allocation unexpectedly succeeded"),
        }
    }
}
'''

path.write_text(text + probe)
