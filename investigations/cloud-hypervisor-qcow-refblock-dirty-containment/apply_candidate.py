#!/usr/bin/env python3
from pathlib import Path

metadata = Path("block/src/formats/qcow/metadata.rs")
parser = Path("block/src/formats/qcow/parser.rs")

m = metadata.read_text()
p = parser.read_text()

field_old = "    pub(crate) unref_clusters: Vec<u64>,\n"
field_new = field_old + "    pub(crate) refcount_update_failed: bool,\n"
if field_old not in m:
    raise SystemExit("QcowState unref field anchor missing")
m = m.replace(field_old, field_new, 1)

shutdown_old = '''        let _ = inner.sync_caches();
        let QcowState {
            ref mut header,
            ref mut raw_file,
            ..
        } = *inner;
        if raw_file.file().is_writable() {
            let _ = header.set_dirty_bit(raw_file.file_mut(), false);
        }
'''
shutdown_new = '''        let _ = inner.sync_caches();
        let refcount_update_failed = inner.refcount_update_failed;
        let QcowState {
            ref mut header,
            ref mut raw_file,
            ..
        } = *inner;
        if raw_file.file().is_writable() && !refcount_update_failed {
            let _ = header.set_dirty_bit(raw_file.file_mut(), false);
        }
'''
if shutdown_old not in m:
    raise SystemExit("shutdown anchor missing")
m = m.replace(shutdown_old, shutdown_new, 1)

track_old = '''    fn set_cluster_refcount_track_freed(&mut self, address: u64, refcount: u64) -> io::Result<()> {
        let mut newly_unref = self.set_cluster_refcount(address, refcount)?;
        self.unref_clusters.append(&mut newly_unref);
        Ok(())
    }
'''
track_new = '''    fn set_cluster_refcount_track_freed(&mut self, address: u64, refcount: u64) -> io::Result<()> {
        match self.set_cluster_refcount(address, refcount) {
            Ok(mut newly_unref) => {
                self.unref_clusters.append(&mut newly_unref);
                Ok(())
            }
            Err(e) => {
                self.refcount_update_failed = true;
                Err(e)
            }
        }
    }
'''
if track_old not in m:
    raise SystemExit("tracked refcount anchor missing")
m = m.replace(track_old, track_new, 1)

init_old = '''        refcounts,
        avail_clusters,
        unref_clusters: Vec::new(),
    };
'''
init_new = '''        refcounts,
        avail_clusters,
        unref_clusters: Vec::new(),
        refcount_update_failed: false,
    };
'''
if init_old not in p:
    raise SystemExit("parser QcowState init anchor missing")
p = p.replace(init_old, init_new, 1)

metadata.write_text(m)
parser.write_text(p)
