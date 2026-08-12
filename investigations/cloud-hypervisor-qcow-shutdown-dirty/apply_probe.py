#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/formats/qcow/metadata.rs")
text = path.read_text()
marker = "failed_metadata_flush_must_keep_dirty_bit_set"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = '''    // Regression for the ENOSPC unwind on the relocate-on-write path: when
    // the allocation for the relocated table fails, the still-referenced old
    // L2 table must not be left on the free lists (issue #8606).
    #[test]
    fn failed_l2_relocate_keeps_live_table_off_free_lists() {'''
if text.count(anchor) != 1:
    raise SystemExit(f"expected exactly one metadata unit-test anchor in {path}")

probe = r'''    #[test]
    fn failed_metadata_flush_must_keep_dirty_bit_set() {
        use std::os::unix::fs::FileExt;

        const CLUSTER_SIZE: u64 = 1 << 16;
        const INCOMPATIBLE_FEATURES_OFFSET: u64 = super::super::header::V2_BARE_HEADER_SIZE as u64;

        fn dirty_bit_is_set(file: &std::fs::File) -> bool {
            let mut buf = [0u8; 8];
            file.read_exact_at(&mut buf, INCOMPATIBLE_FEATURES_OFFSET)
                .unwrap();
            u64::from_be_bytes(buf) & super::super::header::IncompatFeatures::DIRTY.bits() != 0
        }

        let temp = super::super::QcowTempDisk::new(64 * CLUSTER_SIZE, None, false, true, false)
            .unwrap()
            .into_tempfile();
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut inner, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();

        assert!(dirty_bit_is_set(temp.as_file()));

        // Mark L1 dirty with a cluster address outside the refcount horizon.
        // sync_caches() must fail while trying to derive the L1 copied bit from
        // this invalid refcount address.
        let invalid_l2 = inner.refcounts.max_valid_cluster_offset() + CLUSTER_SIZE;
        inner.l1_table[0] = invalid_l2;
        assert!(inner.sync_caches().is_err());

        // Recreate the same dirty L1 state because the direct sync attempt
        // above may have touched intermediate cache state. shutdown() must not
        // clear DIRTY when its own sync_caches() attempt fails.
        inner.l1_table[0] = invalid_l2;
        let metadata = super::QcowMetadata::new(inner);
        metadata.shutdown();

        assert!(
            dirty_bit_is_set(temp.as_file()),
            "failed metadata flush must not be advertised as a clean QCOW shutdown"
        );
    }

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
