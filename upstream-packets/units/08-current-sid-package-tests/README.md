# Unit 08 — mmdebstrap package tests: current-sid phase-correct execution

State: `ACTIVE`  
Priority-zero issue: #397, unit 08  
Worker or variant: `primary composition`  
Linux Fieldwork branch: `upstream/unit-08-current-sid-package-tests`  
Internal execution carrier: draft PR #405  
External contact authorized: `false`

## TL;DR

Four upstream-facing package-test corrections are retained as an ordered series:

1. accept Deb822 source entries by rooting raw output paths before `exploded_list()`;
2. use `/usr/bin/mmdebstrap` for stable execution after directory changes;
3. deliver process-group SIGINT with syntax accepted by current Debian sid;
4. run `root-without-cap-sys-admin` in a hook-free hard phase with immediate `create-directory` production and later broad-phase regeneration.

Linux Fieldwork-only proxies, workflows, artifact collectors, generic signal probes, and guard harnesses are excluded from the upstream series.

The executable base is Debian mmdebstrap `debian/1.5.7-3` at canonical Salsa commit `6fde999741f4fe1e7bf38079acf29432ef87a35e`. Historical real-sid run 999 cleared the phase-local producer/consumer repair and reached the independent `chrootless` directory-mtime result after 154 completed tests.

The exact ordered-series gate passed through draft Linux Fieldwork PR #405, workflow `30690576566` / 1145. It validated four patch files and seven hunks, applied the series twice with zero fuzz allowed, checked transformed Python and shell syntax, verified deterministic receipts/digests and source immutability, and passed the complete 439-test Linux Fieldwork suite.

A controlled GitHub repository now exists at `teamleaderleo/mmdebstrap`, but it is not yet an exact canonical delivery fork. Its `master` head is `574048f2a720057b75e56622003932f344dc700a`, canonical Salsa commit `6fde999741f4fe1e7bf38079acf29432ef87a35e` is absent from its history, and its commits reflect a separate downstream import/update lineage. Do not base the candidate on that `master` until it is synced or replaced with an exact current-Salsa branch.

## Accomplished behavior

The package suite processes current Deb822 source paragraphs, invokes the installed mmdebstrap binary through a stable absolute path, interrupts the complete customize-hook process group with current-sid-compatible syntax, executes `root-without-cap-sys-admin` without mount-dependent APT hooks, creates its archive baseline immediately beforehand, and recreates the broad baseline under the broad hook configuration.

## Scope

### Included

- `debian/tests/sourcesfilter`: support Deb822 entries through `exploded_list()` while rooting raw output file paths first.
- `debian/tests/testsuite`: use `/usr/bin/mmdebstrap` for the broad installed-package command.
- `tests/sigint-during-customize-hook`: use the status-zero dash builtin spelling proven on current sid.
- `coverage.txt`, `coverage.py`, and `debian/tests/testsuite`: add the hook-free hard class, prepend `create-directory`, preserve ordinary failure, map timeout 124 to 77, and allow broad producer regeneration.
- `tests/test_upstream_packet_unit_08_current_sid_package_tests.py`: execute and rerun the complete distilled series against fresh imported-source copies.

### Excluded

- the formatted installed-command proxy and every proxy regression;
- disposable-container workflow activation, artifact capture, checkout receipts, bug-report capture, and phase-reordering tools;
- generic process-group probe and selector machinery from PR #326;
- predecessor Linux Fieldwork patch-application guards and synthetic shell fakes;
- the independent `chrootless` directory-mtime policy owned by #380.

### Split boundary

