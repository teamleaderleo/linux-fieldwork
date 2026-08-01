# Current handoff

Updated: `2026-08-01 08:09 +08:00`  
Worker or variant: `GPT-5.6 Thinking`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-10-subid-exact-match` |
| Linux Fieldwork base | `main` at `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Linux Fieldwork head | this HANDOFF update follows packet parent `d0194040a58ce082e6d79c02d28ebaad64105824`; the resulting exact head is recorded in the final #397 checkpoint |
| Upstream base repository/branch | `https://salsa.debian.org/debian/mmdebstrap.git`, `master` |
| Upstream base commit | dgit master view `c8a789205ded12daccfb16deaa35ddd1fc8d688f`; direct live Salsa verification remains incomplete |
| Current published Debian source | `mmdebstrap 1.5.7-3`; Salsa release tag abbreviated `6fde9997` |
| Candidate fork/branch | `NEEDS FORK` / `NEEDS BRANCH` |
| Candidate head | `NEEDS BRANCH` |
| Patch | `patches/0001-debian-tests-match-subid-account-field-exactly.patch` |
| Patch SHA-256 | `fc9c0c4d0552a80565a49a05f068934b3230b81703c9e0ed9c59d3307f9d544d` |
| Imported source blob | `debian/tests/testsuite` Git blob `9f4eda87430da38b08a23a50a51e53b22cf7414b` |
| Candidate source blob | `debian/tests/testsuite` Git blob `6925c7f05c3a5f050a4d3f89142085ff687ce3b0` |
| Owning issue/PR | #397 unit 10; issue #80; product PR #92; proof PR #291 |
| Latest historical workflow | PR #291 Linux Fieldwork CI `30624718470` / 845, success |
| Latest new receipt | `artifacts/2026-08-01-exact-imported-source-gate.md` |

## Current bounded claim

Debian mmdebstrap’s package-test setup can mistake a substring or regular-expression match in another `/etc/subuid` or `/etc/subgid` record for an assignment belonging to `AUTOPKGTEST_NORMAL_USER`. The selected two-line correction parses field 1 and compares it literally and exactly with `cut -s -d: -f1 | grep -Fxq --`, while preserving the existing append value and test flow.

The full recorded Debian 1.5.7-3 testsuite was admitted by exact Git blob. Git whitespace checking, mail-patch application, complete shell syntax, exact two-line diff fencing, and the 18-case behavior/idempotency matrix passed; the matrix passed twice. Direct live Salsa identity/application and package/user-namespace integration remain.

## Work completed in this pass

- resumed the existing unit 10 packet and branch;
- re-read the current packet state and prior complete handoff;
- confirmed the branch contains the full required packet bundle and retained patch;
- retried read-only live Salsa access through project, branch, archive, raw-file, API, and direct Git paths without creating any fork or public action;
- classified direct container Salsa access as an environment/DNS limitation;
- reconstructed the full connector-fetched imported testsuite;
- required the reconstructed file to hash to Git blob `9f4eda87430da38b08a23a50a51e53b22cf7414b` before use;
- ran `git apply --check --whitespace=error-all` on the packet patch;
- applied the mail patch with `git am --keep-cr`;
- ran complete `/bin/sh -n`, `git diff --check`, exact diff-stat, line-count, blob, and SHA-256 checks;
- ran the complete 18-case baseline/candidate matrix twice;
- recorded the exact receipt under `artifacts/`;
- updated `README.md`, `TESTS.md`, and `DECISIONS.md` with the stronger evidence;
- removed the disposable verification repository and temporary outputs;
- made no upstream contact.

## Changed paths in this pass

- `upstream-packets/units/10-subid-exact-match/artifacts/2026-08-01-exact-imported-source-gate.md`
- `upstream-packets/units/10-subid-exact-match/README.md`
- `upstream-packets/units/10-subid-exact-match/TESTS.md`
- `upstream-packets/units/10-subid-exact-match/DECISIONS.md`
- `upstream-packets/units/10-subid-exact-match/HANDOFF.md`

## Distinguishing observations

- The reconstructed full source exactly matches the recorded imported Git blob; the stronger gate no longer relies on a nine-line excerpt.
- The packet patch applies cleanly under Git’s whitespace-error gate and through mail-patch application.
- The candidate source has Git blob `6925c7f05c3a5f050a4d3f89142085ff687ce3b0`, SHA-256 `d9792e1fa95d4565a49cbe6fcf305d210d0f855a7334049f2f6b366839dc734d`, and the same 219-line count as the baseline.
- The complete diff is one file with two insertions and two deletions; `git diff --check` is empty.
- The behavior matrix executed baseline and candidate blocks from the same admitted Git history. It reported `DIFFS=2`, `CASES=18`, and `MATRIX=PASS` twice.
- `cut -s` remains required because delimiter-free rows otherwise emerge from `cut` unchanged.
- `grep -F`, `-x`, and `--` protect separate executed boundaries: regex punctuation, exact field identity, and leading-hyphen data.
- Live Salsa pages remain publicly visible, while direct Git/API/archive retrieval from the execution container fails at DNS resolution. This result changes the environment assessment, not source behavior.

