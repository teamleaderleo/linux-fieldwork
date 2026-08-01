# Current handoff

Updated: `2026-08-01 16:09 +08:00`  
Worker or variant: `GPT-5.6 Thinking`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-19-tarfilter-pax-idshift` |
| Linux Fieldwork parent head before this handoff commit | `ee653d18a1ad23e46d3a0738e0003674b36eca4d` |
| Linux Fieldwork final head | the commit containing this `HANDOFF.md`; exact SHA is recorded in the #397 checkpoint |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Canonical repository head observed | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Canonical tarfilter file commit | `87b9b385b38795c58bc13ffb33b8724bed27f7a0` |
| Controlled repository | `teamleaderleo/mmdebstrap` |
| Controlled repository classification | public GitHub package-source mirror; not canonical Forgejo commit lineage |
| Controlled default branch/head | `master` at `574048f2a720057b75e56622003932f344dc700a` |
| Candidate branch | `linux-fieldwork/unit-19-tarfilter-pax-idshift` |
| Candidate source commit | `1cd61501e18b5ffd861eceac9b70b1284fb0a0b6` |
| Candidate head | `07e89c68dbed198b04bb60aeb1947433f6ead0b0` |
| Candidate compare state | ahead by `2`, behind by `0` relative to mirror `master` |
| Candidate changed paths | `tarfilter`; `tests/tarfilter-idshift` |
| Candidate attached statuses | none observed |
| Base tarfilter blob | `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Base native-test blob | `6956e76aca153147d3a8a6668196d913ebc8a49e` |
| Candidate tarfilter blob | `8c40acebba1734a26140790cfc59b72c62a98971` |
| Candidate native-test blob | `cd749c063e754c4503771988fa1e5802076db0b0` |
| Source patch | `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch` |
| Source patch SHA-256 | `b86da5f6a2f2f1757b5b3fc0e32ebeabeeadbdebebb4cdc1961d3d1ff5eb3303` |
| Native test patch | `patches/0002-tests-cover-pax-idshift.patch` |
| Native test patch SHA-256 | `ce5442b10be51b900a86947f25046ff39392fd2e9e9a776e982eabe79a177edc` |
| Prior reviewed candidate | Linux Fieldwork PR #78 head `8d6443626e4338b180ec0533969bfe4d32b20d52` |
| Prior CI receipt | Linux Fieldwork run `30538012863`, success |

## Current bounded claim

Current mmdebstrap `tarfilter` retains PAX `uid` and `gid` strings after `--idshift` changes the numeric fields. Those strings override shifted large IDs during output serialization. Removing only the two stale numeric PAX keys after successful validation and shifting corrects large-ID output while preserving ordinary header behavior, unrelated PAX metadata, payloads, and inverse-shift ownership.

The native owner is `tests/tarfilter-idshift`. The retained extension has an executable losing path: the baseline model exits `1` with `large ownership was not shifted`; the candidate model exits `0`.

A controlled candidate branch is now materialized and verified. It changes only the expected two files, and both target files on the mirror base exactly match the packet/import blobs. The mirror's commit lineage is different from canonical Forgejo, so canonical-lineage preparation remains mandatory before upstream authorization.

## Work completed in this continuation

- located the user's new repository `teamleaderleo/mmdebstrap` through the connected GitHub installation;
- verified owner/admin/push access, public visibility, and default branch `master`;
- identified mirror base head `574048f2a720057b75e56622003932f344dc700a`;
- classified the repository as a package-source mirror rather than the canonical Forgejo commit lineage;
- verified exact base blob equality for both target files:
  - `tarfilter`: `ad776167a8473d5d15dbe22e850f4f6db35cf278`;
  - `tests/tarfilter-idshift`: `6956e76aca153147d3a8a6668196d913ebc8a49e`;
- created branch `linux-fieldwork/unit-19-tarfilter-pax-idshift` from mirror `master`;
- materialized the two-line source correction in commit `1cd61501e18b5ffd861eceac9b70b1284fb0a0b6`;
- materialized the native PAX-large regression in commit `07e89c68dbed198b04bb60aeb1947433f6ead0b0`;
- verified candidate source blob `8c40acebba1734a26140790cfc59b72c62a98971` contains the two expected `pax_headers.pop()` calls;
- verified candidate native-test blob `cd749c063e754c4503771988fa1e5802076db0b0` contains the forced-large fixture, ordinary control, regenerated-key checks, metadata/payload preservation, and inverse shift;
- compared mirror `master` against candidate head: ahead `2`, behind `0`, exactly two changed paths;
- checked candidate commit statuses: none attached;
- created `FORK_MATERIALIZATION.md` with exact evidence and lineage limitations;
- updated `README.md`, `SOURCE_MAP.md`, and `UPSTREAM_PR.md` to distinguish controlled review materialization from canonical submission readiness;
- preserved the no-contact boundary.

## Candidate branch fence

```text
base: 574048f2a720057b75e56622003932f344dc700a
head: 07e89c68dbed198b04bb60aeb1947433f6ead0b0
status: ahead
commits: 2
behind: 0
paths:
  tarfilter                    +2/-0
  tests/tarfilter-idshift      +85/-2
```

No other paths changed.

## Controlled repository caveat

The GitHub repository's history contains package-source import commits and does not share the canonical Forgejo SHA lineage. The target files match exactly, making the branch suitable for code review and project test execution. It does not prove whole-tree equality with canonical head `77ec9be5417ee44c96343d2347145585da1b1f94` and must not be represented as an exact canonical rebase.

Before submission, fetch/import canonical history into a controlled repository and rebuild or rebase the same two-file change onto the current reviewed canonical head.

## Project-native focused gate

