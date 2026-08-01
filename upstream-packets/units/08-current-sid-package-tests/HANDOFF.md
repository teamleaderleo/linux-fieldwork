# Current handoff

Updated: `2026-08-01 08:05 UTC`  
Worker or variant: `primary composition`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-08-current-sid-package-tests` |
| Linux Fieldwork technical head before this handoff update | `111ccf6c7d8177b1a990cded598287e90d07765d` |
| Linux Fieldwork final branch head | commit containing this `HANDOFF.md`; #397 checkpoint records the returned SHA |
| Internal execution carrier | draft PR #405; do not merge while unit remains `ACTIVE` |
| Upstream base repository/branch | `https://salsa.debian.org/debian/mmdebstrap.git`; intended `master` |
| Executed source base | tag `debian/1.5.7-3`; commit `6fde999741f4fe1e7bf38079acf29432ef87a35e` |
| Candidate fork/branch | `NEEDS FORK`; packet patch series only |
| Candidate technical state | `DISTILLED SERIES GATE PASSED; LIVE REBASE PENDING` |
| Patch or series | `upstream-packets/units/08-current-sid-package-tests/patches/series` |
| Complete-series gate | `tests/test_upstream_packet_unit_08_current_sid_package_tests.py` |
| Gate source commit | `7782872ae2f731a27ed672df3a37b1d3b1581aa4` |
| Exact gate workflow | PR #405; `Linux Fieldwork CI` run `30690576566` / 1145 |
| Candidate head tested | `a361f91f1b9cc3167baad5fbd6c61bbee546a10e` |
| Generated merge tested | `4c5abe5e3777cfa57a5d1551e1975a8d769a8814` |
| Exact job | `lab-tools`, `91344449950`, success |
| Latest real sid package run | PR #361 workflow `30640356619` / 999; artifact `8798679560`; ZIP SHA-256 `50d8ab7a20cb241ff9821b35329508ecdb0c58cbd3dec348c18d68d1dfe7a244` |

## Current bounded claim

Four upstream package-test corrections are retained as one ordered series against exact Debian mmdebstrap revision `debian/1.5.7-3` / `6fde999741f4fe1e7bf38079acf29432ef87a35e`:

1. accept Deb822 source entries by rooting raw output paths before `exploded_list()`;
2. use `/usr/bin/mmdebstrap` for stable execution after directory changes;
3. deliver process-group SIGINT with current-sid-compatible dash builtin syntax;
4. run `root-without-cap-sys-admin` in a hook-free hard phase with immediate `create-directory` production and later broad-phase regeneration.

Historical current-sid integration proves the selected Deb822 handling, signal spelling, focused producer/consumer order, and broad fixture regeneration reached the next independent `chrootless` result. The exact distilled series now also applies and reruns cleanly under Linux Fieldwork CI. The remaining technical boundary is current live Salsa `master`, followed by focused upstream-native and current-sid package execution.

## Work completed in this pass

- re-read issue #397 and the packet workflow instructions;
- confirmed the unit branch was 19 commits ahead of `main` with no divergence at the start of the pass;
- opened draft internal Linux Fieldwork PR #405 solely as an execution carrier;
- triggered `Linux Fieldwork CI` run `30690576566` / 1145 against candidate head `a361f91f1b9cc3167baad5fbd6c61bbee546a10e`;
- confirmed generated merge `4c5abe5e3777cfa57a5d1551e1975a8d769a8814` was checked out;
- validated four patch carriers and seven unified-diff hunks;
- compiled repository Python tools/tests;
- executed the complete Linux Fieldwork unit-test suite;
- observed `test_series_applies_exactly_and_reruns_cleanly ... ok`;
- observed 439 tests run in 166.008 seconds with final result `OK`;
- completed repository shell syntax and command-help checks;
- recorded exact run identities and interpretation in `TESTS.md` and `README.md`;
- made no Debian, Salsa, mmdebstrap, email, review, or other public contact.

## Exact distinguishing evidence

```text
validated 4 patch file(s) and 7 hunk(s)
fieldwork discovery retained 439 of 462 tests; removed 23 exact inherited duplicate(s)
test_series_applies_exactly_and_reruns_cleanly (test_upstream_packet_unit_08_current_sid_package_tests.Unit08CurrentSidPackageTestsSeriesTest.test_series_applies_exactly_and_reruns_cleanly) ... ok
Ran 439 tests in 166.008s
OK
```

The passing gate proves, through its assertions, that:

- the expected four-patch order was used;
- two fresh applications returned zero;
- no receipt contained `fuzz` or `offset`;
- every expected patched path appeared;
- transformed Python and shell files parsed;
- candidate digests and receipts were identical across both applications;
- the five imported-source files retained their original digests;
- both temporary trees were released before test completion.

## Gates completed

