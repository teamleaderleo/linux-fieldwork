#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/formats/qcow/metadata.rs")
text = path.read_text()
marker = "refblock_recursive_enospc_retains_dirty_and_rebuilds"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

end = text.rfind("\n}")
if end == -1:
    raise SystemExit(f"could not find final unit-test module close in {path}")

probe = r'''

    #[test]
    fn refblock_recursive_enospc_retains_dirty_and_rebuilds() {
        let cluster_size: u64 = 1 << 16;
        let refcount_bits: u64 = 16;
        let refcount_block_entries = cluster_size * 8 / refcount_bits;
        assert_eq!(refcount_block_entries, 32_768);

        // The deterministic ENOSPC fixture sparse-extends the physical file
        // across two real refcount regions. Use a virtual geometry large
        // enough that DIRTY recovery accepts that physical extent, so the
        // containment test exercises refcount rebuild rather than the parser's
        // unrelated impossible-file-size rejection.
        let temp = super::super::QcowTempDisk::new(
            4 * 1024 * 1024 * 1024,
            None,
            false,
            true,
            false,
        )
        .unwrap()
        .into_tempfile();
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut inner, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();

        let refcount_table_offset = inner.header.refcount_table_offset;
        let initial_size = inner.raw_file.file_mut().metadata().unwrap().len();
        let target = initial_size;
        let replacement_refblock = refcount_block_entries * cluster_size;
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
        inner.avail_clusters.push(replacement_refblock);
        inner.avail_clusters.push(target);

        let allocated_target = inner.get_new_cluster(None).unwrap();
        assert_eq!(allocated_target, target);
        let err = inner
            .set_cluster_refcount_track_freed(allocated_target, 1)
            .expect_err("recursive refblock ownership must hit deterministic ENOSPC");
        assert_eq!(err.raw_os_error(), Some(libc::ENOSPC));
        assert!(
            inner.refcount_update_failed,
            "tracked refcount failure must poison clean-shutdown eligibility"
        );

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
        assert_eq!(target_refcount, 1);
        assert_eq!(replacement_refcount, 0);
        eprintln!(
            "REFBLOCK_DIRTY_CONTAIN pre_close target={allocated_target:#x} target_refcount={target_refcount} replacement={replacement_refblock:#x} replacement_refcount={replacement_refcount} poisoned={}",
            inner.refcount_update_failed
        );

        // Remove only the unused sparse tail that forces deterministic ENOSPC,
        // then run the real final-owner shutdown path.
        inner
            .raw_file
            .file_mut()
            .set_len(replacement_refblock + cluster_size)
            .unwrap();
        drop(super::QcowMetadata::new(inner));

        // Verify the candidate retained DIRTY on disk before parser recovery.
        let header_file = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let header_after_shutdown = super::super::QcowHeader::new(&header_file).unwrap();
        let dirty_after_shutdown = super::super::header::IncompatFeatures::from_bits_truncate(
            header_after_shutdown.incompatible_features,
        )
        .contains(super::super::header::IncompatFeatures::DIRTY);
        eprintln!(
            "REFBLOCK_DIRTY_CONTAIN post_shutdown dirty={dirty_after_shutdown} replacement={replacement_refblock:#x}"
        );
        assert!(dirty_after_shutdown);

        // Writable parse must rebuild because DIRTY was retained. The rebuild
        // may keep Y as a refblock or replace it, but it must never publish Y
        // as allocator-free while the top-level refcount table still reaches Y.
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut reopened, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        let table_after_rebuild = reopened
            .raw_file
            .read_pointer_table(refcount_table_offset, 2, None)
            .unwrap();
        let replacement_reachable = table_after_rebuild.contains(&replacement_refblock);
        let replacement_free = reopened.avail_clusters.contains(&replacement_refblock);
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
            "REFBLOCK_DIRTY_CONTAIN reopened table0={:#x} table1={:#x} replacement_refcount={replacement_refcount_after} reachable={replacement_reachable} free={replacement_free}",
            table_after_rebuild[0], table_after_rebuild[1]
        );
        assert!(
            !(replacement_reachable && replacement_free),
            "rebuild must not leave replacement refblock both reachable and allocator-free"
        );
        if replacement_reachable {
            assert_ne!(replacement_refcount_after, 0);
        }
    }
'''

path.write_text(text[:end] + probe + text[end:])
