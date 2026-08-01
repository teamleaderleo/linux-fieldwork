# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Upstream base | dgit master view `c8a789205ded12daccfb16deaa35ddd1fc8d688f`; direct Salsa checkout pending |
| Candidate head | `NEEDS BRANCH` |
| Linux Fieldwork branch | `upstream/unit-10-subid-exact-match` |
| Imported source | Debian `mmdebstrap 1.5.7-3`, testsuite blob `9f4eda87430da38b08a23a50a51e53b22cf7414b` |
| Historical canonical proof head | PR #291 `125d4e5097625b38850292525c7eb2f98818f5d9` |
| Platform/distribution | Debian 13 |
| Architecture | `x86_64` |
| Kernel | `6.12.13` |
| Shell/runtime | `/usr/bin/dash` `0.5.12-12`; Python `3.13.5` |
| Privilege boundary | ordinary temporary files only; no user, namespace, mount, or package changes |
| Important tool versions | GNU patch `2.8`; GNU grep `3.11`; GNU coreutils `cut` `9.7` |

## Baseline reproducer

### Command

The packet-local smoke reconstructed the exact nine-line package-test block at its declared hunk location and executed the baseline predicate against a temporary file containing:

```text
old-debci-helper:200000:65536
```

with:

```text
AUTOPKGTEST_NORMAL_USER=debci /bin/sh -eu -c '<baseline subuid or subgid block>'
```

### Expected distinguishing result

The unanchored whole-record grep returns success because `debci` appears inside another account name. The setup block appends nothing.

### Observed result

- status: `0`
- stdout/stderr: empty
- changed state: none
- resulting bytes, for both subuid and subgid variants: `old-debci-helper:200000:65536\n`
- classification: baseline false positive reproduced

## Candidate reproducer

### Commands

```text
patch --batch --forward --fuzz=0 -p1 -i 0001.patch
/bin/sh -n tree/debian/tests/testsuite
python3 synthetic_matrix.py baseline tree/debian/tests/testsuite
```

The temporary patch body is byte-equivalent to `patches/0001-debian-tests-match-subid-account-field-exactly.patch` from the `diff --git` line onward.

### Expected result

- exact patch application with no fuzz message;
- complete reconstructed shell parses;
- exactly two source-line replacements and equal line counts;
- the full bounded account matrix passes for both files;
- immediate rerun preserves bytes.

### Observed result

```text
PATCH_OUTPUT=patching file debian/tests/testsuite
SHELL_SYNTAX=PASS
```

Exact replacements:

```text
line 154: grep whole /etc/subuid record -> cut field 1 | grep -Fxq --
line 157: grep whole /etc/subgid record -> cut field 1 | grep -Fxq --
```

All candidate cases returned status 0 and expected bytes.

## Matrix

| Case | Baseline | Candidate | Exact command or test | Result identity |
| --- | --- | --- | --- | --- |
| Primary negative control: substring account | leaves missing `debci` entry | appends `debci:100000:65536` | packet-local synthetic matrix | PASS, discriminator observed |
| Exact account present | whole grep succeeds | exact field succeeds | matrix for subuid and subgid | PASS, unchanged bytes |
| Delimiter-free `debci` row | whole grep suppresses append | `cut -s` discards row and append occurs | retained PR #291 test and packet matrix | PASS |
| Regex-significant user `debci.*` | regex can match `debci123` | fixed-string comparison appends literal user | retained proof and packet matrix | PASS |
| Leading-hyphen user `-debci` | unsafe without option boundary | exact record remains unchanged with `--` | retained proof and packet matrix | PASS |
| Empty file | append | append | packet matrix | PASS |
| Absent file | append | append | packet matrix | PASS |
| Subuid/subgid parity | same false-positive class | same exact-field behavior | packet matrix | PASS |
| Immediate rerun | depends on baseline match | exact row prevents duplicate | packet matrix | PASS, byte-identical |
| Complete shell syntax | historical imported testsuite | patched imported testsuite passed `/bin/sh -n` in PR #291; reconstructed upstream-path shell passed locally | `/bin/sh -n` | PASS within stated source boundary |
| Source diff fence | unbounded zip could miss tail changes in early proof | equal line count plus `zip(..., strict=True)` | PR #291 retained test | PASS |
| Patch fuzz | malformed ten-line declaration failed at PR #252 run 797 | repaired nine-line hunk applies with zero fuzz | PR #291 and packet smoke | PASS |

