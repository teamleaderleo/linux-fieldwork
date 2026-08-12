#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/formats/qcow/metadata.rs")
text = path.read_text()
marker = "refblock_recursive_enospc_transaction_rolls_back"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

end = text.rfind("\n}")
if end == -1:
    raise SystemExit(f"could not find final unit-test module close in {path}")

probe = r'''

    #[test]
    fn refblock_recursive_enospc_transaction_rolls_back() {
        let cluster_size: u64 = 1 << 16;
        let refcount_bits: u64 = 16;
        let refcount_block_entries = cluster_size * 8 / refcount_bits;
        assert_eq!(refcount_block_entries, 32_768);

        let temp = super::super::QcowTempDisk::new(4 * 1024 * 1024 * 1024, None, false, true, false)
            .unwrap()
            .into_tempfile();
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut inner, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();

        let refcount_table_offset = inner.header.refcount_table_offset;
        let initial_table = inner
            .raw_file
            .read_pointer_table(refcount_table_offset, 2, None)
            .unwrap();
        let old_refblock = initial_table[0];
        assert_ne!(old_refblock, 0);
        assert_eq!(initial_table[1], 0);

        let target = inner.raw_file.file_mut().metadata().unwrap().len();
        let replacement_refblock = refcount_block_entries * cluster_size;
        assert!(target < replacement_refblock);

        // Keep exact 64 KiB / 16-bit geometry but cap the test RefCount at
        // two regions. Once Y is consumed as the region-0 replacement, the
        // recursive region-1 ownership request has no cluster left and cannot
        // extend beyond the artificial horizon.
        let artificial_table_entries = 2u64;
        let artificial_clusters = artificial_table_entries * refcount_block_entries;
        inner
            .raw_file
            .file_mut()
            .set_len(artificial_clusters * cluster_size)
            .unwrap();
        inner.refcounts = super::super::refcount::RefCount::new(
            &mut inner.raw_file,
            refcount_table_offset,
            artificial_table_entries,
            refcount_block_entries,
            cluster_size,
            refcount_bits,
        )
        .unwrap();
        inner.avail_clusters.clear();
        inner.unref_clusters.clear();

        // LIFO: X is the externally allocated target; Y is the only cluster
        // the recursive refcount transaction itself may consume.
        inner.avail_clusters.push(replacement_refblock);
        inner.avail_clusters.push(target);
        let allocated_target = inner.get_new_cluster(None).unwrap();
        assert_eq!(allocated_target, target);

        let err = inner
            .set_cluster_refcount_track_freed(allocated_target, 1)
            .expect_err("recursive refblock ownership must hit deterministic ENOSPC");
        assert_eq!(err.raw_os_error(), Some(libc::ENOSPC));

        let (target_refcount, replacement_refcount) = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut inner;
            (
                refcounts
                    .get_cluster_refcount(raw_file, allocated_target)
                    .unwrap(),
                refcounts
                    .get_cluster_refcount(raw_file, replacement_refblock)
                    .unwrap(),
            )
        };
        eprintln!(
            "REFBLOCK_TX_ROLLBACK post_error target={allocated_target:#x} target_refcount={target_refcount} replacement={replacement_refblock:#x} replacement_refcount={replacement_refcount} replacement_free={} unref_count={}",
            inner.avail_clusters.contains(&replacement_refblock),
            inner.unref_clusters.len()
        );
        assert_eq!(target_refcount, 0, "failed target refcount must roll back");
        assert_eq!(replacement_refcount, 0);
        assert!(inner.avail_clusters.contains(&replacement_refblock));
        assert_eq!(inner.avail_clusters.last().copied(), Some(replacement_refblock));
        assert!(inner.unref_clusters.is_empty());

        // Flush the restored transaction state. If table0 still pointed at Y
        // in memory this would make that bad pointer durable here.
        inner.sync_caches().unwrap();
        let table_after_rollback = inner
            .raw_file
            .read_pointer_table(refcount_table_offset, 2, None)
            .unwrap();
        eprintln!(
            "REFBLOCK_TX_ROLLBACK post_sync table0={:#x} table1={:#x} old={old_refblock:#x}",
            table_after_rollback[0], table_after_rollback[1]
        );
        assert_eq!(table_after_rollback[0], old_refblock);
        assert_eq!(table_after_rollback[1], 0);

        // Trim only the unused deterministic-ENOSPC tail, then perform normal
        // final-owner clean shutdown. A complete rollback should permit DIRTY
        // to clear; it should not need the #634 containment mechanism.
        inner
            .raw_file
            .file_mut()
            .set_len(replacement_refblock + cluster_size)
            .unwrap();
        drop(super::QcowMetadata::new(inner));

        let header_file = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let header_after_shutdown = super::super::QcowHeader::new(&header_file).unwrap();
        let dirty_after_shutdown = super::super::header::IncompatFeatures::from_bits_truncate(
            header_after_shutdown.incompatible_features,
        )
        .contains(super::super::header::IncompatFeatures::DIRTY);
        assert!(!dirty_after_shutdown);

        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut reopened, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        let table_after_reopen = reopened
            .raw_file
            .read_pointer_table(refcount_table_offset, 2, None)
            .unwrap();
        let replacement_refcount_after = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut reopened;
            refcounts
                .get_cluster_refcount(raw_file, replacement_refblock)
                .unwrap()
        };
        eprintln!(
            "REFBLOCK_TX_ROLLBACK reopened table0={:#x} replacement_refcount={replacement_refcount_after} replacement_free={} free_tail={:#x?}",
            table_after_reopen[0],
            reopened.avail_clusters.contains(&replacement_refblock),
            reopened.avail_clusters.last().copied()
        );
        assert_eq!(table_after_reopen[0], old_refblock);
        assert_eq!(replacement_refcount_after, 0);
        assert!(reopened.avail_clusters.contains(&replacement_refblock));
        assert_eq!(reopened.avail_clusters.last().copied(), Some(replacement_refblock));

        let reused = reopened
            .get_new_cluster(Some(vec![0xa5; cluster_size as usize]))
            .expect("rolled-back replacement must be safely reusable");
        let table_after_reuse = reopened
            .raw_file
            .read_pointer_table(refcount_table_offset, 2, None)
            .unwrap();
        eprintln!(
            "REFBLOCK_TX_ROLLBACK allocator_reuse reused={reused:#x} table0={:#x}",
            table_after_reuse[0]
        );
        assert_eq!(reused, replacement_refblock);
        assert_eq!(table_after_reuse[0], old_refblock);
    }

    #[test]
    fn refblock_recursive_transaction_success_owns_chain_and_tracks_old_block() {
        let cluster_size: u64 = 1 << 16;
        let refcount_bits: u64 = 16;
        let refcount_block_entries = cluster_size * 8 / refcount_bits;

        let temp = super::super::QcowTempDisk::new(4 * 1024 * 1024 * 1024, None, false, true, false)
            .unwrap()
            .into_tempfile();
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut inner, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();

        let refcount_table_offset = inner.header.refcount_table_offset;
        let initial_table = inner
            .raw_file
            .read_pointer_table(refcount_table_offset, 2, None)
            .unwrap();
        let old_refblock = initial_table[0];
        assert_ne!(old_refblock, 0);
        assert_eq!(initial_table[1], 0);

        let target = inner.raw_file.file_mut().metadata().unwrap().len();
        let replacement_region0 = refcount_block_entries * cluster_size;
        let replacement_region1 = replacement_region0 + cluster_size;
        assert!(target < replacement_region0);

        inner
            .raw_file
            .file_mut()
            .set_len(replacement_region1 + cluster_size)
            .unwrap();
        inner.refcounts = super::super::refcount::RefCount::new(
            &mut inner.raw_file,
            refcount_table_offset,
            2,
            refcount_block_entries,
            cluster_size,
            refcount_bits,
        )
        .unwrap();
        inner.avail_clusters.clear();
        inner.unref_clusters.clear();

        // X is the target, Y replaces region 0, and Z becomes the new region-1
        // refblock that owns both Y and itself. This is the successful version
        // of the exact cross-region dependency that fails in #634.
        inner.avail_clusters.push(replacement_region1);
        inner.avail_clusters.push(replacement_region0);
        inner.avail_clusters.push(target);
        let allocated_target = inner.get_new_cluster(None).unwrap();
        assert_eq!(allocated_target, target);
        inner
            .set_cluster_refcount_track_freed(allocated_target, 1)
            .unwrap();

        let (target_refcount, y_refcount, z_refcount, old_refcount) = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut inner;
            (
                refcounts
                    .get_cluster_refcount(raw_file, allocated_target)
                    .unwrap(),
                refcounts
                    .get_cluster_refcount(raw_file, replacement_region0)
                    .unwrap(),
                refcounts
                    .get_cluster_refcount(raw_file, replacement_region1)
                    .unwrap(),
                refcounts
                    .get_cluster_refcount(raw_file, old_refblock)
                    .unwrap(),
            )
        };
        eprintln!(
            "REFBLOCK_TX_SUCCESS target={allocated_target:#x}:{target_refcount} y={replacement_region0:#x}:{y_refcount} z={replacement_region1:#x}:{z_refcount} old={old_refblock:#x}:{old_refcount} old_tracked={}",
            inner.unref_clusters.contains(&old_refblock)
        );
        assert_eq!(target_refcount, 1);
        assert_eq!(y_refcount, 1);
        assert_eq!(z_refcount, 1);
        assert_eq!(old_refcount, 0);
        assert!(
            inner.unref_clusters.contains(&old_refblock),
            "recursive ownership must propagate freed old refblocks to caller bookkeeping"
        );

        drop(super::QcowMetadata::new(inner));

        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut reopened, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        let table_after_reopen = reopened
            .raw_file
            .read_pointer_table(refcount_table_offset, 2, None)
            .unwrap();
        let (target_after, y_after, z_after, old_after) = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut reopened;
            (
                refcounts
                    .get_cluster_refcount(raw_file, allocated_target)
                    .unwrap(),
                refcounts
                    .get_cluster_refcount(raw_file, replacement_region0)
                    .unwrap(),
                refcounts
                    .get_cluster_refcount(raw_file, replacement_region1)
                    .unwrap(),
                refcounts
                    .get_cluster_refcount(raw_file, old_refblock)
                    .unwrap(),
            )
        };
        eprintln!(
            "REFBLOCK_TX_SUCCESS reopened table0={:#x} table1={:#x} target={target_after} y={y_after} z={z_after} old={old_after} old_free={}",
            table_after_reopen[0],
            table_after_reopen[1],
            reopened.avail_clusters.contains(&old_refblock)
        );
        assert_eq!(table_after_reopen[0], replacement_region0);
        assert_eq!(table_after_reopen[1], replacement_region1);
        assert_eq!(target_after, 1);
        assert_eq!(y_after, 1);
        assert_eq!(z_after, 1);
        assert_eq!(old_after, 0);
        assert!(reopened.avail_clusters.contains(&old_refblock));
    }
'''

path.write_text(text[:end] + probe + text[end:])
