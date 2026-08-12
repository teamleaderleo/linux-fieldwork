#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/formats/qcow/metadata.rs")
text = path.read_text()

replacements = [
    (
        '''        let mut set_refcounts = Vec::new();

        if let Some(new_addr) = self.cache_l2_cluster_alloc(l1_index, l2_addr_disk)? {
            set_refcounts.push((new_addr, 1));
        }
''',
        '''        let mut set_refcounts = Vec::new();

        self.cache_l2_cluster_alloc(l1_index, l2_addr_disk)?;
''',
        "map_write fresh-L2 caller",
    ),
    (
        '''    /// Populates the L2 cache for write operations and may allocate a new
    /// L2 table. Returns the address of the newly allocated cluster if any.
    fn cache_l2_cluster_alloc(
        &mut self,
        l1_index: usize,
        l2_addr_disk: u64,
    ) -> io::Result<Option<u64>> {
        let mut new_cluster: Option<u64> = None;
        if !self.l2_cache.contains_key(l1_index) {
            let l2_table = if l2_addr_disk == 0 {
                // Allocate a new cluster to store the L2 table
                let new_addr = self.get_new_cluster(None)?;
                new_cluster = Some(new_addr);
                self.l1_table[l1_index] = new_addr;
                VecCache::new(self.l2_entries as usize)
            } else {
                self.reject_invalid_cluster_offset(l2_addr_disk)?;
                VecCache::from_vec(self.raw_file.read_pointer_cluster(l2_addr_disk, None)?)
            };
            let l1_table = &self.l1_table;
            let raw_file = &mut self.raw_file;
            self.l2_cache.insert(l1_index, l2_table, |index, evicted| {
                raw_file.write_pointer_table_direct(l1_table[index], evicted.iter())
            })?;
        }
        Ok(new_cluster)
    }
''',
        '''    /// Populates the L2 cache for write operations and may allocate a new
    /// L2 table, establishing its refcount ownership before L1 can reference it.
    fn cache_l2_cluster_alloc(
        &mut self,
        l1_index: usize,
        l2_addr_disk: u64,
    ) -> io::Result<()> {
        if !self.l2_cache.contains_key(l1_index) {
            let l2_table = if l2_addr_disk == 0 {
                // Allocate and own the new L2 table before publishing it through L1.
                let new_addr = self.get_new_cluster(None)?;
                self.set_cluster_refcount_track_freed(new_addr, 1)?;
                self.l1_table[l1_index] = new_addr;
                VecCache::new(self.l2_entries as usize)
            } else {
                self.reject_invalid_cluster_offset(l2_addr_disk)?;
                VecCache::from_vec(self.raw_file.read_pointer_cluster(l2_addr_disk, None)?)
            };
            let l1_table = &self.l1_table;
            let raw_file = &mut self.raw_file;
            self.l2_cache.insert(l1_index, l2_table, |index, evicted| {
                raw_file.write_pointer_table_direct(l1_table[index], evicted.iter())
            })?;
        }
        Ok(())
    }
''',
        "cache_l2_cluster_alloc owner",
    ),
    (
        '''            // live L2 table (issue #8606). The cluster will be written when
            // the cache is flushed.
            let new_addr = self.get_new_cluster(None)?;
            set_refcounts.push((new_addr, 1));

            // Free the previously used cluster if one exists. Modified tables are always
''',
        '''            // live L2 table (issue #8606). The cluster will be written when
            // the cache is flushed.
            let new_addr = self.get_new_cluster(None)?;
            self.set_cluster_refcount_track_freed(new_addr, 1)?;

            // Free the previously used cluster if one exists. Modified tables are always
''',
        "relocated L2 owner",
    ),
    (
        '''        if l2_addr_disk == 0 {
            if zero_marker {
                if let Some(new_addr) = self.cache_l2_cluster_alloc(l1_index, l2_addr_disk)? {
                    self.set_cluster_refcount_track_freed(new_addr, 1)?;
                }
                self.l2_cache.get_mut(l1_index).unwrap()[l2_index] = dealloc_entry;
            }
            return Ok(None);
        }
''',
        '''        if l2_addr_disk == 0 {
            if zero_marker {
                self.cache_l2_cluster_alloc(l1_index, l2_addr_disk)?;
                self.l2_cache.get_mut(l1_index).unwrap()[l2_index] = dealloc_entry;
            }
            return Ok(None);
        }
''',
        "zero-marker fresh-L2 caller",
    ),
]

for old, new, label in replacements:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected exactly one {label} in {path}, found {count}")
    text = text.replace(old, new, 1)

cleanup_replacements = [
    (
        "        let mut set_refcounts = Vec::new();",
        "        let mut deferred_unrefs = Vec::new();",
        "map_write deferred-unref declaration",
        1,
    ),
    (
        "&mut set_refcounts",
        "&mut deferred_unrefs",
        "map_write deferred-unref calls",
        2,
    ),
    (
        '''        // Apply deferred refcount updates
        for (addr, refcount) in set_refcounts {
            self.set_cluster_refcount_track_freed(addr, refcount)?;
        }
''',
        '''        // Apply deferred L2 releases
        for addr in deferred_unrefs {
            self.set_cluster_refcount_track_freed(addr, 0)?;
        }
''',
        "release-only application loop",
        1,
    ),
    (
        "        set_refcounts: &mut Vec<(u64, u64)>,",
        "        deferred_unrefs: &mut Vec<u64>,",
        "update_cluster_addr release-only parameter",
        1,
    ),
    (
        "                set_refcounts.push((addr, 0));",
        "                deferred_unrefs.push(addr);",
        "old-L2 deferred release",
        1,
    ),
    (
        "        let mut deferred = Vec::new();",
        "        let mut deferred_unrefs = Vec::new();",
        "relocation regression deferred declaration",
        1,
    ),
    (
        "            .update_cluster_addr(0, 1, data_cluster, &mut deferred)",
        "            .update_cluster_addr(0, 1, data_cluster, &mut deferred_unrefs)",
        "relocation regression deferred call",
        1,
    ),
    (
        "        drop(deferred);",
        "        assert_eq!(deferred_unrefs, vec![old_l2]);\n        drop(deferred_unrefs);",
        "relocation regression release-only assertion",
        1,
    ),
]

for old, new, label, expected in cleanup_replacements:
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"expected {expected} {label} occurrences in {path}, found {count}")
    text = text.replace(old, new)

path.write_text(text)
