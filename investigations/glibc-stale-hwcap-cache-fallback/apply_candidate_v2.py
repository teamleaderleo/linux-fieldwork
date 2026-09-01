#!/usr/bin/env python3
"""Apply and tighten the first stale-cache candidate transform.

This wrapper keeps the first transform as retained design history, then fixes
four review/build findings before any candidate is compiled:

* only byte-exact cache keys are eligible, so fallback cannot widen the
  numeric-name alias behavior tracked separately by Linux Fieldwork #502;
* the generated range walk has an explicit signed bound matching its `int`
  cursor;
* successful pathname ownership is transferred without inserting an interior
  NULL into the candidate vector, so later copied candidates are still freed;
* the new candidate lookup sees declarations for the existing static cache
  reload helpers before it calls them.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys


def replace_exact(path: pathlib.Path, old: str, new: str, count: int = 1) -> None:
    text = path.read_text()
    observed = text.count(old)
    if observed != count:
        raise SystemExit(
            f"{path}: expected {count} occurrence(s) of reviewed block, found {observed}"
        )
    path.write_text(text.replace(old, new, count))


def exact_key_guard() -> str:
    return """      const struct file_entry *key_entry\n        = _dl_cache_file_entry (libs, entry_size, index);\n      if (!_dl_cache_verify_ptr (key_entry->key, string_table_size)\n          || strcmp (name, string_table + key_entry->key) != 0)\n        continue;\n\n"""


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} GLIBC_SOURCE_ROOT")

    root = pathlib.Path(sys.argv[1]).resolve()
    transform = pathlib.Path(__file__).with_name("apply_candidate.py")
    subprocess.run([sys.executable, str(transform), str(root)], check=True)

    dl_cache = root / "elf/dl-cache.c"
    dl_load = root / "elf/dl-load.c"

    replace_exact(
        dl_cache,
        "\nstruct cache_candidate_copy\n",
        """
+/* These helpers are defined later in this file.  The candidate lookup is
+   inserted before their definitions, so retain their existing static linkage
+   and make the call order explicit.  */
+static bool _dl_check_ldsocache_needs_loading (void);
+static void _dl_maybe_load_ldsocache (void);
+
+struct cache_candidate_copy
+""".replace("+", ""),
    )

    replace_exact(
        dl_cache,
        "while (end + 1 < nlibs)",
        "while (end + 1 < (int) nlibs)",
    )

    count_loop = """  for (uint32_t index = first; index <= last; ++index)\n    {\n      const char *path;\n      bool named;\n      uint32_t priority;\n      if (!cache_candidate_info (string_table, string_table_size, libs,\n                                 entry_size, index, &path, &named, &priority))\n        continue;\n"""
    count_loop_exact = (
        "  for (uint32_t index = first; index <= last; ++index)\n    {\n"
        + exact_key_guard()
        + """      const char *path;\n      bool named;\n      uint32_t priority;\n      if (!cache_candidate_info (string_table, string_table_size, libs,\n                                 entry_size, index, &path, &named, &priority))\n        continue;\n"""
    )
    replace_exact(dl_cache, count_loop, count_loop_exact)

    copy_loop = """  for (uint32_t index = first; index <= last; ++index)\n    {\n      const char *path;\n      bool named;\n      uint32_t priority;\n      if (!cache_candidate_info (string_table, string_table_size, libs,\n                                 entry_size, index, &path, &named, &priority)\n          || !named)\n        continue;\n"""
    copy_loop_exact = (
        "  for (uint32_t index = first; index <= last; ++index)\n    {\n"
        + exact_key_guard()
        + """      const char *path;\n      bool named;\n      uint32_t priority;\n      if (!cache_candidate_info (string_table, string_table_size, libs,\n                                 entry_size, index, &path, &named, &priority)\n          || !named)\n        continue;\n"""
    )
    replace_exact(dl_cache, copy_loop, copy_loop_exact)

    old_transfer = """\t      for (size_t index = 0; cached[index] != NULL; ++index)\n\t\t{\n\t\t  bool use_candidate = true;\n"""
    new_transfer = """\t      char *selected = NULL;\n\t      for (size_t index = 0; cached[index] != NULL; ++index)\n\t\t{\n\t\t  bool use_candidate = true;\n"""
    replace_exact(dl_load, old_transfer, new_transfer)

    replace_exact(
        dl_load,
        """\t\t      if (__glibc_likely (fd != -1))\n\t\t\t{\n\t\t\t  realname = cached[index];\n\t\t\t  cached[index] = NULL;\n\t\t\t  break;\n\t\t\t}\n""",
        """\t\t      if (__glibc_likely (fd != -1))\n\t\t\t{\n\t\t\t  selected = cached[index];\n\t\t\t  break;\n\t\t\t}\n""",
    )

    replace_exact(
        dl_load,
        """\t      for (size_t index = 0; cached[index] != NULL; ++index)\n\t\tfree (cached[index]);\n\t      free (cached);\n""",
        """\t      for (size_t index = 0; cached[index] != NULL; ++index)\n\t\tif (cached[index] != selected)\n\t\t  free (cached[index]);\n\t      free (cached);\n\t      if (selected != NULL)\n\t\trealname = selected;\n""",
    )

    print("classification\tcandidate_v2_transform_applied")
    print("exact_cache_key_filter\ttrue")
    print("selected_path_ownership\tbalanced")


if __name__ == "__main__":
    main()
