#!/usr/bin/env python3
from pathlib import Path

vec_cache = Path("block/src/formats/qcow/vec_cache.rs")
refcount = Path("block/src/formats/qcow/refcount.rs")
metadata = Path("block/src/formats/qcow/metadata.rs")

v = vec_cache.read_text()
r = refcount.read_text()
m = metadata.read_text()

old_insert = '''    // Check if the refblock cache is full and we need to evict.\n    pub(super) fn insert<F>(&mut self, index: usize, block: T, write_callback: F) -> io::Result<()>\n    where\n        F: FnOnce(usize, T) -> io::Result<()>,\n    {\n        if self.map.len() == self.capacity {\n            // TODO(dgreid) - smarter eviction strategy.\n            let to_evict = *self.map.iter().next().unwrap().0;\n            if let Some(evicted) = self.map.remove(&to_evict)\n                && evicted.dirty()\n            {\n                write_callback(to_evict, evicted)?;\n            }\n        }\n        self.map.insert(index, block);\n        Ok(())\n    }\n'''
new_insert = '''    // Check if the refblock cache is full and we need to evict.\n    pub(super) fn insert<F>(&mut self, index: usize, block: T, write_callback: F) -> io::Result<()>\n    where\n        F: FnOnce(usize, &T) -> io::Result<()>,\n    {\n        if self.map.len() == self.capacity {\n            // TODO(dgreid) - smarter eviction strategy.\n            let to_evict = *self.map.iter().next().unwrap().0;\n            if let Some(evicted) = self.map.get(&to_evict)\n                && evicted.dirty()\n            {\n                // Keep the dirty victim resident until its write succeeds so\n                // an I/O error leaves a retryable in-memory copy.\n                write_callback(to_evict, evicted)?;\n            }\n            self.map.remove(&to_evict);\n        }\n        self.map.insert(index, block);\n        Ok(())\n    }\n'''
if v.count(old_insert) != 1:
    raise SystemExit(f"expected one CacheMap::insert body, found {v.count(old_insert)}")
v = v.replace(old_insert, new_insert, 1)

unit_anchor = '''        assert!(cache.contains_key(3));\n    }\n}\n'''
unit_new = '''        assert!(cache.contains_key(3));\n    }\n\n    #[test]\n    fn failed_eviction_keeps_dirty_victim() {\n        let mut cache = CacheMap::<NumCache>::new(1);\n        cache.insert(0, NumCache(()), |_index, _| Ok(())).unwrap();\n\n        let err = cache\n            .insert(1, NumCache(()), |_index, _| {\n                Err(io::Error::other("injected eviction write failure"))\n            })\n            .expect_err("dirty eviction callback must fail");\n        assert_eq!(err.kind(), io::ErrorKind::Other);\n        assert!(cache.contains_key(0));\n        assert!(!cache.contains_key(1));\n    }\n}\n'''
if v.count(unit_anchor) != 1:
    raise SystemExit(f"expected one vec_cache unit-test anchor, found {v.count(unit_anchor)}")
v = v.replace(unit_anchor, unit_new, 1)

ref_old = '''            if let Some((addr, table)) = new_cluster.take() {\n                self.ref_table[table_index] = addr;\n                let ref_table = &self.ref_table;\n                self.refblock_cache\n                    .insert(table_index, table, |index, evicted| {\n                        raw_file.write_refcount_block(ref_table[index], evicted.get_values())\n                    })\n                    .map_err(Error::EvictingRefCounts)?;\n            } else {\n'''
ref_new = '''            if let Some((addr, table)) = new_cluster.take() {\n                let ref_table = &self.ref_table;\n                self.refblock_cache\n                    .insert(table_index, table, |index, evicted| {\n                        raw_file.write_refcount_block(ref_table[index], evicted.get_values())\n                    })\n                    .map_err(Error::EvictingRefCounts)?;\n                // Cache insertion can evict dirty metadata and perform I/O.\n                // Publish the new refblock pointer only after that succeeds.\n                self.ref_table[table_index] = addr;\n            } else {\n'''
if r.count(ref_old) != 1:
    raise SystemExit(f"expected one refcount new-block insertion, found {r.count(ref_old)}")
r = r.replace(ref_old, ref_new, 1)

meta_old = '''            let l2_table = if l2_addr_disk == 0 {\n                // Allocate a new cluster to store the L2 table\n                let new_addr = self.get_new_cluster(None)?;\n                new_cluster = Some(new_addr);\n                self.l1_table[l1_index] = new_addr;\n                VecCache::new(self.l2_entries as usize)\n            } else {\n                self.reject_invalid_cluster_offset(l2_addr_disk)?;\n                VecCache::from_vec(self.raw_file.read_pointer_cluster(l2_addr_disk, None)?)\n            };\n            let l1_table = &self.l1_table;\n            let raw_file = &mut self.raw_file;\n            self.l2_cache.insert(l1_index, l2_table, |index, evicted| {\n                raw_file.write_pointer_table_direct(l1_table[index], evicted.iter())\n            })?;\n'''
meta_new = '''            let l2_table = if l2_addr_disk == 0 {\n                // Allocate a new cluster to store the L2 table. Publication\n                // through L1 happens only after cache insertion succeeds.\n                let new_addr = self.get_new_cluster(None)?;\n                new_cluster = Some(new_addr);\n                VecCache::new(self.l2_entries as usize)\n            } else {\n                self.reject_invalid_cluster_offset(l2_addr_disk)?;\n                VecCache::from_vec(self.raw_file.read_pointer_cluster(l2_addr_disk, None)?)\n            };\n            let l1_table = &self.l1_table;\n            let raw_file = &mut self.raw_file;\n            self.l2_cache.insert(l1_index, l2_table, |index, evicted| {\n                raw_file.write_pointer_table_direct(l1_table[index], evicted.iter())\n            })?;\n            if let Some(new_addr) = new_cluster {\n                self.l1_table[l1_index] = new_addr;\n            }\n'''
if m.count(meta_old) != 1:
    raise SystemExit(f"expected one fresh L2 cache insertion body, found {m.count(meta_old)}")
m = m.replace(meta_old, meta_new, 1)

vec_cache.write_text(v)
refcount.write_text(r)
metadata.write_text(m)
