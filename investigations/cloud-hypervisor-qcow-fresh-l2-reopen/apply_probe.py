#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/formats/qcow/metadata.rs")
text = path.read_text()
marker = "fresh_l2_enospc_reopen_allocator_reuses_live_table"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

end = text.rfind("\n}")
if end == -1:
    raise SystemExit(f"could not find final unit-test module close in {path}")

probe = r'''

    #[test]
    #[ignore = "baseline corruption witness; run explicitly before candidate"]
    fn fresh_l2_enospc_reopen_allocator_reuses_live_table() {
        let cluster_size: u64 = 1 << 16;
        let temp = super::super::QcowTempDisk::new(4 * cluster_size, None, false, true, false)
            .unwrap()
            .into_tempfile();
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut inner, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert_eq!(inner.l1_table[0], 0);

        // Keep exactly two addressable free clusters. The LIFO allocator takes
        // the higher one for the fresh L2. On baseline, later data/refcount
        // work consumes the lower one and then fails ENOSPC while the fresh
        // L2 refcount increment is still deferred in map_write().
        let file_size = inner.raw_file.file_mut().metadata().unwrap().len();
        assert_eq!(file_size % cluster_size, 0);
        let low_free = file_size;
        let high_free = file_size + cluster_size;
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
        inner.avail_clusters.push(low_free);
        inner.avail_clusters.push(high_free);

        let err = inner
            .map_write(0, None)
            .expect_err("allocator exhaustion must fail the first write");
        assert_eq!(err.raw_os_error(), Some(libc::ENOSPC));

        let live_l2 = inner.l1_table[0];
        assert_eq!(
            live_l2, high_free,
            "fixture requires the highest reserved cluster to be the fresh L2"
        );
        let pre_close_refcount = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut inner;
            refcounts.get_cluster_refcount(raw_file, live_l2).unwrap()
        };
        eprintln!(
            "FRESH_L2_BASELINE pre_close live_l2={live_l2:#x} refcount={pre_close_refcount} low_free={low_free:#x} high_free={high_free:#x}"
        );
        assert_eq!(
            pre_close_refcount, 0,
            "failed baseline write must leave the fresh reachable L2 at refcount 0"
        );

        // Production clean-close owner: sync caches and clear DIRTY.
        drop(super::QcowMetadata::new(inner));

        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut reopened, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert_eq!(
            reopened.l1_table[0], live_l2,
            "clean reopen must preserve the live L1 -> fresh L2 reference"
        );
        let reopened_refcount = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut reopened;
            refcounts.get_cluster_refcount(raw_file, live_l2).unwrap()
        };
        let free_tail = reopened.avail_clusters.last().copied();
        eprintln!(
            "FRESH_L2_BASELINE reopened live_l2={live_l2:#x} l1={:#x} refcount={reopened_refcount} free_contains={} free_tail={free_tail:#x?}",
            reopened.l1_table[0],
            reopened.avail_clusters.contains(&live_l2)
        );
        assert_eq!(reopened_refcount, 0);
        assert!(
            reopened.avail_clusters.contains(&live_l2),
            "clean reopen must publish the refcount-0 live L2 into avail_clusters on baseline"
        );
        assert_eq!(
            free_tail,
            Some(live_l2),
            "ascending reopen scan must make the highest live L2 the next LIFO allocation"
        );

        // Decisive end of the chain: execute the real allocator. This call
        // also zeroes the returned cluster, exactly as a normal allocation
        // with no initial payload does.
        let reused = reopened
            .get_new_cluster(None)
            .expect("reopened allocator must return a free-list cluster");
        eprintln!(
            "FRESH_L2_BASELINE allocator_return reused={reused:#x} live_l2={live_l2:#x} l1_still={:#x}",
            reopened.l1_table[0]
        );
        assert_eq!(
            reused, live_l2,
            "allocator must hand out the exact cluster still referenced by L1"
        );
        assert_eq!(reopened.l1_table[0], live_l2);
    }

    #[test]
    fn fresh_l2_enospc_reopen_keeps_live_table_owned() {
        let cluster_size: u64 = 1 << 16;
        let temp = super::super::QcowTempDisk::new(4 * cluster_size, None, false, true, false)
            .unwrap()
            .into_tempfile();
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut inner, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert_eq!(inner.l1_table[0], 0);

        let file_size = inner.raw_file.file_mut().metadata().unwrap().len();
        assert_eq!(file_size % cluster_size, 0);
        let low_free = file_size;
        let high_free = file_size + cluster_size;
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
        inner.avail_clusters.push(low_free);
        inner.avail_clusters.push(high_free);

        let err = inner
            .map_write(0, None)
            .expect_err("allocator exhaustion must fail the first write");
        assert_eq!(err.raw_os_error(), Some(libc::ENOSPC));

        let live_l2 = inner.l1_table[0];
        assert_ne!(live_l2, 0, "failed write must have published a fresh L2");
        let pre_close_refcount = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut inner;
            refcounts.get_cluster_refcount(raw_file, live_l2).unwrap()
        };
        eprintln!(
            "FRESH_L2_INVARIANT pre_close live_l2={live_l2:#x} refcount={pre_close_refcount}"
        );

        drop(super::QcowMetadata::new(inner));

        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut reopened, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert_eq!(
            reopened.l1_table[0], live_l2,
            "clean reopen must preserve the L1 reference"
        );
        let reopened_refcount = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut reopened;
            refcounts.get_cluster_refcount(raw_file, live_l2).unwrap()
        };
        eprintln!(
            "FRESH_L2_INVARIANT reopened live_l2={live_l2:#x} refcount={reopened_refcount} free_contains={} free_tail={:#x?}",
            reopened.avail_clusters.contains(&live_l2),
            reopened.avail_clusters.last().copied()
        );
        assert!(
            !reopened.avail_clusters.contains(&live_l2),
            "clean reopen must not classify a still-referenced fresh L2 as free"
        );
        assert_eq!(
            reopened_refcount, 1,
            "clean reopen must retain a nonzero refcount for the live L2"
        );
    }

    #[test]
    fn fresh_l2_success_reopen_keeps_live_table_owned() {
        let cluster_size: u64 = 1 << 16;
        let temp = super::super::QcowTempDisk::new(4 * cluster_size, None, false, true, false)
            .unwrap()
            .into_tempfile();
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut inner, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert_eq!(inner.l1_table[0], 0);

        inner
            .map_write(0, None)
            .expect("ordinary first write must allocate its L2 and data cluster");
        let live_l2 = inner.l1_table[0];
        assert_ne!(live_l2, 0);
        let before_close = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut inner;
            refcounts.get_cluster_refcount(raw_file, live_l2).unwrap()
        };
        assert_eq!(before_close, 1);
        eprintln!("FRESH_L2_CONTROL pre_close live_l2={live_l2:#x} refcount={before_close}");

        drop(super::QcowMetadata::new(inner));

        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut reopened, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert_eq!(reopened.l1_table[0], live_l2);
        let reopened_refcount = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut reopened;
            refcounts.get_cluster_refcount(raw_file, live_l2).unwrap()
        };
        eprintln!(
            "FRESH_L2_CONTROL reopened live_l2={live_l2:#x} refcount={reopened_refcount} free_contains={}",
            reopened.avail_clusters.contains(&live_l2)
        );
        assert_eq!(reopened_refcount, 1);
        assert!(!reopened.avail_clusters.contains(&live_l2));
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
        eprintln!("FRESH_L2_ZERO_MARKER live_l2={live_l2:#x} refcount={refcount}");
        assert_eq!(refcount, 1);
    }
'''

path.write_text(text[:end] + probe + text[end:])