- all directly linked unit-08 carrier history read and classified;
- exact imported base identified;
- upstream-facing four-patch boundary selected and LF-only machinery excluded;
- complete source ownership and imported-base diff review;
- predecessor Deb822, signal, hook-free scheduling, producer/consumer, and broad-regeneration evidence retained;
- exact four-patch application and immediate rerun on a full hosted checkout;
- patch grammar validation, Python compilation, shell parsing, source immutability, and deterministic receipt/digest checks;
- complete Linux Fieldwork suite and cleanup on exact candidate head through PR #405.

## Gates still open

- fetch current Salsa `master` and record its exact commit;
- search active upstream overlap for each of the four corrections;
- reapply or rebase the series on that exact commit with zero fuzz and zero offset;
- rerun the exact distilled-series gate against the refreshed source;
- run focused upstream-native Deb822, direct command-path, SIGINT, focused-pair, and broad-regeneration tests;
- run the current sid Debian package tests from the exact upstream-facing series without LF proxy/evidence machinery;
- review the final exact upstream diff after the live rebase;
- obtain explicit authorization before creating a Salsa fork or merge request.

## Red or neutral runs classified

- PR #72 Deb822 assertion: package-test compatibility defect, repaired by patch 0001.
- PR #72 command loss after `chdir`: disposable relative-path defect, distilled to patch 0002.
- procps long-form signal rejection: current-sid command compatibility defect, repaired by patch 0003.
- capability-case mount failure: hook contradiction, repaired by patch 0004.
- run 939 missing `tar1.txt`: focused fixture prerequisite, repaired by explicit producer prefix.
- run 974 broad archive mismatch: phase-stale baseline, repaired by broad producer regeneration.
- run 999 `chrootless` directory mtimes: independent later source-policy result owned by #380.

## Cleanup state

The successful hosted job completed post-checkout cleanup and orphan-process cleanup. The series gate released both temporary source trees and verified the imported source remained unchanged. No local package installation, mount, socket, container, long-running process, or source-tree mutation survives this pass.

GitHub intentionally retains the unit branch, draft internal PR #405, packet, patches, test, commits, workflow logs, and issue coordination comments.

## First incomplete step

Obtain the exact current commit for `https://salsa.debian.org/debian/mmdebstrap.git` branch `master`, then perform an overlap review and zero-fuzz/zero-offset reapplication of the four-patch series.

## Next safe action

From a full checkout with network access to Salsa:

```sh
set -eu
git clone --filter=blob:none https://salsa.debian.org/debian/mmdebstrap.git /tmp/mmdebstrap-unit08-upstream
cd /tmp/mmdebstrap-unit08-upstream
git switch master
git pull --ff-only
printf 'upstream-master=%s\n' "$(git rev-parse HEAD)"
```

Record the exact commit before changing files. Search the current tree and recent history for equivalent Deb822, `/usr/bin/mmdebstrap`, process-group SIGINT, and hook-free hard-phase changes. If none supersede the series, apply the four packet patches in order with `patch --batch --forward --fuzz=0 -p1`, capture complete receipts, run syntax checks, and rerun the packet gate against a refreshed imported source snapshot.

Do not open a Salsa fork or merge request during that work without explicit authorization.

## Unresolved blockers

- overlap: current Salsa `master` exact identity and equivalent-work search remain incomplete;
- execution: focused upstream-native and exact current-sid package runs remain incomplete;
- compatibility: direct `/usr/bin/mmdebstrap` has strong historical rationale and exact imported-base application proof, but still needs package execution on the refreshed live head;
- environment/tooling: this session executed the repository gate through GitHub Actions but did not materialize the live Salsa repository;
- authority: Salsa fork/MR creation and every public upstream action require explicit authorization.

## Files to read first

1. `README.md`
2. `TESTS.md`
3. `SOURCE_MAP.md`
4. `DEEP_DIVE.md`
5. `DECISIONS.md`
6. `tests/test_upstream_packet_unit_08_current_sid_package_tests.py`
7. issue #397 unit 08, draft PR #405, PR #359, and PR #361

## External-contact state

`false; none occurred`. Draft PR #405 and issue #397 comments are internal Linux Fieldwork coordination. The only outward-looking text remains unpublished in `UPSTREAM_ISSUE.md` and `UPSTREAM_PR.md`.

## Do not repeat

- do not rerun the imported-base gate merely to prove the already-recorded PR #405 result;
- do not revive the relative formatted installed-command proxy as upstream source;
- do not move the capability consumer into the soft phase that maps ordinary failures to 77;
- do not mark `create-directory` hook-free-only, which starves broad baseline regeneration;
- do not rerun the full sid matrix solely for run-999 `chrootless`; #380 owns that result;
- do not treat PR #72 as the delivery carrier; PR #361 preserves clean integration evidence;
- do not claim current Salsa `master` from the package tag without a fresh fetch;
- do not merge draft PR #405 while the packet remains `ACTIVE`;
- do not contact Debian or mmdebstrap upstream without explicit authorization.
