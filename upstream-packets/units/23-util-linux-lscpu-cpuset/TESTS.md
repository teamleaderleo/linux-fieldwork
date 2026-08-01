# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Upstream affected base | util-linux tag `v2.41`; `lib/path.c` blob `42a33ffc53752ba5e00aed2396ca9a4fc876c1ef` |
| Canonical fix | `4581ede384f22983d6155768635ce43cb5304cb0` |
| Current upstream heads | master `fd82c4043fab942b889f478800118c66edfbc39f`; stable/v2.40 `160b7e47d4e6ba0fd15e66b4041bbdc67d2c457f`; stable/v2.41 `2dacaf3eea391e3bbf48e7d3ecce02cafe045b6d`; stable/v2.42 `84796d917bcbad37aecfdadf36d71fee5b356efd` |
| Candidate head | none; retained canonical patch under package verification |
| Linux Fieldwork base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Platform/distribution | Linux execution sandbox; Debian userspace |
| Architecture | x86_64 |
| Kernel | Linux 6.12.13 |
| Shell/runtime | `/bin/bash`; Python 3.13.5 |
| Privilege boundary | unprivileged; no mounts, containers, or package install |
| Important tool versions | cc 14.2.0; GNU patch 2.8 |
| Execution date | 2026-08-01 |

## Baseline reproducer

### Command

```text
cc -std=c11 -Wall -Wextra -Werror \
  investigations/util-linux-lscpu-cpuset-double-free/ownership_model.c \
  -o /tmp/baseline
/tmp/baseline
```

The retained runner performed this compile in a temporary directory without `CLEAR_OUTPUT_AFTER_ERROR`.

### Expected distinguishing result

The parser model frees the published output and retains the address. Later cleanup detects duplicate logical cleanup and exits 42.

### Observed result

- status: 42 inside the runner; overall matrix status 0 after expected-result validation;
- stderr: `duplicate cleanup detected`;
- changed state: temporary compiler output only;
- surviving processes/files/resources: none from the runner temporary directory;
- receipt: `artifacts/2026-08-01-focused-regression.txt`.

## Candidate reproducer

### Command

```text
cc -DCLEAR_OUTPUT_AFTER_ERROR -std=c11 -Wall -Wextra -Werror \
  investigations/util-linux-lscpu-cpuset-double-free/ownership_model.c \
  -o /tmp/candidate
/tmp/candidate
```

The retained runner performed this compile in a temporary directory.

### Expected result

The parser model frees the output, clears it, and later cleanup exits 0.

### Observed result

- status: 0;
- stdout: `cleanup is idempotent after parse failure`;
- changed state: temporary compiler output only;
- surviving processes/files/resources: none from the runner temporary directory;
- receipt: `artifacts/2026-08-01-focused-regression.txt`.

## Matrix

| Case | Baseline | Candidate | Exact command or test | Result identity |
| --- | --- | --- | --- | --- |
| Ownership failure | retains freed output; later duplicate cleanup | clears output; later cleanup harmless | `test_baseline_and_candidate_ownership_matrix` | PASS |
| Exact fixture | v2.41 error path matches retained bytes | canonical patch adds free-then-NULL | `test_retained_patch_applies_to_the_exact_v241_fixture` | PASS |
| Losing mutation | one leading newline changes fixture identity | assertion fails before patch execution | `test_fixture_drift_is_rejected_before_patch_execution` | PASS |
| Patch content/order | stale output in baseline | `cpuset_free(*set)` precedes `*set = NULL` | `test_retained_patch_clears_output_after_free` | PASS |
| Model ownership order | first cleanup occurs in parser; later cleanup reaches published pointer | output clear interrupts duplicate path | `test_model_preserves_the_relevant_ownership_boundary` | PASS |
| Patch dry-run | exact fixture | applies with `--fuzz=0`; hunk offset -1044 due minimal fixture | `patch --batch --forward --fuzz=0 --dry-run -p1 -i ...` | PASS |
| Patch real application | exact fixture | applies with `--fuzz=0`; reviewed final source | `patch --batch --forward --fuzz=0 -p1 -i ...` | PASS |
| Immediate clean rerun | fresh temporary directories | same 5/5 pass | `/usr/bin/python3 -m unittest -v tests/test_util_linux_lscpu_cpuset_double_free.py` | PASS |

