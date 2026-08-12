#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/formats/qcow/refcount.rs")
text = path.read_text()
marker = "failed_refblock_eviction_loses_dirty_victim_after_pointer_swap"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

probe = r'''

#[cfg(test)]
mod eviction_error_unit_tests {
    use super::*;
    use std::fs::{OpenOptions, remove_file};
    use std::time::{SystemTime, UNIX_EPOCH};

    #[test]
    fn failed_refblock_eviction_loses_dirty_victim_after_pointer_swap() {
        let cluster_size = 4096u64;
        let refcount_bits = 16u64;
        let entries_per_block = cluster_size * 8 / refcount_bits;
        let old_region1_block = cluster_size;
        let new_region0_block = 2 * cluster_size;

        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = std::env::temp_dir().join(format!(
            "cloud-hypervisor-refcount-evict-{}-{nonce}.qcow",
            std::process::id()
        ));

        let seed = OpenOptions::new()
            .create_new(true)
            .read(true)
            .write(true)
            .open(&path)
            .unwrap();
        seed.set_len(4 * cluster_size).unwrap();
        drop(seed);

        let read_only = OpenOptions::new().read(true).open(&path).unwrap();
        let mut raw = QcowRawFile::from(
            crate::AlignedFile::new(read_only, false),
            cluster_size,
            refcount_bits,
        )
        .unwrap();

        let mut refcounts = RefCount {
            ref_table: VecCache::from_vec(vec![0, old_region1_block]),
            refcount_table_offset: 0,
            refblock_cache: CacheMap::new(1),
            refcount_block_entries: entries_per_block,
            cluster_size,
            max_valid_cluster_offset: (2 * entries_per_block - 1) * cluster_size,
            max_refcount: u16::MAX as u64,
            refcount_bits,
        };

        let mut dirty_victim = VecCache::new(entries_per_block as usize);
        dirty_victim[0] = 7;
        refcounts
            .refblock_cache
            .insert(1, dirty_victim, |_index, _evicted| Ok(()))
            .unwrap();
        assert!(refcounts.refblock_cache.contains_key(1));

        let err = refcounts
            .set_cluster_refcount(
                &mut raw,
                0,
                1,
                Some((
                    new_region0_block,
                    VecCache::new(entries_per_block as usize),
                )),
            )
            .expect_err("read-only metadata fd must fail dirty-victim eviction write");
        assert!(matches!(err, Error::EvictingRefCounts(_)));

        eprintln!(
            "REFCOUNT_EVICT_FAIL after_error table0={:#x} victim_cached={} new_cached={}",
            refcounts.ref_table[0],
            refcounts.refblock_cache.contains_key(1),
            refcounts.refblock_cache.contains_key(0),
        );
        assert_eq!(refcounts.ref_table[0], new_region0_block);
        assert!(
            !refcounts.refblock_cache.contains_key(1),
            "failed eviction dropped the dirty victim from cache"
        );
        assert!(
            !refcounts.refblock_cache.contains_key(0),
            "new cache insertion must not complete after callback error"
        );
        drop(raw);

        // Model a later normal metadata retry with a writable fd. The cache no
        // longer contains the dirty region-1 block, so flush_blocks() has
        // nothing to rewrite and succeeds. The already-mutated top-level table
        // can then be flushed successfully.
        let writable = OpenOptions::new().read(true).write(true).open(&path).unwrap();
        let mut raw = QcowRawFile::from(
            crate::AlignedFile::new(writable, false),
            cluster_size,
            refcount_bits,
        )
        .unwrap();
        refcounts
            .flush_blocks(&mut raw)
            .expect("later block flush sees no retained dirty victim");
        assert!(
            refcounts.flush_table(&mut raw).unwrap(),
            "mutated refcount table is still dirty and can be persisted"
        );

        let table = raw.read_pointer_table(0, 2, None).unwrap();
        let lost_victim_disk = raw.read_refcount_block(old_region1_block).unwrap();
        let unwritten_new_disk = raw.read_refcount_block(new_region0_block).unwrap();
        eprintln!(
            "REFCOUNT_EVICT_FAIL post_retry table0={:#x} victim_disk0={} new_disk0={}",
            table[0], lost_victim_disk[0], unwritten_new_disk[0]
        );
        assert_eq!(table[0], new_region0_block);
        assert_eq!(
            lost_victim_disk[0], 0,
            "the dirty victim value 7 was lost rather than retried"
        );
        assert_eq!(
            unwritten_new_disk[0], 0,
            "new table pointer can be persisted even though its cache insertion failed"
        );

        drop(raw);
        remove_file(path).unwrap();
    }
}
'''

path.write_text(text + probe)