The four patches stay ordered in one package-test submission because they remove sequential current-sid blockers from the same Debian autopkgtest entry point. The `chrootless` timestamp result begins after this series clears and remains a separate source-policy unit.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://salsa.debian.org/debian/mmdebstrap.git` |
| Intended base branch | `master`; exact live head still requires fetch |
| Executed upstream base | tag `debian/1.5.7-3`; commit `6fde999741f4fe1e7bf38079acf29432ef87a35e` |
| Controlled repository | `https://github.com/teamleaderleo/mmdebstrap` |
| Controlled repository default branch | `master` at `574048f2a720057b75e56622003932f344dc700a` during the 2026-08-01 check |
| Fork qualification | `CONTROLLED REPOSITORY EXISTS; EXACT CANONICAL SYNC PENDING` |
| Candidate source branch | absent; create only from a verified exact Salsa commit |
| Candidate technical state | `DISTILLED SERIES GATE PASSED; LIVE REBASE PENDING` |
| Linux Fieldwork branch | `upstream/unit-08-current-sid-package-tests` |
| Series-gate source commit | `7782872ae2f731a27ed672df3a37b1d3b1581aa4` |
| Exact gate run | PR #405; workflow `30690576566` / 1145; tested head `a361f91f1b9cc3167baad5fbd6c61bbee546a10e`; generated merge `4c5abe5e3777cfa57a5d1551e1975a8d769a8814` |
| Imported/local source identity | `upstream/mmdebstrap/.linux-fieldwork-source.json`; imported 2026-07-30 |
| Patch or series path | `upstream-packets/units/08-current-sid-package-tests/patches/series` |
| Proposed destination | Debian/mmdebstrap Salsa project |
| Delivery method | `GitLab/Salsa fork and merge request`, pending authorization and exact fork setup |

## Canonical links

- Priority-zero unit: #397 unit 08
- Canonical history: #119/PR #72, #153/PR #171, #320/PR #326, #350, #357, PRs #354 and #359
- Clean current-main execution carrier: PR #361
- Internal exact-series execution carrier: draft PR #405
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream merge-request draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- Deb822 correction reached real sid package execution in the broad carrier.
- Current-sid signal selection found status-zero whole-group spellings; the retained package patch uses the dash builtin.
- Run 974 executed `create-directory` followed by `root-without-cap-sys-admin`; both passed and exposed phase leakage into broad consumers.
- Run 999 executed the focused producer/consumer and later broad producer successfully, completed 154 tests, and first failed independently at `chrootless` directory mtimes.
- PR #405 run `30690576566` validated four patches/seven hunks and passed `test_series_applies_exactly_and_reruns_cleanly`.
- The same run retained 439 of 462 discovered tests after exact inherited-duplicate removal, ran all 439 in 166.008 seconds, and finished `OK`.
- Compile and shell/help checks passed; hosted-runner cleanup completed.
- The controlled GitHub repository identity and its non-canonical current history were checked explicitly.

### Yet to be demonstrated

- exact current Salsa `master` identity and overlap state;
- an exact canonical branch in the controlled repository;
- zero-fuzz/zero-offset application on that refreshed head;
- focused upstream-native execution on the refreshed series;
- a current sid run from the exact upstream-facing series without proxy or evidence machinery.

### Compatibility boundary

- Signal syntax evidence is current Debian sid/Linux behavior, not a cross-platform shell claim.
- The phase scheduler is bounded to one hook-free consumer with exact prerequisite `create-directory`.
- Status 1 and 2 remain package-test failures; GNU timeout status 124 maps to autopkgtest skip status 77.
- The broad command path assumes the Debian package installs mmdebstrap at `/usr/bin/mmdebstrap`.
- The existing GitHub repository is controlled but must not be treated as canonical ancestry until synced and compared.

## Candidate organization

1. `0001-tests-sourcesfilter-accept-deb822.patch`
2. `0002-tests-use-absolute-installed-mmdebstrap.patch`
3. `0003-tests-use-current-sid-process-group-sigint.patch`
4. `0004-tests-run-capability-case-in-phase-local-hook-free-pass.patch`

The order follows the historical first-failure sequence and keeps each behavior independently reviewable inside one merge request.

## Current disposition

`ACTIVE` — exact imported-base application and rerun are green. The controlled repository exists, while exact canonical synchronization, live Salsa overlap review, focused upstream-native execution, and an exact current-sid package run remain incomplete.

## Next technical action

Fetch current Salsa `master` and record its exact commit. Compare that source to `teamleaderleo/mmdebstrap` rather than assuming fork ancestry. Create a candidate branch in the controlled repository only from the verified canonical commit, reapply the series with zero fuzz/offset, and rerun the distilled-series gate before current-sid package execution.

## Authority

Internal repository reads, branch work, patch composition, testing, review, draft preparation, draft Linux Fieldwork PR #405, controlled-fork inspection, and issue checkpoints are authorized. No external issue, merge request, email, comment, review, or other public contact has been authorized or made for unit 08.