## Upstream-native gates

| Gate | Exact command | Result | Candidate head |
| --- | --- | --- | --- |
| Current-base apply check | `git apply --check <packet patch>` in direct Salsa checkout | NOT RUN | NEEDS BRANCH |
| Focused package/user-namespace test | identify shortest relevant Debian autopkgtest or coverage invocation after checkout | NOT RUN | NEEDS BRANCH |
| Complete Debian autopkgtest | `autopkgtest`/Salsa CI equivalent | NOT RUN | NEEDS BRANCH |
| Formatting/lint | shellcheck/shfmt gates used by the package | NOT RUN | NEEDS BRANCH |
| Build/package test | Debian package build and package tests | NOT RUN | NEEDS BRANCH |

## Linux Fieldwork retained gates

| Gate or fixture | Exact command/run | Result | Artifact/digest |
| --- | --- | --- | --- |
| Canonical proof CI | Linux Fieldwork CI `30624718470` / 845 on PR #291 head `125d4e5097625b38850292525c7eb2f98818f5d9` | PASS; 249 tests, four dedicated unit tests once each | GitHub Actions run 845 |
| First zero-fuzz detector | Linux Fieldwork CI `30598944690` / 797 on PR #252 | FAIL before behavior; malformed hunk count required fuzz | classified patch-packaging failure |
| Earlier leading-hyphen/full-shell proof | Linux Fieldwork CI `30581822309` on PR #218 head `cde9d361...` | PASS | superseded by PR #291 |
| Packet-local upstream-path smoke | temporary reconstructed source, 2026-08-01 | PASS | console receipt summarized above; temporary directory cleaned |

## Patch application and rebase

- current published package: Debian `mmdebstrap 1.5.7-3`;
- dgit master identity observed: `c8a789205ded12daccfb16deaa35ddd1fc8d688f`;
- direct Salsa base identity: pending clone/API confirmation;
- packet smoke command: `patch --batch --forward --fuzz=0 -p1 -i 0001.patch`;
- smoke result: status 0, `patching file debian/tests/testsuite`, no fuzz text;
- full current-checkout conflict resolution: pending;
- complete upstream diff reviewed: patch itself yes; direct current-base diff pending;
- active overlap searched: public package/source/runtime summaries and Debian bug list on 2026-08-01; repeat before authorization.

## Cleanup and rerun

The packet-local smoke used one `mktemp -d` tree, temporary subuid/subgid stand-ins, `/bin/sh`, Python, `patch`, `cut`, and `grep`. A shell trap removed the tree. It created no accounts, namespaces, mounts, sockets, containers, packages, cache entries, or persistent host files. The immediate-rerun case passed for both subuid and subgid stand-ins.

Intentional retained state exists only in the Linux Fieldwork packet branch.

## Tests not run

- direct Salsa `master` clone and exact SHA/blob receipt: network/DNS access to Salsa was unavailable from the execution container; public read-only pages were used for the refresh;
- exact current-base `git apply --check`: requires that checkout;
- Debian autopkgtest and user-namespace integration: requires package source, dependencies, mirror/cache preparation, and suitable test capabilities;
- full repository Linux Fieldwork CI on this packet branch: no PR was opened and no hosted run was requested in this pass;
- external Salsa CI: external contact and fork activity remain unauthorized.

## Failure classification

- PR #252 run 797: patch-packaging owner; no product claim.
- Direct container `git ls-remote` attempt for Salsa: environment/network owner (`Could not resolve host`); no source-state claim from that command.
- Public Salsa branch page errors: source-host/UI retrieval limitation; dgit and Debian Sources provided current released/package views.

## Final evidence statement

The executed packet matrix establishes the exact predicate defect and the corrected behavior for synthetic subordinate-ID files on Debian 13 with dash, GNU patch, GNU grep, and GNU cut. Historical PR #291 evidence establishes zero-fuzz application and full shell syntax on Linux Fieldwork’s exact imported Debian 1.5.7-3 testsuite blob.

The conclusion ends before direct current-Salsa application, package build, Debian autopkgtest execution, user-namespace integration, and public review.
