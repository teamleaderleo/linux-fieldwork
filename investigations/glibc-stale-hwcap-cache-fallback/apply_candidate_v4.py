#!/usr/bin/env python3
"""Apply v3 and strengthen the native stale-cache fallback regression.

v4 changes no product code.  It extends the existing glibc HWCAP cache test so
native execution covers the complete intended fallback chain:

* stale preferred named HWCAP -> next named HWCAP;
* all named HWCAP entries stale -> cached baseline;
* every cached candidate stale -> ordinary search still runs and the load fails.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys


def replace_exact(path: pathlib.Path, old: str, new: str) -> None:
    text = path.read_text()
    observed = text.count(old)
    if observed != 1:
        raise SystemExit(
            f"{path}: expected one reviewed v3 test block, found {observed}"
        )
    path.write_text(text.replace(old, new, 1))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} GLIBC_SOURCE_ROOT")

    root = pathlib.Path(sys.argv[1]).resolve()
    v3 = pathlib.Path(__file__).with_name("apply_candidate_v3.py")
    subprocess.run([sys.executable, str(v3), str(root)], check=True)

    test = root / "elf/tst-glibc-hwcaps-prepend-cache.c"
    old = """  /* Remove the preferred override without running ldconfig.  Cache
     lookup should continue with the next compatible cached candidate.  */
  xunlink (\"/glibc-test/lib/glibc-hwcaps/prepend3/\" SONAME);
  {
    void *handle = xdlopen (SONAME, RTLD_NOW);
    int (*marker1) (void) = xdlsym (handle, \"marker1\");
    TEST_COMPARE (marker1 (), 2);
    xdlclose (handle);
  }
  run_ldconfig ();
  {
    /* After running ldconfig, the second implementation is available
       once more.  */
    void *handle = xdlopen (SONAME, RTLD_NOW);
    int (*marker1) (void) = xdlsym (handle, \"marker1\");
    TEST_COMPARE (marker1 (), 2);
    xdlclose (handle);
  }
"""
    new = """  /* Remove the preferred override without running ldconfig.  Cache
     lookup should continue with the next compatible named HWCAP candidate.  */
  xunlink (\"/glibc-test/lib/glibc-hwcaps/prepend3/\" SONAME);
  {
    void *handle = xdlopen (SONAME, RTLD_NOW);
    int (*marker1) (void) = xdlsym (handle, \"marker1\");
    TEST_COMPARE (marker1 (), 2);
    xdlclose (handle);
  }

  /* Leave both named HWCAP cache entries stale.  The compatible baseline
     entry recorded in the same cache must remain a fallback candidate.  */
  xunlink (\"/glibc-test/lib/glibc-hwcaps/prepend2/\" SONAME);
  {
    void *handle = xdlopen (SONAME, RTLD_NOW);
    int (*marker1) (void) = xdlsym (handle, \"marker1\");
    TEST_COMPARE (marker1 (), 1);
    xdlclose (handle);
  }

  /* Finally make every cached pathname stale.  Exhausting the copied cache
     candidates must preserve the existing ordinary-search fallback.  There is
     no copy on that search path in this fixture, so the load still fails.  */
  xunlink (\"/glibc-test/lib/\" SONAME);
  TEST_VERIFY (dlopen (SONAME, RTLD_NOW) == NULL);

  /* Leave the container cache consistent for diagnostics and cleanup.  */
  run_ldconfig ();
  TEST_VERIFY (dlopen (SONAME, RTLD_NOW) == NULL);
"""
    replace_exact(test, old, new)

    print("classification\tcandidate_v4_transform_applied")
    print("product_code\tunchanged_from_v3")
    print("native_fallback_chain\tnamed_to_named,named_to_baseline,all_cached_stale")


if __name__ == "__main__":
    main()
