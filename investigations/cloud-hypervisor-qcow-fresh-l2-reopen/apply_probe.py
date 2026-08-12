#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/formats/qcow/metadata.rs")
text = path.read_text()
marker = "failed_fresh_l2_becomes_reusable_after_clean_reopen"
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
    fn failed_fresh_l2_becomes_reusable_after_clean_reopen() {
        const CLUSTER_SIZE: u64 = 1 << 16;

        let temp = super::super::QcowTempDisk::new(64 * CLUSTER_SIZE, None, false, true, false)
            .unwrap()
            .into_tempfile();
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut inner, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();

        assert_eq!(
            inner.l1_table[0], 0,
            "fresh image must start with an empty L1 slot"
        );

        // Add exactly one physical cluster whose on-disk refcount remains zero,
        // then cap the refcount horizon at the current file size so the next
        // allocation cannot extend the image.
        let sole_free = inner.get_new_cluster(None).unwrap();
        let file_clusters = inner
            .raw_file
            .file_mut()
            .metadata()
            .unwrap()
            .len()
            .div_ceil(CLUSTER_SIZE);
        inner.refcounts = super::super::refcount::RefCount::new(
            &mut inner.raw_file,
            inner.header.refcount_table_offset,
            1,
            file_clusters,
            CLUSTER_SIZE,
            16,
        )
        .unwrap();
        inner.avail_clusters.clear();
        inner.unref_clusters.clear();
        inner.avail_clusters.push(sole_free);

        // The only free cluster is consumed by cache_l2_cluster_alloc() and
        // published in L1. The following data-cluster allocation then fails.
        let err = inner
            .map_write(0, None)
            .expect_err("data allocation must fail after the fresh L2 consumes the last cluster");
        assert_eq!(err.raw_os_error(), Some(libc::ENOSPC));

        let live_l2 = inner.l1_table[0];
        assert_eq!(live_l2, sole_free);
        let refcount = inner
            .refcounts
            .get_cluster_refcount(&mut inner.raw_file, live_l2)
            .unwrap();
        assert_eq!(
            refcount, 0,
            "failed map_write dropped the fresh L2's deferred refcount"
        );

        // Clean shutdown flushes the reachable L1/L2 state and clears DIRTY.
        drop(super::QcowMetadata::new(inner));

        // A clean reopen trusts the zero refcount and rebuilds avail_clusters
        // directly from it instead of traversing metadata to repair refcounts.
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut reopened, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert_eq!(reopened.l1_table[0], live_l2);
        assert!(
            reopened.avail_clusters.contains(&live_l2),
            "a still-referenced L2 must never re-enter the allocator free list"
        );

        // The fresh L2 was appended at the physical end of the image, and the
        // free list is built in ascending file order while allocation pops from
        // the end. The next allocation therefore returns the live table itself.
        let reused = reopened.get_new_cluster(None).unwrap();
        assert_eq!(
            reused, live_l2,
            "allocator reused a cluster still referenced as an L2 table"
        );
    }

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
