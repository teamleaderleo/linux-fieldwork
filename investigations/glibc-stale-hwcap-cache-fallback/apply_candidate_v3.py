#!/usr/bin/env python3
"""Apply the stale-HWCAP candidate without changing cache-key identity policy.

v2 retained several necessary build/lifetime repairs but also inserted exact-byte
name guards. Those guards belong to the separate numeric-name identity lane.
This wrapper preserves the v2 mechanical fixes and removes only those two
identity-policy guards before the candidate is built.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} GLIBC_SOURCE_ROOT")

    root = pathlib.Path(sys.argv[1]).resolve()
    v2 = pathlib.Path(__file__).with_name("apply_candidate_v2.py")
    subprocess.run([sys.executable, str(v2), str(root)], check=True)

    dl_cache = root / "elf/dl-cache.c"
    text = dl_cache.read_text()
    guard = """      const struct file_entry *key_entry
        = _dl_cache_file_entry (libs, entry_size, index);
      if (!_dl_cache_verify_ptr (key_entry->key, string_table_size)
          || strcmp (name, string_table + key_entry->key) != 0)
        continue;

"""
    observed = text.count(guard)
    if observed != 2:
        raise SystemExit(
            f"expected two v2 exact-key guards to remove, found {observed}"
        )
    dl_cache.write_text(text.replace(guard, ""))

    final = dl_cache.read_text()
    forbidden = "strcmp (name, string_table + key_entry->key)"
    if forbidden in final:
        raise SystemExit("exact-byte cache-key policy still present after v3 repair")

    print("classification\tcandidate_v3_transform_applied")
    print("exact_cache_key_filter\tfalse")
    print("identity_policy_owner\tseparate_fieldwork_502")
    print("selected_path_ownership\tbalanced")


if __name__ == "__main__":
    main()
