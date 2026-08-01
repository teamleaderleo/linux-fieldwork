# Source map

## Upstream source identity

| Item | Repository path or URL | Exact revision | Notes |
| --- | --- | --- | --- |
| Affected implementation | `util-linux/util-linux:lib/path.c`, `ul_path_cpuparse()` | tag `v2.41`; blob `42a33ffc53752ba5e00aed2396ca9a4fc876c1ef` | error path frees `*set` without clearing it |
| Canonical correction | `util-linux/util-linux:lib/path.c` | `4581ede384f22983d6155768635ce43cb5304cb0` | adds braces and `*set = NULL` after `cpuset_free(*set)` |
| Stable cherry-pick | `util-linux/util-linux:lib/path.c` | `3cd5f1dd69495864f3046cdbcefa104786fe5a27` | same one-file correction; cherry-picked from `4581ede...` |
| Current master source | `util-linux/util-linux:lib/path.c` | head `fd82c4043fab942b889f478800118c66edfbc39f`; blob `90aac2058034143a7ccea5bf6f43f2831df492f0` | contains free-then-NULL |
| Current stable/v2.40 source | `util-linux/util-linux:lib/path.c` | head `160b7e47d4e6ba0fd15e66b4041bbdc67d2c457f`; blob `29b074a959b70ab21d4ff195649780e9062cbe02` | contains free-then-NULL |
| Current stable/v2.41 source | `util-linux/util-linux:lib/path.c` | head `2dacaf3eea391e3bbf48e7d3ecce02cafe045b6d`; blob `a828aea493c05c207331e4489e2f8da788bcc678` | contains free-then-NULL |
| Current stable/v2.42 source | `util-linux/util-linux:lib/path.c` | head `84796d917bcbad37aecfdadf36d71fee5b356efd`; blob `6ce8a10d2dd035432a4701e0f38c1120578028f0` | contains free-then-NULL |
| Original report | `https://github.com/util-linux/util-linux/issues/3641` | closed 2025-10-14 | maintainer identified `ul_path_cpuparse()`; reporter confirmed patch |
| Later report | `https://github.com/util-linux/util-linux/issues/4401` | open; checked 2026-08-01 | malformed `5,12-%`; maintainer states fix in stable/v2.{40,41,42}, with no expected v2.40.x release |
| Debian stable package | `https://packages.debian.org/trixie/util-linux` | `2.41-5` | still uses upstream 2.41 source |
| Debian stable patch series | `https://sources.debian.org/patches/util-linux/2.41-5/` | checked 2026-08-01 | searches for `cpuset`, `lib/path.c`, and `4581ede` returned no matches |
| Debian testing/unstable line | `https://packages.debian.org/en/util-linux` | forky `2.42.2-1`; sid `2.42.2-2` at check time | fixed through newer upstream release |

## Linux Fieldwork carriers

| Carrier | Exact head or merge | Role | Status |
| --- | --- | --- | --- |
| PR #387 | head `030eeca63da29c07984f7e752d2022317987d6d7`; merge `4a2196a705c06f5604879f655d465a4ac6fcb198` | canonical retained patch, fixture, model, and test carrier | canonical evidence |
| Issue #234 | closed completed | source and release fix map | canonical decision record |
| PR #239 | head `7bc904f71059299491d91dba7b7ef6a03857305a` | predecessor investigation carrier | superseded by PR #387 merge |
| Investigation README | `investigations/util-linux-lscpu-cpuset-double-free/README.md`, blob `9dd0e2a0bc2c1501e5bdc7f167cca38732a7b332` | source mechanism and adoption map | retained evidence |
| Unit 23 packet branch | base `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` | downstream destination verification | active hold packet |

## Candidate code

| File | Lines or symbols | Change | Owning commit or patch |
| --- | --- | --- | --- |
| `lib/path.c` | `ul_path_cpuparse()` `out:` path | wrap error cleanup in braces and set `*set = NULL` after free | `patches/0001-clear-cpuset-output-after-error.patch`; upstream `4581ede...` |
| Debian packaging metadata | version/changelog/series entry | pending exact destination and package version | `NEEDS PACKAGE CARRIER` |

## Candidate tests

| File | Test or fixture | Baseline failure | Candidate expectation |
| --- | --- | --- | --- |
| `tests/test_util_linux_lscpu_cpuset_double_free.py` | deterministic ownership matrix | duplicate logical cleanup, status 42 | output cleared; later cleanup harmless, status 0 |
| `investigations/.../fixtures/v2.41/lib/path.c` | exact minimal v2.41 error path | lacks NULL assignment | canonical patch applies with `--fuzz=0` |
| issue #4401 attachment `test.tar.gz` | package-level malformed sysfs fixture | affected 2.40.4/2.41 abort | rebuilt package exits without duplicate free | 

## Patch and branch links

- Linux Fieldwork branch: `upstream/unit-23-util-linux-lscpu-cpuset`
- Controlled upstream fork: `teamleaderleo/util-linux`
- Debian packaging fork: `NEEDS FORK`
- Candidate Debian branch: `NEEDS BRANCH`
- Compare or diff: `NEEDS PACKAGE CARRIER`
- Retained patch: `patches/0001-clear-cpuset-output-after-error.patch`
- Patch application command: `patch --batch --forward --fuzz=0 -p1 -i patches/0001-clear-cpuset-output-after-error.patch`

## Operation ownership map

| Operation | Owner before candidate | Owner after candidate | Evidence |
| --- | --- | --- | --- |
| allocate and publish cpuset | `ul_path_cpuparse()` writes allocation through caller output | unchanged | v2.41 source and ownership model |
| first error-path cleanup | `ul_path_cpuparse()` frees allocation but leaves stale output | `ul_path_cpuparse()` frees allocation and clears output | canonical patch `4581ede...` |
| later ordinary cleanup | `lscpu` frees retained pointer and can duplicate the first free | `lscpu` sees NULL; cleanup remains harmless | reporter Valgrind trace and deterministic model |
| source correction ownership | util-linux upstream | already complete upstream | current master/stable source checks |
| remaining package adoption | Debian trixie `util-linux 2.41-5` | proposed downstream backport | Debian package/version and patch-series checks |

## Overlap and current upstream state

Search date: 2026-08-01.

No new util-linux implementation is useful. The exact correction is upstream and present on all currently visible util-linux stable branches v2.40, v2.41, and v2.42. Debian testing and unstable moved to fixed upstream releases. Debian trixie stable remains at `2.41-5`; the package source identity plus absent quilt patch references make it the remaining plausible maintained destination. This package conclusion is an inference pending exact source unpack/build verification.

The issue/index phrase “derive cpuset ownership from owning mount” has no corresponding mechanism in PR #387, issue #234, PR #239, util-linux issues #3641/#4401, or commits `4581ede...`/`3cd5f1d...`. The canonical carrier scope controls this packet: caller-visible cpuset pointer ownership after parse failure.

## Files deliberately not changed

- util-linux `sys-utils/lscpu.c`: final cleanup exposes the stale pointer but does not create it.
- CPU-list parser policy: malformed input remains an error.
- current util-linux master/stable branches: they already contain the canonical correction.
- Debian testing/unstable packaging: fixed upstream releases already supersede the affected source.
- Linux Fieldwork retained model/tests: fresh execution passed without source changes.
