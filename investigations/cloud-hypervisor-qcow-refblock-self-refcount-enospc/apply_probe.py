#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/formats/qcow/metadata.rs")
text = path.read_text()
marker = "refblock_recursive_ownership_enospc_reopen_reuses_live_block"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

end = text.rfind("\n}")
if end == -1:
    raise SystemExit(f"could not find final unit-test module close in {path}")

probe = r'''

    #[test]
    fn refblock_recursive_ownership_enospc_reopen_reuses_live_block() {
        let cluster_size: u64 = 1 << 16;
        let refcount_bits: u64 = 16;
        let refcount_block_entries = cluster_size * 8 / refcount_bits;
        assert_eq!(refcount_block_entries, 32_768);

        let temp = super::super::QcowTempDisk::new(4 * cluster_size, None, false, true, false)
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
        assert_ne!(initial_table[0], 0);
        assert_eq!(initial_table[1], 0);

        let initial_size = inner.raw_file.file_mut().metadata().unwrap().len();
        assert_eq!(initial_size % cluster_size, 0);
        let target = initial_size;
        assert!(target / cluster_size < refcount_block_entries);

        // Y is the first cluster covered by refcount-table entry 1. It is a
        // valid replacement refblock address but its own refcount therefore
        // lives in a different refcount region from the block it will replace.
        let replacement_refblock = refcount_block_entries * cluster_size;

        // Keep real 64 KiB/16-bit geometry, but cap this in-memory RefCount at
        // exactly two regions and sparse-extend to the end of that horizon.
        // Once X and Y are consumed, add_cluster_end() deterministically
        // returns ENOSPC just as host ENOSPC would.
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

        // LIFO: allocate X first as the object whose refcount is being set;
        // Y remains as the only cluster available for refblock relocation.
        inner.avail_clusters.push(replacement_refblock);
        inner.avail_clusters.push(target);
        let allocated_target = inner.get_new_cluster(None).unwrap();
        assert_eq!(allocated_target, target);

        let err = inner
            .set_cluster_refcount_track_freed(allocated_target, 1)
            .expect_err("recursive ownership of replacement refblock must hit ENOSPC");
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
            "REFBLOCK_OWNERSHIP_FAIL pre_close target={allocated_target:#x} target_refcount={target_refcount} replacement={replacement_refblock:#x} replacement_refcount={replacement_refcount} in_avail={} in_unref={}",
            inner.avail_clusters.contains(&replacement_refblock),
            inner.unref_clusters.contains(&replacement_refblock)
        );
        assert_eq!(target_refcount, 1);
        assert_eq!(replacement_refcount, 0);
        assert!(!inner.avail_clusters.contains(&replacement_refblock));
        assert!(!inner.unref_clusters.contains(&replacement_refblock));

        // Remove only the unused sparse tail that existed to make ENOSPC
        // deterministic. X, Y, and all original metadata remain in-range.
        inner
            .raw_file
            .file_mut()
            .set_len(replacement_refblock + cluster_size)
            .unwrap();

        // Production clean-close owner flushes the dirty refblock to Y, then
        // flushes refcount-table entry 0 -> Y and clears DIRTY.
        drop(super::QcowMetadata::new(inner));

        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut reopened, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        let table_after_reopen = reopened
            .raw_file
            .read_pointer_table(refcount_table_offset, 2, None)
            .unwrap();
        let (reopened_target_refcount, reopened_replacement_refcount) = {
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
                    .get_cluster_refcount(raw_file, replacement_refblock)
                    .unwrap(),
            )
        };
        let free_tail = reopened.avail_clusters.last().copied();
        eprintln!(
            "REFBLOCK_OWNERSHIP_FAIL reopened table0={:#x} table1={:#x} target_refcount={reopened_target_refcount} replacement_refcount={reopened_replacement_refcount} free_contains={} free_tail={free_tail:#x?}",
            table_after_reopen[0],
            table_after_reopen[1],
            reopened.avail_clusters.contains(&replacement_refblock)
        );
        assert_eq!(table_after_reopen[0], replacement_refblock);
        assert_eq!(table_after_reopen[1], 0);
        assert_eq!(reopened_target_refcount, 1);
        assert_eq!(reopened_replacement_refcount, 0);
        assert!(reopened.avail_clusters.contains(&replacement_refblock));
        assert_eq!(free_tail, Some(replacement_refblock));

        // Reuse the live refcount block through the ordinary allocator and
        // overwrite it with a valid nonzero guest-data-like marker. 0xa5a5 is
        // also a legal 16-bit refcount, so the old "first cluster refcount is
        // zero" rebuild heuristic will not rescue the next clean reopen.
        let marker = vec![0xa5; cluster_size as usize];
        let reused = reopened
            .get_new_cluster(Some(marker))
            .expect("allocator should return the still-referenced refcount block");
        assert_eq!(reused, replacement_refblock);
        let table_after_reuse = reopened
            .raw_file
            .read_pointer_table(refcount_table_offset, 2, None)
            .unwrap();
        let mut overwritten_prefix = [0u8; 8];
        use std::os::unix::fs::FileExt;
        reopened
            .raw_file
            .file()
            .read_exact_at(&mut overwritten_prefix, replacement_refblock)
            .unwrap();
        eprintln!(
            "REFBLOCK_OWNERSHIP_FAIL allocator_reuse reused={reused:#x} table0={:#x} marker={overwritten_prefix:02x?}",
            table_after_reuse[0]
        );
        assert_eq!(table_after_reuse[0], replacement_refblock);
        assert_eq!(overwritten_prefix, [0xa5; 8]);

        // Clean close does not rewrite the now-stale *clean* refblock cache.
        // On the next writable reopen, the first refcount read from Y is
        // 0xa5a5 rather than zero, so the legacy broken-refcount heuristic does
        // not trigger a rebuild. The parser trusts guest-data bytes as the
        // region-0 refcount block.
        drop(super::QcowMetadata::new(reopened));

        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut reopened_again, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        let table_after_second_reopen = reopened_again
            .raw_file
            .read_pointer_table(refcount_table_offset, 2, None)
            .unwrap();
        let (corrupt_first_refcount, corrupt_target_refcount, replacement_still_zero) = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut reopened_again;
            (
                refcounts.get_cluster_refcount(raw_file, 0).unwrap(),
                refcounts
                    .get_cluster_refcount(raw_file, allocated_target)
                    .unwrap(),
                refcounts
                    .get_cluster_refcount(raw_file, replacement_refblock)
                    .unwrap(),
            )
        };
        eprintln!(
            "REFBLOCK_OWNERSHIP_FAIL second_reopen table0={:#x} first_refcount={corrupt_first_refcount:#x} target_refcount={corrupt_target_refcount:#x} replacement_refcount={replacement_still_zero} replacement_free={}",
            table_after_second_reopen[0],
            reopened_again.avail_clusters.contains(&replacement_refblock)
        );
        assert_eq!(table_after_second_reopen[0], replacement_refblock);
        assert_eq!(corrupt_first_refcount, 0xa5a5);
        assert_eq!(corrupt_target_refcount, 0xa5a5);
        assert_eq!(replacement_still_zero, 0);
        assert!(reopened_again.avail_clusters.contains(&replacement_refblock));
    }
'''

path.write_text(text[:end] + probe + text[end:])
