# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Upstream base | `josch/mmdebstrap` `main` `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Candidate head | local composed source SHA-256 `adb1a8353bcd676a8acdba4318b198539820b890e2a96016b9909d382942e42e` |
| Linux Fieldwork branch | `upstream/unit-15-tarfilter-transform-metadata` |
| Linux Fieldwork packet base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Platform/distribution | execution container; distro package identity not recorded |
| Architecture | `x86_64` execution environment |
| Kernel | container host kernel; exact release not retained in first run |
| Shell/runtime | POSIX shell wrapper; Python 3.13.5 |
| Privilege boundary | unprivileged focused archive operations |
| Important tool versions | GNU tar 1.35; GNU patch 2.8; Git available |

## Source and patch identity

```text
baseline Git blob:
  ad776167a8473d5d15dbe22e850f4f6db35cf278
baseline SHA-256:
  442b056aeb414aef0e33d59b6235623ca4d6072c62272508281d126cb3f3d957
historical PR #68 patch blob:
  1703984aa0c030e5131618a3541ee85bfd68ec65
historical PR #102 patch blob:
  81828a468854e7ec9ef4cda9626b9c57314afba3
regenerated patch SHA-256:
  4d8cb2f180cb7798a15195c2dcfac164b409f68a18c69d507cfc624d4725703c
candidate source SHA-256:
  adb1a8353bcd676a8acdba4318b198539820b890e2a96016b9909d382942e42e
```

## Baseline reproducer

### Command

The packet wrapper materializes the exact imported source and runs all controls:

```sh
upstream-packets/units/15-tarfilter-transform-metadata/scripts/materialize_and_run.sh
```

The core baseline replacement control is equivalent to:

```sh
python3 upstream/mmdebstrap/tarfilter --transform='s/a/b/' < a-a.tar > baseline.tar
python3 upstream/mmdebstrap/tarfilter --transform='s/a/b/g' < a-a.tar > /dev/null
```

### Expected distinguishing result

- ordinary replacement changes both matches under Python's default `re.sub()` behavior;
- explicit `g` is rejected;
- default transform leaves hard-link and symlink target text prefixed;
- strip leaves a stale long PAX path;
- the PR #68 predecessor rejects a numeric selector.

### Observed result

- status: baseline ordinary command `0`; `g` command nonzero;
- archive name: `b/b` for `s/a/b/`;
- links: `hard -> prefix/target`, `sym -> prefix/target` after member rename;
- PAX: prefixed 120-byte path remains visible after strip;
- predecessor: numeric `2` rejected;
- receipt: `artifacts/matrix-result.json`.

## Candidate reproducer

### Patch application

```sh
patch --fuzz=0 -p1 -d /path/to/mmdebstrap \
  -i upstream-packets/units/15-tarfilter-transform-metadata/patches/0001-tarfilter-transform-metadata.patch
```

Observed: status `0`, no fuzz, no offsets, and output byte-identical to the composed source. See `artifacts/APPLICATION.txt`.

### Focused matrix

```sh
upstream-packets/units/15-tarfilter-transform-metadata/scripts/materialize_and_run.sh \
  > /tmp/unit15-matrix.json
```

### Expected result

Candidate output matches GNU tar for the retained replacement, scope, PAX, and numeric matrix; extraction and inode checks pass; unsupported non-ASCII selectors fail.

### Observed result

- status: `0`;
- result JSON: `status: PASS`;
- candidate SHA-256: `adb1a8353bcd676a8acdba4318b198539820b890e2a96016b9909d382942e42e`;
- GNU tar: 1.35;
- Python: 3.13.5;
- wrapper output SHA-256: `325db677bba5b435c45de2f09f89b2f52fd88e62137660094457623adb1e8106`.

## Matrix

| Case | Baseline or predecessor | Candidate | Exact gate | Result identity |
| --- | --- | --- | --- | --- |
| Ordinary replacement | `a/a -> b/b` | `a/a -> b/a` | wrapper, `s/a/b/` | matches GNU tar |
| Global replacement | `g` rejected | `a/a -> b/b` | wrapper, `s/a/b/g` | matches GNU tar |
| Whole-match `&` | unsupported semantics | `[a]/a` | wrapper, `s/a/[&]/` | matches GNU tar |
| Escaped delimiter | narrow parser boundary | `x#y/a` | wrapper, `s#a#x\#y#` | matches GNU tar |
| Default target scopes | link targets stale | default `rsh` | wrapper, default expression | matches GNU tar |
| Uppercase `S` | no scope model | symlink text preserved | wrapper, `S` expression | matches GNU tar |
| Hard-link extraction | transformed target unavailable | extraction succeeds; shared inode | wrapper extraction assertion | pass |
| Long PAX strip | stale prefixed `path`/`linkpath` | regenerated leaf values | wrapper, 120-byte leaf | pass |
| Numeric `2` | PR #68 predecessor rejects | second match only | wrapper | matches GNU tar |
| Numeric plus global | predecessor rejects | start at selected match | wrapper, `2g` and `g2` | matches GNU tar |
| Zero | predecessor rejects | ordinary/global default | wrapper, `0` and `0g` | matches GNU tar |
| Repeated decimal runs | predecessor rejects | last run selected | wrapper, `2g3` | matches GNU tar |
| Non-ASCII numerals | rejected | rejected | wrapper | matches GNU tar rejection |
| Cleanup | no retained temp root expected | no `unit15-matrix.*` root remains | wrapper trap | pass |
| Immediate rerun | n/a | identical JSON | three direct runs plus wrapper run | SHA-256 identical |

