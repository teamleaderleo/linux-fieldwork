#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/formats/qcow/metadata.rs")
text = path.read_text()
old = '''    pub(super) fn shutdown(&self) {
        let mut inner = self.inner.write().unwrap();
        let _ = inner.sync_caches();
        let QcowState {
            ref mut header,
            ref mut raw_file,
            ..
        } = *inner;
        if raw_file.file().is_writable() {
            let _ = header.set_dirty_bit(raw_file.file_mut(), false);
        }
    }
'''
new = '''    pub(super) fn shutdown(&self) {
        let mut inner = self.inner.write().unwrap();
        if let Err(e) = inner.sync_caches() {
            log::warn!("Failed to synchronize QCOW metadata during shutdown: {e}");
            return;
        }
        let QcowState {
            ref mut header,
            ref mut raw_file,
            ..
        } = *inner;
        if raw_file.file().is_writable() {
            let _ = header.set_dirty_bit(raw_file.file_mut(), false);
        }
    }
'''
if text.count(old) != 1:
    raise SystemExit(f"expected exactly one QcowMetadata::shutdown owner in {path}, found {text.count(old)}")
path.write_text(text.replace(old, new, 1))
