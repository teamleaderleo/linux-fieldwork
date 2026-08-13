#!/usr/bin/env python3
from pathlib import Path

path = Path("pci/src/vfio.rs")
text = path.read_text()
marker = "if size > len - offset_from_start"
if marker in text:
    raise SystemExit(f"candidate marker already present in {path}")

needle = '''                assert!(
                    size <= len - offset_from_start,
'''
if text.count(needle) != 1:
    raise SystemExit("unexpected sparse user-region size assertion count")
start = text.index(needle)
end = text.index("                // SAFETY:", start)
replacement = '''                if size > len - offset_from_start {
                    continue;
                }
'''
path.write_text(text[:start] + replacement + text[end:])
