#!/usr/bin/env python3
from pathlib import Path

vec_cache = Path("block/src/formats/qcow/vec_cache.rs")
refcount = Path("block/src/formats/qcow/refcount.rs")
metadata = Path("block/src/formats/qcow/metadata.rs")

v = vec_cache.read_text()
r = refcount.read_text()
m = metadata.read_text()
marker = "refblock_journal_rolls_back_dirty_sibling_after_eviction"
if marker in m:
    raise SystemExit("adversarial journal marker already present")

vc_old = '''    pub(super) fn restore_without_evict(&mut self, index: usize, block: T) {
        self.map.insert(index, block);
    }

    pub(super) fn iter_mut(&mut self) -> IterMut<'_, usize, T> {
'''
vc_new = '''    pub(super) fn restore_without_evict(&mut self, index: usize, block: T) {
        self.map.insert(index, block);
    }

    #[cfg(test)]
    pub(super) fn set_capacity_for_test(&mut self, capacity: usize) {
        assert!(capacity >= self.map.len());
        self.capacity = capacity;
    }

    pub(super) fn iter_mut(&mut self) -> IterMut<'_, usize, T> {
'''
if vc_old not in v:
    raise SystemExit("CacheMap rollback helper anchor missing")
v = v.replace(vc_old, vc_new, 1)

rc_old = '''        self.ref_table.set_dirty(ref_table_dirty);
    }

    /// Returns `NeedNewCluster` if a new cluster needs to be allocated for refcounts. If an
'''
rc_new = '''        self.ref_table.set_dirty(ref_table_dirty);
    }

    #[cfg(test)]
    pub(super) fn flush_cached_refblock_for_test(
        &mut self,
        raw_file: &mut QcowRawFile,
        table_index: usize,
    ) -> io::Result<()> {
        let addr = *self
            .ref_table
            .get(table_index)
            .ok_or_else(|| io::Error::from_raw_os_error(EINVAL))?;
        let block = self
            .refblock_cache
            .get_mut(table_index)
            .ok_or_else(|| io::Error::from_raw_os_error(EINVAL))?;
        raw_file.write_refcount_block(addr, block.get_values())?;
        block.mark_clean();
        Ok(())
    }

    #[cfg(test)]
    pub(super) fn set_refblock_cache_capacity_for_test(&mut self, capacity: usize) {
        self.refblock_cache.set_capacity_for_test(capacity);
    }

    #[cfg(test)]
    pub(super) fn ref_table_addr_for_test(&self, table_index: usize) -> u64 {
        self.ref_table[table_index]
    }

    #[cfg(test)]
    pub(super) fn cached_refblock_dirty_for_test(&self, table_index: usize) -> Option<bool> {
        self.refblock_cache.get(table_index).map(Cacheable::dirty)
    }

    /// Returns `NeedNewCluster` if a new cluster needs to be allocated for refcounts. If an
'''
if rc_old not in r:
    raise SystemExit("RefCount rollback helper anchor missing")
r = r.replace(rc_old, rc_new, 1)

end = m.rfind("\n}")
if end == -1:
    raise SystemExit("could not find metadata unit-test module close")