## Gates completed

- exact full imported-source Git blob admission: pass;
- source SHA-256 and line-count receipt: pass;
- `git apply --check --whitespace=error-all`: pass;
- `git am --keep-cr`: pass;
- complete candidate `/bin/sh -n`: pass;
- `git diff --check`: pass;
- exact candidate blob, SHA-256, line count, and two-line diff receipt: pass;
- baseline substring negative control: loses as expected for subuid and subgid;
- candidate exact, substring, malformed, regex-significant, leading-hyphen, empty, absent, parity, and rerun cases: pass;
- full 18-case matrix: pass twice;
- historical canonical proof: PR #291 head `125d4e5097625b38850292525c7eb2f98818f5d9`, CI `30624718470` / 845, success;
- cleanup verification: pass.

## Red or neutral runs classified

- PR #252 CI `30598944690` / 797: patch-packaging failure; product behavior unexecuted.
- Direct `git ls-remote`, clone, API, raw-file, and archive attempts to Salsa from the execution container: environment/DNS failure, `Could not resolve host`; no live-source conclusion.
- Public source-host branch/file UI retrieval errors: read-path limitation; they do not contradict the exact imported-source result.

## Cleanup state

Removed `/tmp/unit10-exact-source`, the temporary Git-am output, partial download destinations, and temporary HTML paths. The behavior matrix’s `TemporaryDirectory` fixtures cleaned themselves.

No users, subordinate-ID records, namespaces, mounts, sockets, containers, packages, cache entries, background processes, or source-tree mutations survive outside the Linux Fieldwork branch. Intentional retained state is the packet, exact evidence artifact, and #397 routing comments.

## First incomplete step

Obtain a direct read of the live Debian Salsa `master` ref, record its exact commit and `debian/tests/testsuite` blob, and compare that blob with the admitted imported blob before applying the packet patch.

## Next safe action

From an environment with read-only Salsa DNS access:

```text
git clone --filter=blob:none --no-checkout https://salsa.debian.org/debian/mmdebstrap.git unit10-mmdebstrap
cd unit10-mmdebstrap
git checkout master
git rev-parse HEAD
git hash-object debian/tests/testsuite
git apply --check --whitespace=error-all ../linux-fieldwork/upstream-packets/units/10-subid-exact-match/patches/0001-debian-tests-match-subid-account-field-exactly.patch
git apply ../linux-fieldwork/upstream-packets/units/10-subid-exact-match/patches/0001-debian-tests-match-subid-account-field-exactly.patch
git diff --check
/bin/sh -n debian/tests/testsuite
git diff --stat
git diff -- debian/tests/testsuite
```

Record the live head, live baseline blob, apply result, and complete diff immediately. If the live baseline blob equals `9f4eda87430da38b08a23a50a51e53b22cf7414b`, reuse the exact-source behavior receipt instead of repeating it. If the blob differs, rerun the 18-case matrix against the live file.

After live application passes, use the existing disposable sid/package-test harness. Run the setup prelude and the shortest ordinary-user namespace consumers first: `create-directory`, `unshare-as-root-user`, and `auto-mode-as-normal-user`. Preserve the first independent result. Add QEMU-only negative subuid cases only when that environment already exists.

## Unresolved blockers

- technical: live Salsa identity/application and focused package/user-namespace execution;
- compatibility: confirm the live package-test ordinary user remains an account name at the current base;
- overlap: repeat public issue/MR search immediately before any authorization request;
- environment: Salsa DNS unavailable from the current execution container;
- delivery: controlled Salsa fork/branch absent;
- patch metadata: replace the internal placeholder author before any authorized upstream candidate branch;
- authority: external contact remains unauthorized.

## Files to read first

1. `README.md`
2. `TESTS.md`
3. `artifacts/2026-08-01-exact-imported-source-gate.md`
4. `SOURCE_MAP.md`
5. `DEEP_DIVE.md`
6. `DECISIONS.md`
7. issue #80, PR #92, and PR #291
8. PR #252 only for zero-fuzz failure history

## External-contact state

`false; none occurred`. No upstream issue, merge request, fork, branch, email, comment, review, reaction, or other public action was created.

## Do not repeat

- do not rerun the exact imported-source matrix while both baseline blob `9f4eda...` and patch SHA-256 `fc9c0c...` remain unchanged;
- do not restore PR #215, #218, #225, or #252 as the canonical carrier;
- do not remove `cut -s` without a replacement malformed-row policy and executable discriminator;
- do not accept fuzzy or whitespace-error patch application;
- do not combine this unit with runtime numeric UID/GID support, the `dev-ptmx` dependency fix, or the broad sid harness;
- do not treat the exact imported-source result as proof of an unread live Salsa head;
- do not create a fork, upstream branch, issue, merge request, email, comment, review, or reaction without explicit authorization.
