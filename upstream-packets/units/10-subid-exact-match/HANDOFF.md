# Current handoff

Updated: `2026-08-01 00:09 UTC`  
Worker or variant: `GPT-5.6 Thinking`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-10-subid-exact-match` |
| Linux Fieldwork base | `main` at `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Linux Fieldwork head | this final HANDOFF commit; parent packet head `3ca898443e2e69c5aed85497a5cb7d3c4861139b`; resulting commit is recorded in the final #397 checkpoint |
| Upstream base repository/branch | `https://salsa.debian.org/debian/mmdebstrap.git`, `master` |
| Upstream base commit | dgit master view `c8a789205ded12daccfb16deaa35ddd1fc8d688f`; direct Salsa verification remains the first incomplete step |
| Current published Debian source | `mmdebstrap 1.5.7-3`; Salsa tag abbreviated `6fde9997` |
| Candidate fork/branch | `NEEDS FORK` / `NEEDS BRANCH` |
| Candidate head | `NEEDS BRANCH` |
| Patch or series | `patches/0001-debian-tests-match-subid-account-field-exactly.patch` |
| Imported/local source identity | `upstream/mmdebstrap/debian/tests/testsuite` blob `9f4eda87430da38b08a23a50a51e53b22cf7414b` |
| Owning issue/PR | #397 unit 10; issue #80; product PR #92; proof PR #291 |
| Latest workflow/run/artifact | PR #291 Linux Fieldwork CI `30624718470` / 845, success |

## Current bounded claim

Debian mmdebstrap’s package-test setup can mistake a substring or regular-expression match in another `/etc/subuid` or `/etc/subgid` record for an assignment belonging to `AUTOPKGTEST_NORMAL_USER`. The selected two-line correction parses field 1 and compares it literally and exactly with `cut -s -d: -f1 | grep -Fxq --`, while preserving the existing append value and test flow.

The retained proof and this pass’s fresh synthetic smoke establish exact, substring, malformed, regex-significant, leading-hyphen, empty, absent, subuid/subgid parity, zero-fuzz application, shell syntax, and immediate-rerun behavior. Direct current-Salsa application and package/user-namespace integration remain.

## Work completed in this pass

- read issue #397, its packet protocol, `upstream-packets/README.md`, and `upstream-packets/INDEX.md`;
- read the complete direct carrier lineage: issue #80 and PRs #92, #215, #218, #225, #252, and #291;
- read adjacent package-test context issue #53 and PRs #72 and #86 to preserve the unit boundary;
- posted `CLAIMED — unit 10` on #397;
- created `upstream/unit-10-subid-exact-match` from current Linux Fieldwork `main`;
- created the complete required packet workspace;
- refreshed current public Debian/upstream identities and separated runtime numeric-UID work from this Debian package-test predicate;
- rewrote the retained correction with upstream path `debian/tests/testsuite`;
- ran a fresh zero-fuzz synthetic application and behavior/idempotency matrix;
- drafted the upstream merge-request text and recorded that a separate upstream issue is currently unnecessary;
- recorded decisions, limits, failed carrier evidence, cleanup, and the exact next action;
- posted the first durable `UNIT CHECKPOINT` on #397.

## Changed paths

- `upstream-packets/units/10-subid-exact-match/README.md`
- `upstream-packets/units/10-subid-exact-match/SOURCE_MAP.md`
- `upstream-packets/units/10-subid-exact-match/DEEP_DIVE.md`
- `upstream-packets/units/10-subid-exact-match/TESTS.md`
- `upstream-packets/units/10-subid-exact-match/UPSTREAM_ISSUE.md`
- `upstream-packets/units/10-subid-exact-match/UPSTREAM_PR.md`
- `upstream-packets/units/10-subid-exact-match/DECISIONS.md`
- `upstream-packets/units/10-subid-exact-match/HANDOFF.md`
- `upstream-packets/units/10-subid-exact-match/patches/0001-debian-tests-match-subid-account-field-exactly.patch`

## Distinguishing observations

- Linux Fieldwork’s exact imported Debian 1.5.7-3 testsuite blob still contains whole-record unanchored grep for both subuid and subgid.
- `cut -s` is required. Plain `cut -d: -f1` emits delimiter-free rows unchanged, allowing a malformed line containing only the username to suppress setup.
- `grep -F`, `-x`, and `--` each protect a separately executed boundary: regex punctuation, substring fields, and leading-hyphen identities.
- PR #252’s red run is useful evidence: zero-fuzz enforcement found a malformed retained hunk before any behavioral claim. PR #291 repaired and superseded it.
- PR #291 is the canonical durable proof. PRs #215, #218, #225, and #252 remain historical/superseded.
- Upstream runtime commit `6f0a2fcd7f0b21a69d6c2b7c90272a132ed58ff5` adds numeric UID/GID support in different files. It does not consume this Debian package-test account-name defect.
- `coverage.txt` identifies relevant downstream consumers including `unshare-as-root-user`, `auto-mode-as-normal-user`, and the QEMU negative cases `fail-without-etc-subuid` and `fail-without-username-in-etc-subuid`. The package test’s mirror/setup prelude must run before selecting a focused coverage subset.

