# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Direct upstream base | dgit master view `c8a789205ded12daccfb16deaa35ddd1fc8d688f`; live Salsa clone/API confirmation remains pending |
| Exact imported source | Debian `mmdebstrap 1.5.7-3`, testsuite Git blob `9f4eda87430da38b08a23a50a51e53b22cf7414b` |
| Exact candidate file blob | `6925c7f05c3a5f050a4d3f89142085ff687ce3b0` after packet application |
| Candidate branch/head | `NEEDS BRANCH`; the ephemeral local verification commit is evidence only |
| Linux Fieldwork branch | `upstream/unit-10-subid-exact-match` |
| Historical canonical proof head | PR #291 `125d4e5097625b38850292525c7eb2f98818f5d9` |
| Platform/distribution | Debian 13 |
| Architecture | `x86_64` |
| Shell/runtime | `/usr/bin/dash` `0.5.12-12`; Python `3.13.5` |
| Privilege boundary | ordinary temporary files only; no user, namespace, mount, or package changes |
| Important tool versions | Git, GNU patch `2.8`, GNU grep `3.11`, GNU coreutils `cut` `9.7` |

## Baseline reproducer

### Fixture

For `AUTOPKGTEST_NORMAL_USER=debci`, the file contains only another account:

```text
old-debci-helper:200000:65536
```

### Predicate

```sh
if [ ! -e "$file" ] || ! grep "$AUTOPKGTEST_NORMAL_USER" "$file"; then
    echo "$AUTOPKGTEST_NORMAL_USER:100000:65536" >> "$file"
fi
```

### Expected distinguishing result

The unanchored whole-record grep returns success because `debci` appears inside another account name. The setup block appends nothing.

### Observed result

- status: `0`;
- stdout/stderr: empty;
- resulting bytes: `old-debci-helper:200000:65536\n`;
- classification: baseline false positive reproduced for both subuid and subgid blocks.

## Exact imported-source application gate

Durable receipt: [`artifacts/2026-08-01-exact-imported-source-gate.md`](artifacts/2026-08-01-exact-imported-source-gate.md).

### Admission

The connector-fetched full testsuite was reconstructed locally and admitted only when:

```text
git hash-object debian/tests/testsuite
9f4eda87430da38b08a23a50a51e53b22cf7414b
```

This equals the recorded imported source blob. Additional identities:

```text
source SHA-256:    14bd64347e58cdc36e3b33aaff8663f9ea34dd0ea24049a7452c849923bd090f
source lines:      219
packet patch SHA:  fc9c0c4d0552a80565a49a05f068934b3230b81703c9e0ed9c59d3307f9d544d
```

### Commands

```sh
git apply --check --whitespace=error-all 0001.patch
git am --keep-cr 0001.patch
/bin/sh -n debian/tests/testsuite
git diff --check HEAD^ HEAD
git diff --numstat HEAD^ HEAD -- debian/tests/testsuite
```

### Observed result

```text
Applying: debian/tests: match subid account fields exactly
NEW_BLOB=6925c7f05c3a5f050a4d3f89142085ff687ce3b0
DIFF_STAT= debian/tests/testsuite | 4 ++--
 1 file changed, 2 insertions(+), 2 deletions(-)
DIFF_CHECK=
GIT_DIFF_NUMSTAT=2  2  debian/tests/testsuite
```

Candidate file identities:

```text
candidate SHA-256: d9792e1fa95d4565a49cbe6fcf305d210d0f855a7334049f2f6b366839dc734d
candidate lines:   219
ephemeral local verification commit: 7af87bd53b84c2c4310e0b58bbce37654748c266
```

The ephemeral commit is a disposable verification identity, not an upstream candidate head.

## Exact behavior matrix

The matrix read the baseline from Git and the applied candidate from the same disposable repository. It extracted the real package-test blocks and used temporary stand-in files.

| Case | Baseline | Candidate | Result |
| --- | --- | --- | --- |
| Substring account | suppresses required append | appends exact account | discriminator observed |
| Exact account present | found | found | unchanged bytes |
| Delimiter-free `debci` row | suppresses append | `cut -s` discards malformed row and append occurs | pass |
| Regex-significant `debci.*` | can match another account | fixed string remains literal | pass |
| Leading-hyphen `-debci` | unsafe without option boundary | exact record survives through `--` | pass |
| Empty file | append | append | pass |
| Absent file | append | append | pass |
| Subuid/subgid parity | same defect class | same exact-field behavior | pass |
| Immediate rerun | depends on broad match | no duplicate | byte-identical |
| Source diff fence | early ordinary `zip()` could miss tail drift | equal line count and exactly two replacements | pass |
| Complete shell syntax | baseline parsed | candidate parsed | pass |
| Git whitespace/apply gate | n/a | clean | pass |

