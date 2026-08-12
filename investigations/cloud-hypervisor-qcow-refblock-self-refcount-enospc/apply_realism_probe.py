#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/formats/qcow/metadata.rs")
text = path.read_text()
marker = "refblock_recursive_enospc_from_parser_free_list"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

end = text.rfind("\n}")
if end == -1:
    raise SystemExit(f"could not find final unit-test module close in {path}")

probe = r'''

    #[test]
    fn refblock_recursive_enospc_from_parser_free_list() {
        let cluster_size: u64 = 1 << 16;
        let refcount_bits: u64 = 16;
        let refcount_block_entries = cluster_size * 8 / refcount_bits;
        assert_eq!(refcount_block_entries, 32_768);
        let replacement_refblock = refcount_block_entries * cluster_size;
        let artificial_table_entries = 2u64;
        let artificial_clusters = artificial_table_entries * refcount_block_entries;

        // Give the image a normal virtual geometry large enough that its
        // declared refcount table can represent both real refcount regions.
        // No guest data is written.
        let temp = super::super::QcowTempDisk::new(
            4 * 1024 * 1024 * 1024,
            None,
            false,
            true,
            false,
        )
        .unwrap()
        .into_tempfile();
        let initial_size = temp.as_file().metadata().unwrap().len();
        assert_eq!(initial_size % cluster_size, 0);
        let target = initial_size;
        assert!(target / cluster_size < refcount_block_entries);

        // Sparse-extend to the two-region horizon, then reopen through the
        // real parser. This time X and Y are not invented free-list entries:
        // the parser itself must classify both as refcount-0/free first.
        temp.as_file()
            .set_len(artificial_clusters * cluster_size)
            .unwrap();
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
        let parser_found_target = inner.avail_clusters.contains(&target);
        let parser_found_replacement = inner.avail_clusters.contains(&replacement_refblock);
        eprintln!(
            "REFBLOCK_REALISM parser_free target={target:#x} target_free={parser_found_target} replacement={replacement_refblock:#x} replacement_free={parser_found_replacement} free_count={}",
            inner.avail_clusters.len()
        );
        assert!(parser_found_target);
        assert!(parser_found_replacement);

        // Retain only those two parser-proven free clusters so the allocation
        // sequence is deterministic. Rebuild the in-memory RefCount with the
        // same real geometry but exactly two addressable regions; because EOF
        // is already at the end of that horizon, a third allocation returns
        // ENOSPC deterministically.
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
            .expect_err("recursive ownership of parser-free replacement must hit ENOSPC");
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
            "REFBLOCK_REALISM pre_close target_refcount={target_refcount} replacement_refcount={replacement_refcount} table0_pending={replacement_refblock:#x}"
        );
        assert_eq!(target_refcount, 1);
        assert_eq!(replacement_refcount, 0);

        // Discard only the unused sparse tail used to force ENOSPC. The
        // parser-proven replacement cluster Y remains the last physical
        // cluster and the normal clean-close path persists the pointer swap.
        inner
            .raw_file
            .file_mut()
            .set_len(replacement_refblock + cluster_size)
            .unwrap();
        drop(super::QcowMetadata::new(inner));

        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut reopened, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        let table_after_reopen = reopened
            .raw_file
            .read_pointer_table(refcount_table_offset, 2, None)
            .unwrap();
        let reopened_replacement_refcount = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut reopened;
            refcounts
                .get_cluster_refcount(raw_file, replacement_refblock)
                .unwrap()
        };
        let free_tail = reopened.avail_clusters.last().copied();
        eprintln!(
            "REFBLOCK_REALISM reopened table0={:#x} table1={:#x} replacement_refcount={reopened_replacement_refcount} free_contains={} free_tail={free_tail:#x?}",
            table_after_reopen[0],
            table_after_reopen[1],
            reopened.avail_clusters.contains(&replacement_refblock)
        );
        assert_eq!(table_after_reopen[0], replacement_refblock);
        assert_eq!(table_after_reopen[1], 0);
        assert_eq!(reopened_replacement_refcount, 0);
        assert!(reopened.avail_clusters.contains(&replacement_refblock));
        assert_eq!(free_tail, Some(replacement_refblock));

        let marker = vec![0x5a; cluster_size as usize];
        let reused = reopened
            .get_new_cluster(Some(marker))
            .expect("normal allocator should reuse parser-origin live refblock");
        eprintln!(
            "REFBLOCK_REALISM allocator_reuse reused={reused:#x} table0={:#x}",
            table_after_reopen[0]
        );
        assert_eq!(reused, replacement_refblock);
        assert_eq!(table_after_reopen[0], replacement_refblock);
    }
'''

path.write_text(text[:end] + probe + text[end:])