## Upstream-native gates

| Gate | Exact command | Result | Candidate head |
| --- | --- | --- | --- |
| util-linux focused native tests | package/source-specific command pending | NOT RUN | none |
| Relevant lscpu integration tests | pending exact Debian source tree | NOT RUN | none |
| Formatting/lint | canonical upstream patch already merged; package metadata absent | NOT RUN | none |
| Debian package build/test | `dpkg-buildpackage` or Salsa-equivalent pending source unpack | NOT RUN | none |
| Issue #4401 attachment execution | exact `test.tar.gz` pending retrieval | NOT RUN | none |
| ASan/Valgrind package execution | pending rebuilt package | NOT RUN | none |

## Linux Fieldwork retained gates

| Gate or fixture | Exact command/run | Result | Artifact/digest |
| --- | --- | --- | --- |
| Full focused unittest | `/usr/bin/python3 -m unittest -v tests/test_util_linux_lscpu_cpuset_double_free.py` | 5 tests passed in 0.082s | `artifacts/2026-08-01-focused-regression.txt` |
| Ownership runner | `python3 investigations/util-linux-lscpu-cpuset-double-free/run_model.py` | baseline 42; candidate 0; runner 0 | same receipt |
| Exact retained fixture | byte equality in unittest | PASS | SHA-256 `ee86a1384bdad67633dfb8e106937f43b00c33836be6791ffcb7099da3273f96` |
| Canonical patch | content/order and zero-fuzz application | PASS | SHA-256 `3930c2402aeddb37149b2f50ef0b7b692674cfa3898a371f3fc174131672a523` |
| Current branch source inspection | GitHub exact refs and blobs | master plus stable/v2.40/v2.41/v2.42 contain free-then-NULL | recorded in `SOURCE_MAP.md` |
| Debian suite/package inspection | official package and source patch pages | trixie `2.41-5`; no `cpuset`, `lib/path.c`, or `4581ede` patch-series match | recorded in `SOURCE_MAP.md` |

## Patch application and rebase

- base identity: retained exact minimal v2.41 fixture; full Debian effective source pending;
- patch application command: `patch --batch --forward --fuzz=0 -p1 -i investigations/util-linux-lscpu-cpuset-double-free/0001-clear-cpuset-output-after-error.patch`;
- fuzz/offset result: zero fuzz; hunk offset -1044 lines on the intentionally minimal fixture;
- conflict resolution: none;
- complete diff reviewed: yes for retained fixture; one file, three insertions, one deletion;
- active overlap searched: current upstream master/stable source and Debian trixie published quilt series;
- package-level application: NOT RUN.

## Cleanup and rerun

The model runner and patch tests used temporary directories. No mounts, sockets, locks, containers, package installs, or long-lived processes were created. Temporary source and binaries were removed by their context managers or test teardown. The full five-test command passed in one clean run; all individual patch operations used fresh copied fixtures.

## Tests not run

- exact Debian `2.41-5` source unpack and final effective-source hash;
- Debian quilt application and canonical patch insertion;
- baseline package build and issue #4401 fixture execution;
- patched package build and fixture rerun;
- ordinary valid `lscpu` text/JSON output comparison;
- util-linux native lscpu test suite against the package tree;
- ASan or Valgrind against actual util-linux binaries;
- architecture-specific package builds beyond the retained architecture-independent model;
- Debian stable-update policy and autopkgtest gates.

These unexecuted gates are the reason for `HOLD`.

## Failure classification

No retained regression gate failed. The earlier baseline status 42 is the expected product-owner distinction. The minimal-fixture hunk offset is expected because the fixture retains exact hunk bytes without upstream line padding; zero fuzz remains mandatory.

## Final evidence statement

The executed matrix establishes that the canonical free-then-NULL patch fixes the modeled caller-visible ownership defect, applies exactly to the retained v2.41 error path with zero fuzz, and has a functioning losing control. Source inspection establishes that current util-linux branches already carry the fix. Public Debian source/package evidence identifies trixie `2.41-5` as the remaining plausible maintained package lane. Package-level applicability, reproduction, build, and compatibility remain open.
