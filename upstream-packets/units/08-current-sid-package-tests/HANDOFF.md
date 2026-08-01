# Current handoff

Updated: `2026-08-01 00:11 UTC`  
Worker or variant: `primary composition`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-08-current-sid-package-tests` |
| Linux Fieldwork technical head before this handoff commit | `df59c315ea4af95d32bd01ddb6686cec475452d5` |
| Linux Fieldwork final branch head | commit containing this `HANDOFF.md`; #397 checkpoint records the returned SHA |
| Upstream base repository/branch | `https://salsa.debian.org/debian/mmdebstrap.git`; intended `master`, executable base tag `debian/1.5.7-3` |
| Upstream base commit | `6fde999741f4fe1e7bf38079acf29432ef87a35e` |
| Candidate fork/branch | `NEEDS FORK`; packet patch series only |
| Candidate head | `PENDING EXACT SERIES GATE` |
| Patch or series | `upstream-packets/units/08-current-sid-package-tests/patches/series` |
| Owning issue/PR | #397 unit 08; clean integration carrier PR #361 |
| Latest distinguishing workflow/run/artifact | PR #361 run `30640356619` / 999; artifact `8798679560`; ZIP SHA-256 `50d8ab7a20cb241ff9821b35329508ecdb0c58cbd3dec348c18d68d1dfe7a244` |

## Current bounded claim

Four upstream package-test corrections have been extracted into an ordered series against exact Debian mmdebstrap revision `debian/1.5.7-3` / `6fde999741f4fe1e7bf38079acf29432ef87a35e`. Historical current-sid integration proves the selected Deb822 handling, signal spelling, hook-free producer/consumer order, and broad-phase fixture regeneration reached the next independent result. The newly distilled direct `/usr/bin/mmdebstrap` hunk and the exact four-patch series still require fresh application and execution.

## Work completed in this pass

- read issue #397, packet workflow/index, and every direct unit-08 carrier;
- read the clean successor PR #361 and its run-999 classification;
- claimed unit 08 on #397 and created the canonical branch;
- identified the exact imported source revision and current sid package version;
- separated upstream package-test changes from LF-only reduction, workflow, probe, and evidence files;
- created an ordered four-patch series;
- documented source ownership, mechanism, failed approaches, compatibility limits, historical receipts, pending commands, and delivery decisions;
- drafted an upstream issue and Salsa merge request without publishing either;
- recorded the lack of live Salsa-tree materialization and branch-triggered CI in this environment.

## Changed paths

- `upstream-packets/units/08-current-sid-package-tests/README.md`
- `upstream-packets/units/08-current-sid-package-tests/SOURCE_MAP.md`
- `upstream-packets/units/08-current-sid-package-tests/DEEP_DIVE.md`
- `upstream-packets/units/08-current-sid-package-tests/TESTS.md`
- `upstream-packets/units/08-current-sid-package-tests/DECISIONS.md`
- `upstream-packets/units/08-current-sid-package-tests/UPSTREAM_ISSUE.md`
- `upstream-packets/units/08-current-sid-package-tests/UPSTREAM_PR.md`
- `upstream-packets/units/08-current-sid-package-tests/HANDOFF.md`
- `upstream-packets/units/08-current-sid-package-tests/patches/0001-tests-sourcesfilter-accept-deb822.patch`
- `upstream-packets/units/08-current-sid-package-tests/patches/0002-tests-use-absolute-installed-mmdebstrap.patch`
- `upstream-packets/units/08-current-sid-package-tests/patches/0003-tests-use-current-sid-process-group-sigint.patch`
- `upstream-packets/units/08-current-sid-package-tests/patches/0004-tests-run-capability-case-in-phase-local-hook-free-pass.patch`
- `upstream-packets/units/08-current-sid-package-tests/patches/series`

## Distinguishing observations

- Exploded Deb822 entries proxy their parent file path read-only; root raw file paths before calling `exploded_list()`.
- The historical installed-command proxy served reduction and changed source-preflight ownership. The upstream-facing correction is a direct stable installed path.
- Current sid accepted dash builtin `kill -s INT -- -PGID` with whole-group delivery and status 0; external long signal forms rejected the target.
- `root-without-cap-sys-admin` must run without mount-dependent hooks and retain hard failure semantics.
- `tar1.txt` belongs to an execution phase. The focused phase needs explicit producer `create-directory`; the broad phase must run the same producer again under broad hooks.
- Run 999 cleared the unit-08 phase behavior and first failed independently at `chrootless`, owned by #380.