## Upstream-native gates

| Gate | Exact command | Result | Candidate head |
| --- | --- | --- | --- |
| Focused upstream tarfilter test | unresolved upstream-native entry point | NOT RUN | local SHA-256 `adb1a8353bcd676a8acdba4318b198539820b890e2a96016b9909d382942e42e` |
| Relevant integration tests | current checkout required | NOT RUN | local SHA-256 `adb1a8353bcd676a8acdba4318b198539820b890e2a96016b9909d382942e42e` |
| Formatting/lint | current checkout required | NOT RUN | local SHA-256 `adb1a8353bcd676a8acdba4318b198539820b890e2a96016b9909d382942e42e` |
| Build/package test | current checkout required | NOT RUN | local SHA-256 `adb1a8353bcd676a8acdba4318b198539820b890e2a96016b9909d382942e42e` |

## Linux Fieldwork retained gates

| Gate or fixture | Exact command/run | Result | Artifact/digest |
| --- | --- | --- | --- |
| Direct matrix run 1 | `python3 scripts/run_unit15_matrix.py` in materialized worktree | PASS | `artifacts/matrix-result.json`; SHA-256 `325db677bba5b435c45de2f09f89b2f52fd88e62137660094457623adb1e8106` |
| Immediate rerun | same command after cleanup | PASS, identical | retained hash in this file |
| Third direct rerun | same command in this continuation | PASS, identical | retained hash in this file |
| Packet wrapper gate | `scripts/materialize_and_run.sh` in synthetic checkout | PASS, identical | retained hash in this file |
| Clean patch application | GNU patch 2.8, `--fuzz=0` | PASS, byte-identical | `artifacts/APPLICATION.txt` |

Historical exact-head CI receipts retained from carriers:

- PR #56: `30535166174` success on `640f414cb18cf47b3e803856392c720414bea333`.
- PR #68: `30536181358` success on `1f8f16bf0841a720bdc1da727000c26a3ab13a09`.
- PR #102: `30543327305` success on `46f49d04639d6baf43243e5096175866c7e6a58e`; corrected code run `30543032983`; initial differential `30542362599`.

## Patch application and rebase

- base identity: imported blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`, matching the relevant inspected current-upstream source;
- historical application command: `git apply` PR #68 patch then PR #102 patch;
- historical result: both apply, with offsets recorded in `artifacts/APPLICATION.txt`;
- GNU patch historical result: PR #68 parser hunk rejected by patch 2.8;
- selected application command: GNU patch 2.8 with `--fuzz=0` on regenerated patch;
- selected result: clean, no offsets, byte-identical candidate;
- conflict resolution: none in regenerated patch;
- complete source diff reviewed: one file, 179 insertions, 23 deletions; semantic review recorded in `DEEP_DIVE.md`;
- active overlap searched: 2026-08-01; receipt in `artifacts/UPSTREAM_OVERLAP.md`.

## Cleanup and rerun

The direct Python matrix uses `TemporaryDirectory` for every archive case. The wrapper uses `mktemp -d` and a trap for EXIT, HUP, INT, and TERM. The recorded leftover scan is empty. Three direct executions and one wrapper execution produced byte-identical JSON.

No process, socket, mount, container, image, cache entry, package state, or source-tree modification remains. The packet intentionally retains the patch, scripts, JSON receipt, hashes, and prose records.

## Tests not run

- full current-upstream checkout tests;
- an upstream-native committed regression in the project's preferred form;
- Debian package build and autopkgtest;
- other GNU tar versions;
- other Python versions;
- BSD tar or other tar implementations;
- full unit 01 regex-dialect composition;
- persistent `flags=`, expression lists, case conversion, locale/collation, and malformed-expression parity.

## Failure classification

- Historical PR #48 malformed patch: patch packaging carrier.
- Historical stale default symlink expectation: test contract/product compatibility carrier.
- Historical PR #102 `str.isdigit()` issue: product parser over-acceptance.
- Historical reference diagnostic decode failure: evidence harness.
- GNU patch 2.8 rejection of the retained PR #68 parser hunk in this pass: patch-application portability of the retained carrier.
- No red result occurred for the regenerated candidate matrix.

## Final evidence statement

The executed matrix establishes that the regenerated candidate cleanly applies to the exact baseline and matches GNU tar 1.35 for the tested replacement language, default and `S` target scopes, hard-link extraction, long PAX path/linkpath regeneration, and numeric occurrence semantics. It also establishes deterministic cleanup and rerun behavior. The conclusion ends before full current-upstream checkout integration and upstream-native gates.
