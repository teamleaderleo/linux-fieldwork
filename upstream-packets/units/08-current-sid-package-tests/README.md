# Unit 08 — mmdebstrap package tests: current-sid phase-correct execution

State: `ACTIVE`  
Priority-zero issue: #397, unit 08  
Worker or variant: `primary composition`  
Linux Fieldwork branch: `upstream/unit-08-current-sid-package-tests`  
External contact authorized: `false`

## TL;DR

Four upstream-facing test-suite corrections have been extracted from the carrier history into an ordered patch series. The series accepts Deb822 sources, pins behavioral execution to `/usr/bin/mmdebstrap`, uses a current-sid process-group SIGINT spelling, and runs the no-`CAP_SYS_ADMIN` consumer with a phase-local `tar1.txt` producer while allowing broad-phase regeneration. Linux Fieldwork-only proxies, workflows, artifact collectors, probes, and guard harnesses are excluded.

The current exact executable base is Debian mmdebstrap `debian/1.5.7-3` at `6fde999741f4fe1e7bf38079acf29432ef87a35e`. Historical real-sid run 999 cleared the phase-local producer/consumer repair and reached the independent `chrootless` directory-mtime result after 154 completed tests. This unit remains `ACTIVE` until the distilled series receives zero-fuzz application and focused execution on a fresh checkout, plus a live Salsa-master overlap/rebase check.

## Accomplished behavior

The package suite processes current Deb822 source paragraphs, invokes the installed mmdebstrap binary through a stable absolute path, interrupts the complete customize-hook process group with syntax accepted by current sid, executes `root-without-cap-sys-admin` without mount-dependent APT hooks, creates its archive baseline immediately beforehand, and recreates the broad baseline under the broad hook configuration.

## Why care

Each prior failure stopped the package matrix before the next independent product result: a Deb822 assertion, command loss after a directory change, procps `kill` argument rejection, a mount-dependent hook after dropping `CAP_SYS_ADMIN`, a missing `tar1.txt`, and then a stale baseline generated under the wrong hook phase. The composed corrections let the package test classify actual mmdebstrap behavior.

## Scope

### Included

- `debian/tests/sourcesfilter`: support Deb822 entries through `exploded_list()` while rooting raw output file paths first.
- `debian/tests/testsuite`: use `/usr/bin/mmdebstrap` for the broad installed-package command.
- `tests/sigint-during-customize-hook`: use the status-zero dash builtin spelling proven on current sid.
- `coverage.txt`, `coverage.py`, and `debian/tests/testsuite`: add the hook-free hard class, prepend `create-directory`, preserve ordinary failure, map timeout 124 to 77, and allow broad producer regeneration.

### Excluded

- the formatted installed-command proxy and every proxy regression;
- disposable-container workflow activation, artifact capture, checkout receipts, bug-report capture, and phase-reordering tools;
- generic process-group probe and selector machinery from PR #326;
- Linux Fieldwork patch-application guards and synthetic shell fakes;
- the independent `chrootless` directory-mtime policy owned by #380.

### Split boundary

The four patches stay ordered in one package-test submission because they remove sequential current-sid blockers from the same Debian autopkgtest entry point. The `chrootless` timestamp result begins after this series has cleared and remains a separate source-policy unit.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://salsa.debian.org/debian/mmdebstrap.git` |
| Intended base branch | `master`; executable package base currently pinned to `debian/1.5.7-3` |
| Upstream base commit | `6fde999741f4fe1e7bf38079acf29432ef87a35e` |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | patch-series packet; upstream branch absent |
| Candidate head | `PENDING EXACT SERIES GATE` |
| Linux Fieldwork branch | `upstream/unit-08-current-sid-package-tests` |
| Linux Fieldwork head | see `HANDOFF.md` |
| Imported/local source identity | `upstream/mmdebstrap/.linux-fieldwork-source.json`; imported 2026-07-30 |
| Patch or series path | `upstream-packets/units/08-current-sid-package-tests/patches/series` |
| Proposed destination | Debian/mmdebstrap Salsa project |
| Delivery method | `GitLab/Salsa fork and merge request`, pending authorization |

## Canonical links

- Priority-zero unit: #397 unit 08
- Canonical history: #119/PR #72, #153/PR #171, #320/PR #326, #350, #357, PRs #354 and #359
- Clean current-main execution carrier: PR #361
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
- Current-sid signal selection found dash builtin `kill -s INT -- -PGID` and external compact `kill -INT -- -PGID` as status-zero whole-group spellings; the retained package patch uses the dash builtin.
- Run 974 executed `create-directory` followed by `root-without-cap-sys-admin`; both passed, exposing phase leakage into broad consumers.
- Run 999 executed the focused producer/consumer and the later broad producer successfully, completed 154 tests, and first failed independently at `chrootless` directory mtimes.

### Yet to be demonstrated

- zero-fuzz, zero-offset application of this newly distilled four-patch series as a series;
- focused syntax and package-test execution on the exact distilled head;
- live overlap/rebase against current Salsa `master`;
- a current sid run from the exact upstream-facing series without the proxy or other evidence machinery.

### Compatibility boundary

- Signal syntax evidence is current Debian sid/Linux behavior, not a cross-platform shell claim.
- The phase scheduler is bounded to one hook-free consumer with exact prerequisite `create-directory`.
- Status 1 and 2 remain package-test failures; GNU timeout status 124 maps to autopkgtest skip status 77.
- The broad command path assumes the Debian package installs mmdebstrap at `/usr/bin/mmdebstrap`.

## Candidate organization

1. `0001-tests-sourcesfilter-accept-deb822.patch`
2. `0002-tests-use-absolute-installed-mmdebstrap.patch`
3. `0003-tests-use-current-sid-process-group-sigint.patch`
4. `0004-tests-run-capability-case-in-phase-local-hook-free-pass.patch`

The order follows the historical first-failure sequence and keeps each behavior independently reviewable inside one merge request.

## Current disposition

`ACTIVE` — the exact series exists, while the fresh application/focused gate and live Salsa-master refresh remain incomplete.

## Next human decision

After the exact series gate and live rebase complete, choose whether the four sequential package-test corrections should be sent as one Salsa merge request or as a short ordered series of smaller merge requests.

## Authority

Internal repository reads, branch work, patch composition, testing, review, and draft preparation are authorized. No external issue, merge request, email, comment, review, or other public contact has been authorized or made for unit 08.