Receipt, executed twice:

```text
DIFFS=2
CASES=18
MATRIX=PASS
DIFFS=2
CASES=18
MATRIX=PASS
```

## Historical Linux Fieldwork evidence

| Gate or fixture | Exact command/run | Result | Interpretation |
| --- | --- | --- | --- |
| Canonical proof CI | Linux Fieldwork CI `30624718470` / 845 on PR #291 head `125d4e5097625b38850292525c7eb2f98818f5d9` | PASS; 249 tests, four dedicated tests once each | canonical durable proof |
| First zero-fuzz detector | Linux Fieldwork CI `30598944690` / 797 on PR #252 | FAIL before behavior | malformed hunk count; patch-packaging owner |
| Earlier leading-hyphen/full-shell proof | Linux Fieldwork CI `30581822309` on PR #218 head `cde9d361...` | PASS | superseded by PR #291 |
| Earlier packet excerpt smoke | reconstructed hunk, 2026-08-01 | PASS | superseded by exact full-blob gate above |

## Upstream-native gates

| Gate | Exact command | Result | Candidate head |
| --- | --- | --- | --- |
| Live Salsa current-base identity | direct clone/API, `git rev-parse HEAD`, and `git hash-object debian/tests/testsuite` | NOT RUN; source-host DNS unavailable in execution container | NEEDS BRANCH |
| Live Salsa apply check | `git apply --check <packet patch>` in direct checkout | NOT RUN | NEEDS BRANCH |
| Focused package/user-namespace test | package setup prelude plus shortest consumer set | NOT RUN | NEEDS BRANCH |
| Complete Debian autopkgtest | `autopkgtest` or Salsa CI equivalent | NOT RUN | NEEDS BRANCH |
| Formatting/lint | package-declared shell/static gates | NOT RUN | NEEDS BRANCH |
| Build/package test | Debian package build and package tests | NOT RUN | NEEDS BRANCH |

## Patch application and rebase

- current published package: Debian `mmdebstrap 1.5.7-3`;
- current dgit identity observed during refresh: `c8a789205ded12daccfb16deaa35ddd1fc8d688f`;
- exact imported testsuite blob: `9f4eda87430da38b08a23a50a51e53b22cf7414b`;
- exact imported-source `git apply --check --whitespace=error-all`: pass;
- `git am --keep-cr`: pass;
- complete exact imported-source diff: two insertions, two deletions, one file;
- live Salsa rebase/conflict result: pending;
- active overlap search: public package/source/runtime summaries and Debian bug list checked on 2026-08-01; repeat before authorization.

## Cleanup and rerun

The exact-source gate used `/tmp/unit10-exact-source`, one disposable Git repository, and `TemporaryDirectory` paths for every account fixture. It created no accounts, subordinate-ID records, namespaces, mounts, sockets, containers, packages, cache entries, or background processes.

The behavior matrix passed twice. Temporary matrix code was removed after execution. The disposable source repository remains outside Linux Fieldwork and carries no external authority; the durable receipt records every identity needed for reconstruction.

## Tests not run

- direct Salsa `master` clone and exact live SHA/blob receipt: DNS access to Salsa remained unavailable from the execution container;
- exact live-current-base application: requires that checkout;
- Debian autopkgtest and user-namespace integration: requires package source, dependencies, mirror/cache preparation, and suitable capabilities;
- full Linux Fieldwork hosted CI on this packet branch: no PR or workflow run was created;
- Salsa CI, fork, or merge request: external contact and fork activity remain unauthorized.

## Failure classification

- PR #252 run 797: patch-packaging failure; no product behavior executed.
- Direct Salsa `git ls-remote`/clone attempts: environment/network failure, `Could not resolve host`; no live-source conclusion.
- The exact imported-source gate passed; it establishes the recorded Debian 1.5.7-3 blob and candidate bytes, while ending before live Salsa drift and package integration.

## Final evidence statement

The current record establishes the exact predicate defect and corrected behavior on the full recorded Debian `mmdebstrap 1.5.7-3` testsuite blob. Git admission, whitespace checking, mail-patch application, complete shell syntax, exact two-line diff fencing, and the 18-case matrix all pass; the matrix passed twice.

The conclusion ends before direct live Salsa application, package build, Debian autopkgtest execution, user-namespace integration, hosted public review, and submission.
