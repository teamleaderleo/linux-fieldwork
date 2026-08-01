# Source map

## Upstream and package source identity

| Item | Path or carrier | Exact revision | Role |
| --- | --- | --- | --- |
| Ownership implementation | `util-linux/lib/path.c:ul_path_cpuparse()` | tag `v2.41`, blob `42a33ffc53752ba5e00aed2396ca9a4fc876c1ef` | first ownership defect |
| Initial CPU masks | `sys-utils/lscpu-cputype.c` | tag `v2.41` | reads `possible`, `present`, and `online` through cpuset helpers |
| NUMA maps | `sys-utils/lscpu-cputype.c:lscpu_read_numas()` | tag `v2.41` | fills `cxt->nodemaps[]` through `ul_path_readf_cpuset()` |
| Final cleanup | `sys-utils/lscpu.c:lscpu_free_context()` | tag `v2.41`, blob `ffec37206587aff100830b6717a13d82c9ead686` | frees present, online, then nodemaps |
| Canonical fix | util-linux commit | `4581ede384f22983d6155768635ce43cb5304cb0` | free then clear output |
| Stable backport | util-linux commit | `3cd5f1dd69495864f3046cdbcefa104786fe5a27` | cherry-pick identity |
| Debian source | `util-linux 2.41-5` | checksums in `README.md` | remaining maintained affected package |
| Effective Debian owner | `lib/path.c` | SHA-256 `f934339cf7aba38ae6197e5b5ad3b6a9e7e5fb483ed3f807d45971968d3c7cda` | quilt-applied baseline still affected |

## Linux Fieldwork carriers

| Carrier | Exact identity | Role |
| --- | --- | --- |
| Issue #234 | closed fix map | canonical source archaeology |
| PR #239 | head `7bc904f71059299491d91dba7b7ef6a03857305a` | superseded draft carrier |
| PR #387 | merge `4a2196a705c06f5604879f655d465a4ac6fcb198` | canonical retained patch/model evidence |
| Issue #397 unit 23 | current initiative | package adoption decision |
| PR #404 | branch `upstream/unit-23-util-linux-lscpu-cpuset` | internal package execution carrier |

## Packet code and evidence

| File | Purpose |
| --- | --- |
| `patches/0001-clear-cpuset-output-after-error.patch` | canonical patch with upstream authorship |
| `scripts/reproduce-trixie-lscpu-cpuset.sh` | deterministic actual-binary text/JSON matrix |
| `.github/workflows/unit-23-util-linux-lscpu.yml` | exact source, patch, build, and binary execution gate |
| `artifacts/2026-08-01-focused-regression.txt` | retained model/patch matrix |
| `artifacts/2026-08-01-trixie-installed-binary-reproduction.txt` | installed-package baseline receipt |
| `artifacts/2026-08-01-trixie-minimal-sysroot-reproduction.txt` | minimal fixture, losing control, and allocator-size sweep |
| `artifacts/2026-08-01-ci-run-30690487287.txt` | exact Debian source and package-build receipt |

## Operation ownership map

| Operation | Affected owner | Correct owner state | Evidence |
| --- | --- | --- | --- |
| allocate and publish cpuset | `ul_path_cpuparse()` | caller slot contains allocation | v2.41 source |
| reject malformed list | parser helper | nonzero status | public reports and fixture |
| free failed allocation | `ul_path_cpuparse()` | allocation released | v2.41 source |
| publish post-free state | affected helper leaves stale address | corrected helper writes `NULL` | commit `4581ede...` |
| later ordinary cleanup | `lscpu_free_context()` | NULL-safe free | v2.41 cleanup order |

## Patch and branch links

- Linux Fieldwork branch: `upstream/unit-23-util-linux-lscpu-cpuset`
- Internal PR: #404
- Controlled util-linux fork: `teamleaderleo/util-linux`, unused because upstream already owns the fix
- Debian packaging fork: `NEEDS FORK` only if Salsa delivery is selected
- Retained patch: `patches/0001-clear-cpuset-output-after-error.patch`
- Exact application: `patch --batch --forward --fuzz=0 -p1 -i PATCH`

## Overlap and current package state

Checked 2026-08-01:

- upstream owns the source correction;
- current stable branches contain it;
- Debian testing and unstable carry newer fixed upstream releases;
- trixie stable remains `2.41-5`;
- the fully unpacked Debian tree lacks an equivalent correction;
- no util-linux upload appears in the current trixie proposed-updates queue;
- no matching Debian BTS report was found in the overlap search.

## Files deliberately left alone

- final `lscpu` cleanup: changing the last free would treat the symptom and preserve stale ownership;
- parser policy: malformed input remains an error;
- successful cpuset parsing and output formatting;
- cgroup mount discovery: absent from the canonical carrier mechanism;
- upstream util-linux source branches: already fixed.
