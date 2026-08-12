#!/usr/bin/env python3
from pathlib import Path

vec_cache = Path("block/src/formats/qcow/vec_cache.rs")
refcount = Path("block/src/formats/qcow/refcount.rs")
metadata = Path("block/src/formats/qcow/metadata.rs")

v = vec_cache.read_text()
r = refcount.read_text()
m = metadata.read_text()

# ---- VecCache / CacheMap rollback helpers ----
mark_clean_old = '''    /// Mark this cache element as clean.\n    pub(super) fn mark_clean(&mut self) {\n        self.dirty = false;\n    }\n'''
mark_clean_new = '''    /// Mark this cache element as clean.\n    pub(super) fn mark_clean(&mut self) {\n        self.dirty = false;\n    }\n\n    /// Restore an explicit dirty state while rolling metadata back.\n    pub(super) fn set_dirty(&mut self, dirty: bool) {\n        self.dirty = dirty;\n    }\n'''
if mark_clean_old not in v:
    raise SystemExit("VecCache mark_clean anchor missing")
v = v.replace(mark_clean_old, mark_clean_new, 1)

get_mut_old = '''    pub(super) fn get_mut(&mut self, index: usize) -> Option<&mut T> {\n        self.map.get_mut(&index)\n    }\n\n    pub(super) fn iter_mut(&mut self) -> IterMut<'_, usize, T> {\n'''
get_mut_new = '''    pub(super) fn get_mut(&mut self, index: usize) -> Option<&mut T> {\n        self.map.get_mut(&index)\n    }\n\n    /// Remove one entry without invoking the normal eviction callback.\n    /// Used only to restore a previously captured cache state.\n    pub(super) fn remove_for_rollback(&mut self, index: usize) -> Option<T> {\n        self.map.remove(&index)\n    }\n\n    /// Restore one previously captured entry without evicting another entry.\n    /// Journal rollback removes every transaction-touched entry first, so this\n    /// reconstructs prior cache residency without triggering new I/O.\n    pub(super) fn restore_without_evict(&mut self, index: usize, block: T) {\n        self.map.insert(index, block);\n    }\n\n    pub(super) fn iter_mut(&mut self) -> IterMut<'_, usize, T> {\n'''
if get_mut_old not in v:
    raise SystemExit("CacheMap get_mut anchor missing")
v = v.replace(get_mut_old, get_mut_new, 1)

# ---- RefCount bounded undo journal ----
import_old = 'use std::{io, result};\n'
import_new = 'use std::collections::HashMap;\nuse std::{io, result};\n'
if import_old not in r:
    raise SystemExit("refcount import anchor missing")
r = r.replace(import_old, import_new, 1)

struct_old = '''#[derive(Clone, Debug)]\npub(super) struct RefCount {\n    ref_table: VecCache<u64>,\n    refcount_table_offset: u64,\n    refblock_cache: CacheMap<VecCache<u64>>,\n    refcount_block_entries: u64, // number of refcounts in a cluster.\n    cluster_size: u64,\n    max_valid_cluster_offset: u64,\n    max_refcount: u64,  // maximum refcount value for this image's refcount_order\n    refcount_bits: u64, // number of bits per refcount entry\n}\n'''
struct_new = '''#[derive(Clone, Debug)]\npub(super) struct RefCount {\n    ref_table: VecCache<u64>,\n    refcount_table_offset: u64,\n    refblock_cache: CacheMap<VecCache<u64>>,\n    refcount_block_entries: u64, // number of refcounts in a cluster.\n    cluster_size: u64,\n    max_valid_cluster_offset: u64,\n    max_refcount: u64,  // maximum refcount value for this image's refcount_order\n    refcount_bits: u64, // number of bits per refcount entry\n}\n\n#[derive(Debug)]\npub(super) struct RefcountUndo {\n    ref_table_dirty: bool,\n    regions: HashMap<usize, RefcountRegionUndo>,\n}\n\n#[derive(Debug)]\nstruct RefcountRegionUndo {\n    table_addr: u64,\n    cached_block: Option<VecCache<u64>>,\n}\n'''
if struct_old not in r:
    raise SystemExit("RefCount struct anchor missing")
r = r.replace(struct_old, struct_new, 1)

