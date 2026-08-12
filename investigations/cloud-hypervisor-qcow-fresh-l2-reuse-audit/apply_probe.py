#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/formats/qcow/metadata.rs")
text = path.read_text()
marker = "fresh_l2_enospc_clean_reopen_reuses_live_l2"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

end = text.rfind("\n}")
if end == -1:
    raise SystemExit(f"could not find final unit-test module close in {path}")

probe = r'''

    fn fresh_l2_enospc_state() -> (vmm_sys_util::tempfile::TempFile, super::QcowState, u64) {
        let cluster_size: u64 = 1 << 16;
        let temp = super::super::QcowTempDisk::new(4 * cluster_size, None, false, true, false)
            .unwrap()
            .into_tempfile();
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut inner, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert_eq!(inner.l1_table[0], 0);

        // Add two physical clusters and cap the refcount horizon there. Push
        // low then high so get_new_cluster() pops the high cluster for the
        // fresh L2. The low cluster is consumed by append_data_cluster(); its
        // refcount update then needs a refblock relocation and hits ENOSPC.
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
            .expect_err("first write must exhaust after publishing the fresh L2");
        assert_eq!(err.raw_os_error(), Some(libc::ENOSPC));

        let live_l2 = inner.l1_table[0];
        assert_eq!(live_l2, file_size + cluster_size);
        let live_l2_refcount = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut inner;
            refcounts.get_cluster_refcount(raw_file, live_l2).unwrap()
        };
        assert_eq!(live_l2_refcount, 0);
        assert!(inner.avail_clusters.is_empty());
        assert!(!inner.unref_clusters.contains(&live_l2));
        eprintln!(
            "post_enospc live_l2={live_l2:#x} refcount={live_l2_refcount} in_avail={} in_unref={}",
            inner.avail_clusters.contains(&live_l2),
            inner.unref_clusters.contains(&live_l2)
        );

        (temp, inner, live_l2)
    }

    #[test]
    fn fresh_l2_enospc_clean_reopen_reuses_live_l2() {
        use std::os::unix::fs::FileExt;

        let cluster_size: u64 = 1 << 16;
        let (temp, inner, live_l2) = fresh_l2_enospc_state();

        // Production final-owner close: flush caches and clear DIRTY.
        drop(super::QcowMetadata::new(inner));

        let inspect_raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let clean_header = super::super::QcowHeader::new(&inspect_raw).unwrap();
        let dirty_mask = super::super::IncompatFeatures::DIRTY.bits();
        assert_eq!(clean_header.incompatible_features & dirty_mask, 0);
        eprintln!("post_shutdown dirty=false live_l2={live_l2:#x}");

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
        assert_eq!(reopened_refcount, 0);
        assert!(reopened.avail_clusters.contains(&live_l2));
        assert_eq!(reopened.avail_clusters.last().copied(), Some(live_l2));
        eprintln!(
            "clean_reopen l1={:#x} refcount={} free_contains={} free_last={:#x}",
            reopened.l1_table[0],
            reopened_refcount,
            reopened.avail_clusters.contains(&live_l2),
            reopened.avail_clusters.last().copied().unwrap()
        );

        // Exercise the real higher-level data allocator. It must pop the live
        // L2 first, write marker bytes there, and establish a new data owner.
        let marker = vec![0xa5; cluster_size as usize];
        let reused = reopened
            .append_data_cluster(Some(marker))
            .expect("reopened data allocator must be able to reuse a free cluster");
        assert_eq!(reused, live_l2);
        assert_eq!(reopened.l1_table[0], live_l2);

        let mut bytes = [0u8; 16];
        temp.as_file().read_exact_at(&mut bytes, live_l2).unwrap();
        assert_eq!(bytes, [0xa5; 16]);
        eprintln!(
            "allocator_reuse returned={reused:#x} l1_still={:#x} marker={:02x?}",
            reopened.l1_table[0], bytes
        );
    }

    #[test]
    fn fresh_l2_enospc_dirty_reopen_recovers_live_l2() {
        let (temp, mut inner, live_l2) = fresh_l2_enospc_state();

        // Persist the mismatched L1/L2 caches while deliberately retaining
        // DIRTY. This models the recovery discriminator, not a clean close.
        inner.sync_caches().expect("persist mismatched L1 while DIRTY");
        drop(inner);

        let inspect_raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let dirty_header = super::super::QcowHeader::new(&inspect_raw).unwrap();
        let dirty_mask = super::super::IncompatFeatures::DIRTY.bits();
        assert_ne!(dirty_header.incompatible_features & dirty_mask, 0);

        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut reopened, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert_eq!(reopened.l1_table[0], live_l2);
        let recovered_refcount = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut reopened;
            refcounts.get_cluster_refcount(raw_file, live_l2).unwrap()
        };
        assert_eq!(recovered_refcount, 1);
        assert!(!reopened.avail_clusters.contains(&live_l2));
        eprintln!(
            "dirty_reopen l1={:#x} recovered_refcount={} free_contains={}",
            reopened.l1_table[0],
            recovered_refcount,
            reopened.avail_clusters.contains(&live_l2)
        );
    }
'''

path.write_text(text[:end] + probe + text[end:])