## Gates completed

- predecessor Deb822 execution reached later package cases;
- PR #326 repository and dedicated sid signal gates passed on exact head;
- PR #359 focused scheduling/application gate passed 369 tests on its generated merge;
- PR #361 run 999 passed the focused pair and later broad producer in real sid execution;
- complete carrier/source ownership review finished for the selected four-patch boundary;
- branch contains no public upstream action and no LF-only source machinery in the candidate series.

## Red or neutral runs classified

- PR #72 early Deb822 assertion: package-test compatibility defect, repaired by patch 0001.
- PR #72 cwd-changing proxy loss: disposable carrier path defect, distilled to patch 0002.
- procps long-form signal rejection: current-sid command compatibility defect, repaired by patch 0003.
- capability-case mount failure: hook contradiction, repaired by patch 0004.
- run 939 missing `tar1.txt`: focused fixture prerequisite, repaired by explicit prefix.
- run 974 broad archive mismatch: phase-stale baseline, repaired by broad producer regeneration.
- run 999 `chrootless` directory mtimes: independent later source-policy result; routed to #380.

## Cleanup state

This pass created GitHub branch files only. No local package installation, mount, socket, container, process, or source-tree mutation survives. Historical run 999's privileged container exited and artifact upload completed. The exact series test created no temporary checkout because the runtime could not materialize the source tree.

## First incomplete step

Apply the exact four-patch series with zero fuzz and zero offset to a fresh copy of `upstream/mmdebstrap`, then compile the transformed Python files and check shell syntax. Record the complete command output, cleanup, and immediate rerun in `TESTS.md`.

## Next safe action

From a full checkout of `teamleaderleo/linux-fieldwork` on this branch, execute:

```text
set -eu
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM
repo_root=$PWD
cp -a upstream/mmdebstrap "$work/mmdebstrap"
cd "$work/mmdebstrap"
while IFS= read -r patch_name; do
    patch --batch --forward --fuzz=0 -p1 < "$repo_root/upstream-packets/units/08-current-sid-package-tests/patches/$patch_name"
done < "$repo_root/upstream-packets/units/08-current-sid-package-tests/patches/series"
python3 -m py_compile coverage.py debian/tests/sourcesfilter
sh -n debian/tests/testsuite tests/sigint-during-customize-hook
```

Then repeat from a second fresh temporary copy. Search output for `fuzz` and `offset`, update `TESTS.md`, and commit the exact receipt. After that, fetch current Salsa `master`, record its exact commit, check overlap, and reapply the series before any current-sid package run.

## Unresolved blockers

- technical: exact distilled-series application and focused tests have yet to run;
- compatibility: direct `/usr/bin/mmdebstrap` selection has historical rationale and still needs exact-head execution;
- overlap: current Salsa `master` has yet to be fetched and searched for equivalent changes;
- environment or tooling: this session could read connected GitHub and public project/package pages but could not materialize the live Salsa or repository tree for execution; branch pushes triggered no workflow;
- authority: Salsa fork/MR creation and every public upstream action require explicit authorization.

## Files to read first

1. `README.md`
2. `SOURCE_MAP.md`
3. `DEEP_DIVE.md`
4. `TESTS.md`
5. `DECISIONS.md`
6. issue #397 unit 08, PR #359, and PR #361

## External-contact state

`false; none occurred`. The only outward-looking text is stored as unpublished drafts in this packet. The #397 claim/checkpoint are internal Linux Fieldwork coordination.

## Do not repeat

- avoid reviving the relative formatted installed-command proxy as upstream source;
- avoid moving the capability consumer into the soft phase that maps ordinary failures to 77;
- avoid marking `create-directory` hook-free-only, which starves broad baseline regeneration;
- avoid rerunning the full sid matrix solely to reproduce run-999 `chrootless`; #380 owns the timestamp decision;
- avoid treating PR #72 as the live delivery carrier; PR #361 preserves clean integration evidence;
- avoid claiming current Salsa `master` from the package tag without a fresh fetch and overlap review;
- avoid contacting Debian or mmdebstrap upstream without explicit authorization.
