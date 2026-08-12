#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/formats/qcow/metadata.rs")
text = path.read_text()
marker = "fresh_l2_enospc_reopen_does_not_reuse_live_table"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

end = text.rfind("\n}")
if end == -1:
    raise SystemExit(f"could not find final unit-test module close in {path}")

probe = r'''

    #[test]
    fn fresh_l2_enospc_reopen_does_not_reuse_live_table() {
        let cluster_size: u64 = 1 << 16;
        let temp = super::super::QcowTempDisk::new(4 * cluster_size, None, false, true, false)
            .unwrap()
            .into_tempfile();
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut inner, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert_eq!(inner.l1_table[0], 0);

        // Add exactly two addressable clusters and cap file growth there. On
        // baseline the fresh L2 consumes the higher cluster, the data/refcount
        // path consumes the lower one, and ENOSPC drops the deferred L2 owner.
        // With ownership-before-publication the lower cluster can instead be
        // consumed by refcount-block relocation before data allocation fails.
        let file_size = inner.raw_file.file_mut().metadata().unwrap().len();
        assert_eq!(file_size % cluster_size, 0);
        inner
            .raw_file
            .file_mut()
            .set_len(file_size + 2 * cluster_size)
            .unwrap();
        let file_clusters = (file_size + 2 * cluster_size) / cluster_size;
        inner.refcounts = super::super::refcount::RefCount::new(
            &mut inner.raw_file,
            inner.header.refcount_table_offset,
            1,
            file_clusters,
            cluster_size,
            16,
        )
        .unwrap();
        inner.avail_clusters.clear();
        inner.unref_clusters.clear();
        inner.avail_clusters.push(file_size);
        inner.avail_clusters.push(file_size + cluster_size);

        let err = inner
            .map_write(0, None)
            .expect_err("allocator exhaustion must fail the first write");
        assert_eq!(err.raw_os_error(), Some(libc::ENOSPC));

        let live_l2 = inner.l1_table[0];
        assert_ne!(live_l2, 0, "the failed write must have wired a fresh L2");

        drop(super::QcowMetadata::new(inner));

        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut reopened, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert_eq!(reopened.l1_table[0], live_l2);

        let live_refcount = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut reopened;
            refcounts.get_cluster_refcount(raw_file, live_l2).unwrap()
        };
        let live_marked_free = reopened.avail_clusters.contains(&live_l2);
        let next_allocation = reopened
            .get_new_cluster(None)
            .expect("reopen should retain at least one reusable cluster");

        assert_ne!(
            next_allocation, live_l2,
            "clean reopen allocator must not return a still-referenced L2 cluster"
        );
        assert!(
            !live_marked_free,
            "clean reopen must keep a referenced fresh L2 out of the free list"
        );
        assert_eq!(
            live_refcount, 1,
            "clean reopen must retain ownership for the referenced fresh L2"
        );
    }

    #[test]
    fn relocated_l2_dropped_deferred_updates_keeps_refcount_owner() {
        let cluster_size: u64 = 1 << 16;
        let temp = super::super::QcowTempDisk::new(64 * cluster_size, None, false, true, false)
            .unwrap()
            .into_tempfile();
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut inner, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();

        inner.map_write(0, None).expect("initial write");
        inner.sync_caches().expect("make the current L2 clean");
        let old_l2 = inner.l1_table[0];
        assert_ne!(old_l2, 0);

        let data_cluster = inner.append_data_cluster(None).expect("new data cluster");
        let mut deferred = Vec::new();
        inner
            .update_cluster_addr(0, 1, data_cluster, &mut deferred)
            .expect("relocate clean L2");
        let relocated_l2 = inner.l1_table[0];
        assert_ne!(relocated_l2, 0);
        assert_ne!(relocated_l2, old_l2);

        // Model a caller error after L1 publication by dropping map_write's
        // local deferred vector before it can apply refcount updates.
        drop(deferred);
        drop(super::QcowMetadata::new(inner));

        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut reopened, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert_eq!(reopened.l1_table[0], relocated_l2);
        let relocated_refcount = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut reopened;
            refcounts
                .get_cluster_refcount(raw_file, relocated_l2)
                .unwrap()
        };
        assert_eq!(
            relocated_refcount, 1,
            "clean reopen must retain ownership for the published relocated L2"
        );
        assert!(
            !reopened.avail_clusters.contains(&relocated_l2),
            "clean reopen must keep the published relocated L2 out of the free list"
        );
    }

    #[test]
    fn zero_marker_fresh_l2_keeps_refcount_owner() {
        let cluster_size: u64 = 1 << 16;
        let temp = super::super::QcowTempDisk::new(4 * cluster_size, None, false, true, false)
            .unwrap()
            .into_tempfile();
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut inner, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert_eq!(inner.l1_table[0], 0);

        inner
            .deallocate_cluster(0, true, true)
            .expect("zero-marker deallocation must allocate its metadata table");
        let live_l2 = inner.l1_table[0];
        assert_ne!(live_l2, 0);
        let refcount = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut inner;
            refcounts.get_cluster_refcount(raw_file, live_l2).unwrap()
        };
        assert_eq!(refcount, 1);
    }
'''

path.write_text(text[:end] + probe.rstrip() + "\n" + text[end:])
