#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/formats/qcow/metadata.rs")
text = path.read_text()
marker = "self.set_cluster_refcount_track_freed(new_addr, 1)?;\n                self.l1_table[l1_index] = new_addr;"
if marker in text:
    raise SystemExit(f"candidate marker already present in {path}")

old_call = '''        let mut set_refcounts = Vec::new();

        if let Some(new_addr) = self.cache_l2_cluster_alloc(l1_index, l2_addr_disk)? {
            set_refcounts.push((new_addr, 1));
        }
'''
new_call = '''        let mut set_refcounts = Vec::new();

        self.cache_l2_cluster_alloc(l1_index, l2_addr_disk)?;
'''

old_fn = '''    fn cache_l2_cluster_alloc(
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
'''
new_fn = '''    fn cache_l2_cluster_alloc(
        &mut self,
        l1_index: usize,
        l2_addr_disk: u64,
    ) -> io::Result<()> {
        if !self.l2_cache.contains_key(l1_index) {
            let l2_table = if l2_addr_disk == 0 {
                // Commit ownership of the new metadata cluster before L1 can
                // point at it. If the refcount update fails, leave L1 unchanged.
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
'''

if text.count(old_call) != 1:
    raise SystemExit(f"expected exactly one deferred fresh-L2 caller block in {path}")
text = text.replace(old_call, new_call, 1)
if text.count(old_fn) != 1:
    raise SystemExit(f"expected exactly one cache_l2_cluster_alloc owner in {path}")
text = text.replace(old_fn, new_fn, 1)
path.write_text(text)
