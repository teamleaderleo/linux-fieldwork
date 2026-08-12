#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/formats/qcow/refcount.rs")
text = path.read_text()

wrapper = '''    pub(super) fn set_cluster_refcount(
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

'''
if wrapper not in text:
    raise SystemExit("RefCount compatibility wrapper anchor missing")
text = text.replace(wrapper, "    #[cfg(test)]\n" + wrapper, 1)

needle = "if let Some(undo) = undo.as_deref_mut() {"
if text.count(needle) != 2:
    raise SystemExit(f"expected two needless as_deref_mut sites, found {text.count(needle)}")
text = text.replace(needle, "if let Some(undo) = undo.as_mut() {")

path.write_text(text)