max_valid_old = '''    /// Returns the maximum valid cluster offset in the raw file for this refcount table.\n    pub(super) fn max_valid_cluster_offset(&self) -> u64 {\n        self.max_valid_cluster_offset\n    }\n\n    /// Returns `NeedNewCluster` if a new cluster needs to be allocated for refcounts. If an\n'''
max_valid_new = '''    /// Returns the maximum valid cluster offset in the raw file for this refcount table.\n    pub(super) fn max_valid_cluster_offset(&self) -> u64 {\n        self.max_valid_cluster_offset\n    }\n\n    /// Start a bounded undo journal for one recursive refcount transaction.\n    /// The top-level pointer table can be large, so only regions that actually\n    /// mutate are captured later.\n    pub(super) fn begin_undo(&self) -> RefcountUndo {\n        RefcountUndo {\n            ref_table_dirty: self.ref_table.dirty(),\n            regions: HashMap::new(),\n        }\n    }\n\n    fn capture_undo_region(&self, undo: &mut RefcountUndo, table_index: usize) {\n        if undo.regions.contains_key(&table_index) {\n            return;\n        }\n        undo.regions.insert(\n            table_index,\n            RefcountRegionUndo {\n                table_addr: self.ref_table[table_index],\n                cached_block: self.refblock_cache.get(table_index).cloned(),\n            },\n        );\n    }\n\n    /// Restore only regions touched by the transaction. Restored cache blocks\n    /// are marked dirty even if they were previously clean: a transaction-era\n    /// cache eviction may already have written speculative contents, so the\n    /// next normal metadata flush must reassert the captured logical state.\n    pub(super) fn rollback_undo(&mut self, undo: RefcountUndo) {\n        let RefcountUndo {\n            ref_table_dirty,\n            regions,\n        } = undo;\n\n        for table_index in regions.keys() {\n            self.refblock_cache.remove_for_rollback(*table_index);\n        }\n\n        for (table_index, region) in regions {\n            self.ref_table[table_index] = region.table_addr;\n            if let Some(mut cached_block) = region.cached_block {\n                cached_block.set_dirty(true);\n                self.refblock_cache\n                    .restore_without_evict(table_index, cached_block);\n            }\n        }\n        self.ref_table.set_dirty(ref_table_dirty);\n    }\n\n    /// Returns `NeedNewCluster` if a new cluster needs to be allocated for refcounts. If an\n'''
if max_valid_old not in r:
    raise SystemExit("max_valid anchor missing")
r = r.replace(max_valid_old, max_valid_new, 1)

set_old = r'''    pub(super) fn set_cluster_refcount(
        &mut self,
        raw_file: &mut QcowRawFile,
        cluster_address: u64,
        refcount: u64,
        mut new_cluster: Option<(u64, VecCache<u64>)>,
    ) -> Result<Option<u64>> {
        if refcount > self.max_refcount {
            return Err(Error::RefcountOverflow {
                value: refcount,
                max: self.max_refcount,
                refcount_bits: self.refcount_bits,
            });
        }

        let (table_index, block_index) = self.get_refcount_index(cluster_address);

        let block_addr_disk = *self.ref_table.get(table_index).ok_or(Error::InvalidIndex)?;

        // Fill the cache if this block isn't yet there.
        if !self.refblock_cache.contains_key(table_index) {
            // Need a new cluster
            if let Some((addr, table)) = new_cluster.take() {
                self.ref_table[table_index] = addr;
                let ref_table = &self.ref_table;
                self.refblock_cache
                    .insert(table_index, table, |index, evicted| {
                        raw_file.write_refcount_block(ref_table[index], evicted.get_values())
                    })
                    .map_err(Error::EvictingRefCounts)?;
            } else {
                if block_addr_disk == 0 {
                    return Err(Error::NeedNewCluster);
                }
                return Err(Error::NeedCluster(block_addr_disk));
            }
        }

        // Unwrap is safe here as the entry was filled directly above.
        let dropped_cluster = if self.refblock_cache.get(table_index).unwrap().dirty() {
            None
        } else {
            // Free the previously used block and use a new one. Writing modified counts to new
            // blocks keeps the on-disk state consistent even if it's out of date.
            if let Some((addr, _)) = new_cluster.take() {
                self.ref_table[table_index] = addr;
                Some(block_addr_disk)
            } else {
                return Err(Error::NeedNewCluster);
            }
        };

        self.refblock_cache.get_mut(table_index).unwrap()[block_index] = refcount;
        Ok(dropped_cluster)
    }
'''

