#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/formats/qcow/metadata.rs")
text = path.read_text()
marker = "self.set_cluster_refcount_track_freed(new_addr, 1)?;\n                self.l1_table[l1_index] = new_addr;"
if marker in text:
    raise SystemExit(f"candidate marker already present in {path}")

old_map_write = '''        let mut set_refcounts = Vec::new();

        if let Some(new_addr) = self.cache_l2_cluster_alloc(l1_index, l2_addr_disk)? {
            set_refcounts.push((new_addr, 1));
        }
'''
new_map_write = '''        let mut set_refcounts = Vec::new();

        self.cache_l2_cluster_alloc(l1_index, l2_addr_disk)?;
'''

old_zero_marker = '''        if l2_addr_disk == 0 {
            if zero_marker {
                if let Some(new_addr) = self.cache_l2_cluster_alloc(l1_index, l2_addr_disk)? {
                    self.set_cluster_refcount_track_freed(new_addr, 1)?;
                }
                self.l2_cache.get_mut(l1_index).unwrap()[l2_index] = dealloc_entry;
            }
            return Ok(None);
        }
'''
new_zero_marker = '''        if l2_addr_disk == 0 {
            if zero_marker {
                self.cache_l2_cluster_alloc(l1_index, l2_addr_disk)?;
                self.l2_cache.get_mut(l1_index).unwrap()[l2_index] = dealloc_entry;
            }
            return Ok(None);
        }
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
new_fn = '''    fn cache_l2_cluster_alloc(&mut self, l1_index: usize, l2_addr_disk: u64) -> io::Result<()> {
        if !self.l2_cache.contains_key(l1_index) {
            let l2_table = if l2_addr_disk == 0 {
                // Establish ownership before publishing the new metadata cluster
                // through L1. If the refcount update fails, L1 stays unchanged.
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

for old, new, label in [
    (old_map_write, new_map_write, "map_write fresh-L2 caller"),
    (old_zero_marker, new_zero_marker, "zero-marker fresh-L2 caller"),
    (old_fn, new_fn, "cache_l2_cluster_alloc owner"),
]:
    if text.count(old) != 1:
        raise SystemExit(f"expected exactly one {label} in {path}, found {text.count(old)}")
    text = text.replace(old, new, 1)

path.write_text(text)