## Gates completed

- historical canonical proof: PR #291 head `125d4e5097625b38850292525c7eb2f98818f5d9`, Linux Fieldwork CI `30624718470` / 845, success;
- fresh packet-local zero-fuzz patch application: pass, no fuzz output;
- complete reconstructed shell `/bin/sh -n`: pass;
- exactly two replacement lines with equal source line count: pass;
- exact account present: pass for subuid and subgid;
- substring collision: baseline loses, candidate passes;
- delimiter-free malformed row: candidate passes;
- regex-significant username: candidate passes;
- leading-hyphen username: candidate passes;
- empty and absent files: candidate passes;
- immediate rerun: pass and byte-identical;
- temporary-state cleanup: pass.

## Red or neutral runs classified

- PR #252 CI `30598944690` / 797: patch-packaging failure; the retained hunk declared ten lines while supplying nine. Product behavior was unexecuted.
- Direct `git ls-remote` against Salsa from the execution container: environment/network failure, `Could not resolve host`; it supplies no source-state conclusion.
- Public Salsa branch-page retrieval errors: source-host/UI retrieval limitation. Debian Sources and dgit supplied released/current package views, while direct Salsa exact-head verification remains pending.

## Cleanup state

The fresh smoke used one temporary directory, temporary stand-ins for subuid/subgid, `/bin/sh`, Python, GNU patch, GNU cut, and GNU grep. A shell trap removed the tree. No users, subordinate-ID records, namespaces, mounts, sockets, containers, packages, cache entries, or background processes remain.

Intentional retained state is limited to the Linux Fieldwork packet branch and the internal #397 claim/checkpoint comments.

## First incomplete step

Obtain a direct checkout of current Debian Salsa `master`, record the exact head and `debian/tests/testsuite` blob, and apply the packet patch with zero drift.

## Next safe action

Run from a workspace containing this Linux Fieldwork checkout:

```text
git clone https://salsa.debian.org/debian/mmdebstrap.git unit10-mmdebstrap
cd unit10-mmdebstrap
git checkout master
git rev-parse HEAD
git hash-object debian/tests/testsuite
git apply --check ../linux-fieldwork/upstream-packets/units/10-subid-exact-match/patches/0001-debian-tests-match-subid-account-field-exactly.patch
git apply ../linux-fieldwork/upstream-packets/units/10-subid-exact-match/patches/0001-debian-tests-match-subid-account-field-exactly.patch
git diff --check
/bin/sh -n debian/tests/testsuite
git diff -- debian/tests/testsuite
```

Record the exact head, blob, apply output, and complete diff immediately in `README.md`, `SOURCE_MAP.md`, and `TESTS.md`.

After current-base application passes, use the existing disposable sid/package-test harness to run the package setup prelude and the shortest relevant consumer set. Start with `create-directory`, `unshare-as-root-user`, and `auto-mode-as-normal-user`; retain the first independent result. Run the QEMU negative subuid cases only when that environment is already available.

## Unresolved blockers

- technical: direct current-Salsa application and focused package/user-namespace execution;
- compatibility: confirm the package-test ordinary user remains an account name at the current base;
- overlap: repeat public issue/MR search immediately before any authorization request;
- environment or tooling: Salsa DNS failed from the current execution container;
- delivery: controlled Salsa fork/branch absent;
- patch metadata: replace the internal placeholder author before creating any authorized upstream candidate branch;
- authority: external contact remains unauthorized.

## Files to read first

1. `README.md`
2. `SOURCE_MAP.md`
3. `DEEP_DIVE.md`
4. `TESTS.md`
5. `DECISIONS.md`
6. issue #80, PR #92, and PR #291
7. superseded-carrier evidence in PR #252 only when reviewing zero-fuzz packaging history

## External-contact state

`false; none occurred`. No upstream issue, merge request, fork, branch, email, comment, review, or other public contact was created.

## Do not repeat

- do not restore PR #215, #218, #225, or #252 as the canonical carrier;
- do not remove `cut -s` without a replacement malformed-row policy and executable discriminator;
- do not accept fuzzy patch application;
- do not combine this unit with runtime numeric UID/GID support, the `dev-ptmx` dependency fix, or the broad sid harness;
- do not rerun the historical PR #291 proof merely to recreate its receipt; rerun when the current upstream base or candidate changes;
- do not treat Linux Fieldwork’s imported source blob as a substitute for direct current-Salsa verification;
- do not create a fork, upstream branch, issue, merge request, email, comment, or review without explicit authorization.