set_new = r'''    pub(super) fn set_cluster_refcount(
        &mut self,
        raw_file: &mut QcowRawFile,
        cluster_address: u64,
        refcount: u64,
        new_cluster: Option<(u64, VecCache<u64>)>,
    ) -> Result<Option<u64>> {
        self.set_cluster_refcount_with_undo(
            raw_file,
            cluster_address,
            refcount,
            new_cluster,
            None,
        )
    }

    pub(super) fn set_cluster_refcount_with_undo(
        &mut self,
        raw_file: &mut QcowRawFile,
        cluster_address: u64,
        refcount: u64,
        mut new_cluster: Option<(u64, VecCache<u64>)>,
        mut undo: Option<&mut RefcountUndo>,
    ) -> Result<Option<u64>> {
        if refcount > self.max_refcount {
            return Err(Error::RefcountOverflow {
                value: refcount,
                max: self.max_refcount,
                refcount_bits: self.refcount_bits,
            });
        }

        let (table_index, block_index) = self.get_refcount_index(cluster_address);

        let block_addr_disk = *self.ref_table.get(table_index).ok_or(Error::InvalidIndex)?;

        // Fill the cache if this block isn't yet there.
        if !self.refblock_cache.contains_key(table_index) {
            // Need a new cluster
            if let Some((addr, table)) = new_cluster.take() {
                if let Some(undo) = undo.as_deref_mut() {
                    self.capture_undo_region(undo, table_index);
                }
                self.ref_table[table_index] = addr;
                let ref_table = &self.ref_table;
                self.refblock_cache
                    .insert(table_index, table, |index, evicted| {
                        raw_file.write_refcount_block(ref_table[index], evicted.get_values())
                    })
                    .map_err(Error::EvictingRefCounts)?;
            } else {
                if block_addr_disk == 0 {
                    return Err(Error::NeedNewCluster);
                }
                return Err(Error::NeedCluster(block_addr_disk));
            }
        }

        // Every path below mutates either a cached refcount, the top-level
        // pointer for this region, or both. Capture the first pre-transaction
        // state before that mutation. If the cache was inserted above, this is
        // already journaled and therefore a no-op.
        if let Some(undo) = undo.as_deref_mut() {
            self.capture_undo_region(undo, table_index);
        }

        // Unwrap is safe here as the entry was filled directly above.
        let dropped_cluster = if self.refblock_cache.get(table_index).unwrap().dirty() {
            None
        } else {
            // Free the previously used block and use a new one. Writing modified counts to new
            // blocks keeps the on-disk state consistent even if it's out of date.
            if let Some((addr, _)) = new_cluster.take() {
                self.ref_table[table_index] = addr;
                Some(block_addr_disk)
            } else {
                return Err(Error::NeedNewCluster);
            }
        };

        self.refblock_cache.get_mut(table_index).unwrap()[block_index] = refcount;
        Ok(dropped_cluster)
    }
'''
if set_old not in r:
    raise SystemExit("RefCount set_cluster_refcount anchor missing")
r = r.replace(set_old, set_new, 1)

# ---- Metadata transaction wrapper using the bounded journal ----
meta_old = r'''    /// Sets the refcount for a cluster. Returns freed cluster addresses.
    fn set_cluster_refcount(&mut self, address: u64, refcount: u64) -> io::Result<Vec<u64>> {
        let mut added_clusters = Vec::new();
        let mut unref_clusters = Vec::new();
        let mut refcount_set = false;
        let mut new_cluster = None;

        while !refcount_set {
            match self.refcounts.set_cluster_refcount(
                &mut self.raw_file,
                address,
                refcount,
                new_cluster.take(),
            ) {
                Ok(None) => {
                    refcount_set = true;
                }
                Ok(Some(freed_cluster)) => {
                    let mut freed = self.set_cluster_refcount(freed_cluster, 0)?;
                    unref_clusters.push(freed_cluster);
                    unref_clusters.append(&mut freed);
                    refcount_set = true;
                }
                Err(refcount::Error::EvictingRefCounts(e)) => {
                    return Err(e);
                }
                Err(refcount::Error::InvalidIndex) => {
                    self.set_corrupt_bit_best_effort();
                    return Err(io::Error::from_raw_os_error(EINVAL));
                }
                Err(refcount::Error::NeedCluster(addr)) => {
                    new_cluster = Some((
                        addr,
                        VecCache::from_vec(self.raw_file.read_refcount_block(addr)?),
                    ));
                }
                Err(refcount::Error::NeedNewCluster) => {
                    let addr = self.get_new_cluster(None)?;
                    added_clusters.push(addr);
                    new_cluster = Some((
                        addr,
                        VecCache::new(self.refcounts.refcounts_per_block() as usize),
                    ));
                }
                Err(refcount::Error::ReadingRefCounts(e)) => {
                    return Err(e);
                }
                Err(refcount::Error::RefcountOverflow { .. }) => {
                    return Err(io::Error::from_raw_os_error(EINVAL));
                }
                Err(refcount::Error::RefblockUnaligned(_)) => {
                    self.set_corrupt_bit_best_effort();
                    return Err(io::Error::from_raw_os_error(EIO));
                }
            }
        }

        for addr in added_clusters {
            self.set_cluster_refcount(addr, 1)?;
        }
        Ok(unref_clusters)
    }
'''

