#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/formats/qcow/metadata.rs")
text = path.read_text()
marker = "fresh_l2_enospc_reopen_keeps_live_table_out_of_free_list"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

end = text.rfind("\n}")
if end == -1:
    raise SystemExit(f"could not find final unit-test module close in {path}")

probe = r'''

    #[test]
    fn fresh_l2_enospc_reopen_keeps_live_table_out_of_free_list() {
        let cluster_size: u64 = 1 << 16;
        let temp = super::super::QcowTempDisk::new(4 * cluster_size, None, false, true, false)
            .unwrap()
            .into_tempfile();
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut inner, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert_eq!(inner.l1_table[0], 0);

        // Add exactly two refcount-addressable free clusters and prevent file
        // growth beyond them. Baseline uses one for the fresh L2 and one for
        // the following data/refcount work, then fails while the L2 increment
        // is still only in map_write()'s local deferred vector. A candidate
        // that commits the L2 refcount first may use the second cluster for a
        // refcount-block relocation and then fail the data allocation instead.
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
        assert_ne!(live_l2, 0, "failed write must have wired a fresh L2");

        // Use the same clean-close owner as production. This persists the L1
        // pointer and clears the DIRTY bit before the next parse.
        drop(super::QcowMetadata::new(inner));

        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut reopened, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert_eq!(
            reopened.l1_table[0], live_l2,
            "clean reopen must preserve the L1 reference"
        );

        if reopened.avail_clusters.contains(&live_l2) {
            // Prove allocator eligibility all the way through reuse. Restrict
            // the free list to the parser-published live cluster so the next
            // allocation is deterministic.
            reopened.avail_clusters.clear();
            reopened.avail_clusters.push(live_l2);
            let reused = reopened
                .get_new_cluster(None)
                .expect("parser-published live L2 must be allocatable");
            assert_ne!(
                reused, live_l2,
                "allocator must never return a still-referenced fresh L2"
            );
        }

        assert!(
            !reopened.avail_clusters.contains(&live_l2),
            "clean reopen must keep a still-referenced fresh L2 off the free list"
        );

        let reopened_refcount = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut reopened;
            refcounts.get_cluster_refcount(raw_file, live_l2).unwrap()
        };
        assert_eq!(
            reopened_refcount, 1,
            "clean reopen must retain a nonzero refcount for the live L2"
        );
    }

    #[test]
    fn fresh_l2_refcount_enospc_does_not_publish_l1() {
        let cluster_size: u64 = 1 << 16;
        let temp = super::super::QcowTempDisk::new(4 * cluster_size, None, false, true, false)
            .unwrap()
            .into_tempfile();
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut inner, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert_eq!(inner.l1_table[0], 0);

        // Leave one fresh cluster available and cap growth. The candidate can
        // allocate that L2, but securing its refcount needs a COW refcount
        // block and must fail ENOSPC before L1 publication.
        let file_size = inner.raw_file.file_mut().metadata().unwrap().len();
        assert_eq!(file_size % cluster_size, 0);
        inner
            .raw_file
            .file_mut()
            .set_len(file_size + cluster_size)
            .unwrap();
        let file_clusters = (file_size + cluster_size) / cluster_size;
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

        let err = inner
            .map_write(0, None)
            .expect_err("refcount ownership must fail at allocator exhaustion");
        assert_eq!(err.raw_os_error(), Some(libc::ENOSPC));
        assert_eq!(
            inner.l1_table[0], 0,
            "failed fresh-L2 ownership must leave L1 unpublished"
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

path.write_text(text[:end] + probe.rstrip() + text[end:])