```sh
black --check ./tarfilter
./make_mirror.sh
CMD=./mmdebstrap ./coverage.sh tarfilter-idshift
CMD=./mmdebstrap ./coverage.sh tarfilter-idshift
```

Requirements:

- QEMU must be enabled so `tarfilter-idshift` actually runs;
- `coverage.sh` checks `tarfilter` with Black;
- `coverage.py` checks rendered `shared/test.sh` with the project's ShellCheck and shfmt settings;
- the second named run supplies the immediate-rerun receipt;
- a Debian autopkgtest using `HAVE_QEMU=no` skips this test and is not sufficient.

## Gates completed

- prior exact imported-source regression: PASS;
- prior independent exact-head review: ACCEPT;
- prior Linux Fieldwork CI: PASS, run `30538012863`;
- packet semantic probe: PASS twice with identical output;
- current canonical source persistence review: complete;
- indexed overlap refresh: complete as of 2026-08-01;
- imported native test-owner review: complete;
- native detector losing/winning model run: expected FAIL/PASS;
- project instruction and gate mapping: complete;
- controlled repository discovery and permission verification: complete;
- controlled branch creation: complete;
- two-file materialization: complete;
- base target-blob equality check: complete;
- candidate changed-file fence review: complete;
- candidate attached-status check: complete; none present.

## Gates not completed

- canonical-lineage branch materialization or rebase;
- complete native baseline run on an unmodified current canonical checkout;
- Black on the materialized candidate;
- generated-test ShellCheck and shfmt;
- QEMU-backed named test run;
- immediate named-test rerun;
- broader project gates, package build, or package autopkgtest;
- current overlap recheck immediately before authorization.

## Failure and neutral-result classification

- early PR #78 revisions: patch-packaging failures, superseded;
- native detector baseline model: intended product failure, status `1`, exact diagnostic `large ownership was not shifted`;
- prior canonical clone attempts: execution-environment DNS failures with zero source mutation;
- candidate commit status query: neutral, no statuses attached;
- controlled mirror lineage mismatch: preparation limitation, not a source-content mismatch for the two target files.

## Complete retained packet

- `README.md`
- `SOURCE_MAP.md`
- `DEEP_DIVE.md`
- `TESTS.md`
- `PROJECT_INSTRUCTIONS.md`
- `FORK_MATERIALIZATION.md`
- `DECISIONS.md`
- `UPSTREAM_ISSUE.md`
- `UPSTREAM_PR.md`
- `HANDOFF.md`
- `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch`
- `patches/0002-tests-cover-pax-idshift.patch`
- `scripts/test_pax_idshift.py`

## First incomplete step

Use a QEMU-capable environment to run the exact project-native focused gate on controlled candidate head `07e89c68dbed198b04bb60aeb1947433f6ead0b0`, while keeping the result classified as mirror-branch evidence. In parallel or immediately afterward, import canonical Forgejo history and rebuild the candidate on the current reviewed canonical head.

## Next commands

For controlled-branch test execution:

```sh
git clone https://github.com/teamleaderleo/mmdebstrap.git
cd mmdebstrap
git checkout 07e89c68dbed198b04bb60aeb1947433f6ead0b0

git diff --check 574048f2a720057b75e56622003932f344dc700a..HEAD
git diff 574048f2a720057b75e56622003932f344dc700a..HEAD -- tarfilter tests/tarfilter-idshift
black --check ./tarfilter
./make_mirror.sh
CMD=./mmdebstrap ./coverage.sh tarfilter-idshift
CMD=./mmdebstrap ./coverage.sh tarfilter-idshift
```

For canonical-lineage preparation:

```sh
git remote add canonical https://gitlab.mister-muffin.de/josch/mmdebstrap
git fetch canonical
# Resolve the current canonical default-branch head and record its exact SHA.
git checkout -b linux-fieldwork/unit-19-tarfilter-pax-idshift-canonical <canonical-head>
# Reapply the two-line source correction and native test extension.
```

Do not force-move the controlled mirror branch to an unrelated canonical commit without first confirming repository object compatibility and preserving the reviewed mirror candidate.

## Cleanup state

This pass used GitHub repository and contents operations only. No local service, socket, mount, container, package installation, mirror generation, or QEMU process was started. The controlled branch and packet files are intentional retained state. No disposable runtime artifacts survive.

## Unresolved blockers

- environment: no QEMU-backed project test receipt yet;
- tooling: no Black, ShellCheck, or shfmt receipt yet;
- lineage: controlled mirror is not canonical Forgejo history;
- validation: complete native exact-head run and rerun pending;
- overlap: recheck required immediately before authorization;
- authority: canonical upstream contact remains unauthorized.

## Files to read first

1. `README.md`
2. `HANDOFF.md`
3. `FORK_MATERIALIZATION.md`
4. `PROJECT_INSTRUCTIONS.md`
5. `TESTS.md`
6. `SOURCE_MAP.md`
7. `UPSTREAM_PR.md`
8. the controlled branch compare at head `07e89c68dbed198b04bb60aeb1947433f6ead0b0`

## External-contact state

`false; none occurred`. Creating and updating the user's controlled fork branch is internal preparation. No canonical upstream issue, pull request, comment, email, review, reaction, or other public contact occurred.

## Do not repeat

- do not treat the GitHub mirror SHA as a canonical Forgejo SHA;
- do not claim whole-tree canonical equality from two matching target blobs;
- do not open a canonical PR without explicit authorization;
- do not accept a green `HAVE_QEMU=no` package test as evidence that `tarfilter-idshift` ran;
- do not clear all PAX metadata;
- do not assign numeric PAX strings directly for ordinary IDs;
- do not create a second native test file;
- do not fold units 15, 18, 20, 21, 22, or 16 into this candidate.