meta_new = r'''    /// Sets the refcount for a cluster. Returns freed cluster addresses.
    ///
    /// Refcount-block ownership can recurse into more refcount regions. Start
    /// one bounded undo journal at the first replacement allocation and share
    /// it across the complete dependency chain. Allocator ENOSPC can then
    /// restore only the regions that were actually touched.
    fn set_cluster_refcount(&mut self, address: u64, refcount: u64) -> io::Result<Vec<u64>> {
        let mut undo = None;
        let mut allocated_refcount_clusters = Vec::new();
        let result = self.set_cluster_refcount_inner(
            address,
            refcount,
            &mut undo,
            &mut allocated_refcount_clusters,
        );

        if let Err(ref e) = result
            && e.raw_os_error() == Some(libc::ENOSPC)
            && let Some(undo) = undo.take()
        {
            self.refcounts.rollback_undo(undo);
            // get_new_cluster() consumes avail_clusters in LIFO order. Restore
            // failed transaction allocations in reverse consumption order so
            // allocator order matches the pre-transaction state.
            for addr in allocated_refcount_clusters.into_iter().rev() {
                self.avail_clusters.push(addr);
            }
        }

        result
    }

    fn set_cluster_refcount_inner(
        &mut self,
        address: u64,
        refcount: u64,
        undo: &mut Option<refcount::RefcountUndo>,
        allocated_refcount_clusters: &mut Vec<u64>,
    ) -> io::Result<Vec<u64>> {
        let mut added_clusters = Vec::new();
        let mut unref_clusters = Vec::new();
        let mut refcount_set = false;
        let mut new_cluster = None;

        while !refcount_set {
            match self.refcounts.set_cluster_refcount_with_undo(
                &mut self.raw_file,
                address,
                refcount,
                new_cluster.take(),
                undo.as_mut(),
            ) {
                Ok(None) => {
                    refcount_set = true;
                }
                Ok(Some(freed_cluster)) => {
                    let mut freed = self.set_cluster_refcount_inner(
                        freed_cluster,
                        0,
                        undo,
                        allocated_refcount_clusters,
                    )?;
                    unref_clusters.push(freed_cluster);
                    unref_clusters.append(&mut freed);
                    refcount_set = true;
                }
                Err(refcount::Error::EvictingRefCounts(e)) => {
                    return Err(e);
                }
                Err(refcount::Error::InvalidIndex) => {
                    self.set_corrupt_bit_best_effort();
                    return Err(io::Error::from_raw_os_error(EINVAL));
                }
                Err(refcount::Error::NeedCluster(addr)) => {
                    new_cluster = Some((
                        addr,
                        VecCache::from_vec(self.raw_file.read_refcount_block(addr)?),
                    ));
                }
                Err(refcount::Error::NeedNewCluster) => {
                    // NeedNewCluster is reported before the target region is
                    // modified, so this is the last safe point to arm rollback.
                    if undo.is_none() {
                        *undo = Some(self.refcounts.begin_undo());
                    }
                    let addr = self.get_new_cluster(None)?;
                    allocated_refcount_clusters.push(addr);
                    added_clusters.push(addr);
                    new_cluster = Some((
                        addr,
                        VecCache::new(self.refcounts.refcounts_per_block() as usize),
                    ));
                }
                Err(refcount::Error::ReadingRefCounts(e)) => {
                    return Err(e);
                }
                Err(refcount::Error::RefcountOverflow { .. }) => {
                    return Err(io::Error::from_raw_os_error(EINVAL));
                }
                Err(refcount::Error::RefblockUnaligned(_)) => {
                    self.set_corrupt_bit_best_effort();
                    return Err(io::Error::from_raw_os_error(EIO));
                }
            }
        }

        for addr in added_clusters {
            let mut freed = self.set_cluster_refcount_inner(
                addr,
                1,
                undo,
                allocated_refcount_clusters,
            )?;
            unref_clusters.append(&mut freed);
        }
        Ok(unref_clusters)
    }
'''
if meta_old not in m:
    raise SystemExit("metadata set_cluster_refcount anchor missing")
m = m.replace(meta_old, meta_new, 1)

vec_cache.write_text(v)
refcount.write_text(r)
metadata.write_text(m)