probe = r'''

    #[test]
    fn refblock_journal_rolls_back_dirty_sibling_after_eviction() {
        let cluster_size: u64 = 1 << 16;
        let refcount_bits: u64 = 16;
        let refcount_block_entries = cluster_size * 8 / refcount_bits;
        let region_span = refcount_block_entries * cluster_size;
        assert_eq!(region_span, 0x8000_0000);

        let temp = super::super::QcowTempDisk::new(4 * 1024 * 1024 * 1024, None, false, true, false)
            .unwrap()
            .into_tempfile();
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut inner, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();

        let refcount_table_offset = inner.header.refcount_table_offset;
        let initial_table = inner
            .raw_file
            .read_pointer_table(refcount_table_offset, 4, None)
            .unwrap();
        let original_region0 = initial_table[0];
        assert_ne!(original_region0, 0);
        assert_eq!(initial_table[1], 0);
        assert_eq!(initial_table[2], 0);
        assert_eq!(initial_table[3], 0);

        // Four refcount regions give an 8 GiB deterministic allocation horizon.
        let artificial_table_entries = 4u64;
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

        // Build a coherent first transaction without flushing the metadata
        // caches: table0 -> Y, table1 -> Z, and both cached blocks are dirty.
        let target1 = 0x40000;
        let y = region_span;
        let z = region_span + cluster_size;
        inner.avail_clusters.push(z);
        inner.avail_clusters.push(y);
        inner.avail_clusters.push(target1);
        assert_eq!(inner.get_new_cluster(None).unwrap(), target1);
        inner
            .set_cluster_refcount_track_freed(target1, 1)
            .unwrap();
        assert_eq!(inner.refcounts.ref_table_addr_for_test(0), y);
        assert_eq!(inner.refcounts.ref_table_addr_for_test(1), z);
        assert_eq!(inner.refcounts.cached_refblock_dirty_for_test(0), Some(true));
        assert_eq!(inner.refcounts.cached_refblock_dirty_for_test(1), Some(true));

        // Make only table0 clean. Table1 stays dirty with the successful first
        // transaction's Y/Z ownership. Reducing capacity to the current two
        // entries means inserting table2 later must evict table0 or table1.
        inner
            .refcounts
            .flush_cached_refblock_for_test(&mut inner.raw_file, 0)
            .unwrap();
        assert_eq!(inner.refcounts.cached_refblock_dirty_for_test(0), Some(false));
        assert_eq!(inner.refcounts.cached_refblock_dirty_for_test(1), Some(true));
        inner.refcounts.set_refblock_cache_capacity_for_test(2);

        // Second transaction:
        // 1. clean table0 relocates from Y to A;
        // 2. releasing Y mutates pre-existing dirty table1 in place;
        // 3. owning A allocates table2 at B and forces eviction at capacity 2;
        // 4. owning B enters empty region3 and ENOSPCs with no allocation left.
        let target2 = target1 + cluster_size;
        let a = 2 * region_span;
        let b = 3 * region_span;
        inner.avail_clusters.clear();
        inner.avail_clusters.push(b);
        inner.avail_clusters.push(a);
        inner.avail_clusters.push(target2);
        assert_eq!(inner.get_new_cluster(None).unwrap(), target2);

        let unref_before = inner.unref_clusters.clone();
        let err = inner
            .set_cluster_refcount_track_freed(target2, 1)
            .expect_err("region3 recursive ownership must hit deterministic ENOSPC");
        assert_eq!(err.raw_os_error(), Some(libc::ENOSPC));
        assert_eq!(inner.unref_clusters, unref_before);
        assert_eq!(inner.avail_clusters, vec![b, a]);
        assert_eq!(inner.refcounts.ref_table_addr_for_test(0), y);
        assert_eq!(inner.refcounts.ref_table_addr_for_test(1), z);
        assert_eq!(inner.refcounts.ref_table_addr_for_test(2), 0);
        assert_eq!(inner.refcounts.ref_table_addr_for_test(3), 0);

        let (target1_rc, target2_rc, y_rc, z_rc, a_rc, b_rc) = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut inner;
            (
                refcounts.get_cluster_refcount(raw_file, target1).unwrap(),
                refcounts.get_cluster_refcount(raw_file, target2).unwrap(),
                refcounts.get_cluster_refcount(raw_file, y).unwrap(),
                refcounts.get_cluster_refcount(raw_file, z).unwrap(),
                refcounts.get_cluster_refcount(raw_file, a).unwrap(),
                refcounts.get_cluster_refcount(raw_file, b).unwrap(),
            )
        };
        eprintln!(
            "REFBLOCK_JOURNAL_EVICT post_error target1={target1_rc} target2={target2_rc} y={y_rc} z={z_rc} a={a_rc} b={b_rc} free={:#x?}",
            inner.avail_clusters
        );
        assert_eq!(target1_rc, 1);
        assert_eq!(target2_rc, 0);
        assert_eq!(y_rc, 1);
        assert_eq!(z_rc, 1);
        assert_eq!(a_rc, 0);
        assert_eq!(b_rc, 0);

        // This is the important durability discriminator. If inserting table2
        // evicted dirty transaction state, rollback's restored dirty snapshots
        // must repair it before the top-level refcount table is flushed.
        inner.sync_caches().unwrap();
        let table_after_rollback = inner
            .raw_file
            .read_pointer_table(refcount_table_offset, 4, None)
            .unwrap();
        eprintln!(
            "REFBLOCK_JOURNAL_EVICT post_sync table={:#x?}",
            table_after_rollback
        );
        assert_eq!(table_after_rollback[0], y);
        assert_eq!(table_after_rollback[1], z);
        assert_eq!(table_after_rollback[2], 0);
        assert_eq!(table_after_rollback[3], 0);

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
            .read_pointer_table(refcount_table_offset, 4, None)
            .unwrap();
        let (target1_after, target2_after, y_after, z_after, a_after, b_after) = {
            let super::QcowState {
                refcounts,
                raw_file,
                ..
            } = &mut reopened;
            (
                refcounts.get_cluster_refcount(raw_file, target1).unwrap(),
                refcounts.get_cluster_refcount(raw_file, target2).unwrap(),
                refcounts.get_cluster_refcount(raw_file, y).unwrap(),
                refcounts.get_cluster_refcount(raw_file, z).unwrap(),
                refcounts.get_cluster_refcount(raw_file, a).unwrap(),
                refcounts.get_cluster_refcount(raw_file, b).unwrap(),
            )
        };
        eprintln!(
            "REFBLOCK_JOURNAL_EVICT reopened table={:#x?} target1={target1_after} target2={target2_after} y={y_after} z={z_after} a={a_after} b={b_after} a_free={} b_free={}",
            table_after_reopen,
            reopened.avail_clusters.contains(&a),
            reopened.avail_clusters.contains(&b)
        );
        assert_eq!(table_after_reopen[0], y);
        assert_eq!(table_after_reopen[1], z);
        assert_eq!(table_after_reopen[2], 0);
        assert_eq!(table_after_reopen[3], 0);
        assert_eq!(target1_after, 1);
        assert_eq!(target2_after, 0);
        assert_eq!(y_after, 1);
        assert_eq!(z_after, 1);
        assert_eq!(a_after, 0);
        assert_eq!(b_after, 0);
        assert!(reopened.avail_clusters.contains(&a));
        assert!(reopened.avail_clusters.contains(&b));
    }
'''

m = m[:end] + probe + m[end:]
vec_cache.write_text(v)
refcount.write_text(r)
metadata.write_text(m)
