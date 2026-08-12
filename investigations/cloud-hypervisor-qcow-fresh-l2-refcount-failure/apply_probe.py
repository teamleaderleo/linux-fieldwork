#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/formats/qcow/metadata.rs")
text = path.read_text()
marker = "fresh_l2_refcount_acquire_enospc_keeps_l1_unpublished"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

end = text.rfind("\n}")
if end == -1:
    raise SystemExit(f"could not find final unit-test module close in {path}")

probe = r'''

    #[test]
    fn fresh_l2_refcount_acquire_enospc_keeps_l1_unpublished() {
        let cluster_size: u64 = 1 << 16;
        let temp = super::super::QcowTempDisk::new(4 * cluster_size, None, false, true, false)
            .unwrap()
            .into_tempfile();
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut inner, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert_eq!(inner.l1_table[0], 0);
        assert!(!inner.l2_cache.contains_key(0));

        // Exactly one addressable free cluster. The ownership-before-publication
        // candidate consumes it as the prospective fresh L2, then immediate
        // refcount acquisition has to relocate the clean refcount block. With
        // no second cluster available and the horizon capped at this address,
        // that refcount relocation fails ENOSPC before L1 publication.
        let file_size = inner.raw_file.file_mut().metadata().unwrap().len();
        assert_eq!(file_size % cluster_size, 0);
        let prospective_l2 = file_size;
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
        inner.avail_clusters.push(prospective_l2);

        let err = inner
            .map_write(0, None)
            .expect_err("immediate fresh-L2 refcount relocation must hit ENOSPC");
        assert_eq!(err.raw_os_error(), Some(libc::ENOSPC));

        assert_eq!(
            inner.l1_table[0], 0,
            "failed ownership acquisition must leave L1 unpublished"
        );
        assert!(
            !inner.l2_cache.contains_key(0),
            "failed ownership acquisition must not publish a fresh L2 cache entry"
        );
        let pre_close_refcount = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut inner;
            refcounts
                .get_cluster_refcount(raw_file, prospective_l2)
                .unwrap()
        };
        eprintln!(
            "FRESH_L2_REFCOUNT_FAIL pre_close prospective_l2={prospective_l2:#x} l1={:#x} refcount={pre_close_refcount} in_avail={} in_unref={}",
            inner.l1_table[0],
            inner.avail_clusters.contains(&prospective_l2),
            inner.unref_clusters.contains(&prospective_l2)
        );
        assert_eq!(pre_close_refcount, 0);
        assert!(!inner.avail_clusters.contains(&prospective_l2));
        assert!(!inner.unref_clusters.contains(&prospective_l2));

        // Production clean-close owner. The prospective L2 is temporarily
        // unavailable in this process, but it is unreachable metadata.
        drop(super::QcowMetadata::new(inner));

        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut reopened, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert_eq!(
            reopened.l1_table[0], 0,
            "clean reopen must retain the unpublished L1 state"
        );
        let reopened_refcount = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut reopened;
            refcounts
                .get_cluster_refcount(raw_file, prospective_l2)
                .unwrap()
        };
        let free_tail = reopened.avail_clusters.last().copied();
        eprintln!(
            "FRESH_L2_REFCOUNT_FAIL reopened prospective_l2={prospective_l2:#x} l1={:#x} refcount={reopened_refcount} free_contains={} free_tail={free_tail:#x?}",
            reopened.l1_table[0],
            reopened.avail_clusters.contains(&prospective_l2)
        );
        assert_eq!(reopened_refcount, 0);
        assert!(reopened.avail_clusters.contains(&prospective_l2));
        assert_eq!(free_tail, Some(prospective_l2));

        let reused = reopened
            .get_new_cluster(None)
            .expect("clean reopen should safely rediscover the unreachable cluster");
        eprintln!(
            "FRESH_L2_REFCOUNT_FAIL allocator_return reused={reused:#x} prospective_l2={prospective_l2:#x} l1={:#x}",
            reopened.l1_table[0]
        );
        assert_eq!(reused, prospective_l2);
        assert_eq!(reopened.l1_table[0], 0);
    }
'''

path.write_text(text[:end] + probe + text[end:])
