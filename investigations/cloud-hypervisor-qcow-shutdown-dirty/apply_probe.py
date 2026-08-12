#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/formats/qcow/metadata.rs")
text = path.read_text()
marker = "failed_metadata_sync_keeps_dirty_bit_set"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

end = text.rfind("\n}")
if end == -1:
    raise SystemExit(f"could not find final metadata unit-test module close in {path}")

probe = r'''

    fn raw_dirty_bit(file: &std::fs::File) -> bool {
        use std::os::unix::fs::FileExt;

        let mut buf = [0u8; 8];
        file.read_exact_at(&mut buf, super::super::header::V2_BARE_HEADER_SIZE as u64)
            .unwrap();
        u64::from_be_bytes(buf) & super::super::header::IncompatFeatures::DIRTY.bits() != 0
    }

    #[test]
    fn failed_metadata_sync_keeps_dirty_bit_set() {
        let cluster_size: u64 = 1 << 16;
        let temp = super::super::QcowTempDisk::new(4 * cluster_size, None, false, true, false)
            .unwrap()
            .into_tempfile();
        let inspect = temp.as_file().try_clone().unwrap();
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut inner, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert!(raw_dirty_bit(&inspect));

        let invalid_l2 = inner
            .refcounts
            .max_valid_cluster_offset()
            .checked_add(cluster_size)
            .unwrap();
        inner.l1_table[0] = invalid_l2;

        let metadata = super::QcowMetadata::new(inner);
        metadata.shutdown();

        assert!(
            raw_dirty_bit(&inspect),
            "failed metadata synchronization must not publish a clean QCOW image"
        );
    }

    #[test]
    fn successful_metadata_sync_clears_dirty_bit() {
        let cluster_size: u64 = 1 << 16;
        let temp = super::super::QcowTempDisk::new(4 * cluster_size, None, false, true, false)
            .unwrap()
            .into_tempfile();
        let inspect = temp.as_file().try_clone().unwrap();
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (inner, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert!(raw_dirty_bit(&inspect));

        let metadata = super::QcowMetadata::new(inner);
        metadata.shutdown();

        assert!(!raw_dirty_bit(&inspect));
    }
'''

path.write_text(text[:end] + probe + text[end:])
