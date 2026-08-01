# Current handoff

Updated: `2026-08-01 08:12 +08`  
Worker or variant: `GPT-5.6 Thinking`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-18-tarfilter-no-option-passthrough` |
| Linux Fieldwork head before this handoff commit | `ec4efdd61125465c2c393b203976c28720a934b6` |
| Linux Fieldwork final head | commit containing this `HANDOFF.md`; exact SHA is posted in the #397 `UNIT CHECKPOINT` |
| Source/test change head | `748f95cf0470d2c9ba96b8432c3cac7d2267aaeb` |
| Upstream base repository/branch | `https://gitlab.mister-muffin.de/josch/mmdebstrap`, `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Current upstream tarfilter commit | `87b9b385b38795c58bc13ffb33b8724bed27f7a0` |
| Imported source blob | `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Candidate fork/branch | `NEEDS FORK` |
| Candidate head | retained patch plus Linux Fieldwork test head `748f95cf0470d2c9ba96b8432c3cac7d2267aaeb` |
| Linux Fieldwork patch | `investigations/tarfilter-no-option-passthrough/tarfilter-no-option-passthrough.patch` |
| Upstream-shaped patch | `patches/0001-tarfilter-restore-no-option-passthrough.patch` |
| Owning issue/PR | #29 / PR #46; priority-zero #397 unit 18 |
| Latest historical workflow | Linux Fieldwork CI `30534506273`, PASS on PR #46 head `8c8f45872e6eb2b4ea770e5753c6dc66347c8f56` |

## Current bounded claim

The current mmdebstrap `tarfilter` no-option guard is unreachable because `strip_components` always exists. The refreshed candidate cleanly selects the existing byte-copy path when all six modifying operation categories are inactive, preserves explicit numeric zero as no-operation, and keeps every active operation on the rewrite path.

## Work completed in this pass

- read #397, packet workflow files, #29, #27, PRs #46, #33, #23, the investigation, reusable note, patch, regression, LF-14 sparse evidence pointers, and current upstream source;
- claimed unit 18 and created the canonical branch;
- verified current upstream repository head, tarfilter file commit, parser options, and unchanged guard;
- found the retained PR #46 patch applied with fuzz 2;
- regenerated the patch from exact blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`;
- enforced `patch --fuzz=0` in the regression;
- expanded active-operation proof to path, PAX, type, strip, transform, and ID shift;
- retained an upstream-shaped patch in the packet;
- executed the local baseline/candidate matrix and compilation checks;
- wrote the complete packet and upstream drafts;
- removed all `/tmp` test copies.

## Changed paths

- `investigations/tarfilter-no-option-passthrough/tarfilter-no-option-passthrough.patch`
- `tests/test_tarfilter_no_option_passthrough.py`
- `upstream-packets/units/18-tarfilter-no-option-passthrough/README.md`
- `upstream-packets/units/18-tarfilter-no-option-passthrough/SOURCE_MAP.md`
- `upstream-packets/units/18-tarfilter-no-option-passthrough/DEEP_DIVE.md`
- `upstream-packets/units/18-tarfilter-no-option-passthrough/TESTS.md`
- `upstream-packets/units/18-tarfilter-no-option-passthrough/DECISIONS.md`
- `upstream-packets/units/18-tarfilter-no-option-passthrough/UPSTREAM_ISSUE.md`
- `upstream-packets/units/18-tarfilter-no-option-passthrough/UPSTREAM_PR.md`
- `upstream-packets/units/18-tarfilter-no-option-passthrough/HANDOFF.md`
- `upstream-packets/units/18-tarfilter-no-option-passthrough/patches/0001-tarfilter-restore-no-option-passthrough.patch`

## Distinguishing observations

- The code correction already accepted in PR #46 was technically sound.
- Its retained patch carrier failed the priority-zero clean-application requirement: `Hunk #1 succeeded at 201 with fuzz 2 (offset -1 lines)`.
- The regenerated hunk applies to the exact source with `--fuzz=0` and compiles.
- The earlier focused test directly proved transform and ID shift; the committed regression now proves every operation category named by #397.
- Current upstream still displays the same source guard at tarfilter commit `87b9b385b38795c58bc13ffb33b8724bed27f7a0`.

## Gates completed

- canonical carrier read and ownership split;
- current upstream source identity refresh;
- clean zero-fuzz Linux Fieldwork patch application;
- clean zero-fuzz upstream-shaped patch application;
- Python compilation of candidate;
- baseline gzip negative control;
- no-operation byte identity for plain, gzip, bzip2, xz, GNU sparse, strip zero, and ID-shift zero;
- active path/PAX/type/strip/transform/ID-shift result matrix;
- local cleanup.

## Red or neutral runs classified

- Historical PR #46 first hosted run had a repository-wide optional shell-help tail-status failure after unit tests passed. The repaired exact-head run `30534506273` passed.
- PR #33's GitGuardian finding was a documented false positive caused by a synthetic `.secret` pathname.
- The old patch's fuzzy application is classified as a packaging defect and is superseded by the refreshed hunk.

## Cleanup state

No processes, sockets, mounts, containers, or generated repository files remain. `/tmp/u18repo`, `/tmp/u18apply`, `/tmp/u18-upstream-apply`, and `/tmp/u18-upstream.patch` were removed. Intentional retained state is committed on the unit branch.

## First incomplete step

Execute the committed focused regression from a clean checkout of `upstream/unit-18-tarfilter-no-option-passthrough`.

## Next safe action

```text
git switch upstream/unit-18-tarfilter-no-option-passthrough
python3 -m unittest -v tests.test_tarfilter_no_option_passthrough
python3 -m tools.run_fieldwork_unittests --verbosity 2
```

After both pass, record exact output in `TESTS.md`, review `git diff main...HEAD`, and refresh the canonical upstream issue/pull-request overlap search.

## Unresolved blockers

- technical: exact committed branch test run pending;
- compatibility: no current concern; final complete-diff review pending;
- overlap: current upstream issue/pull-request title and body search pending immediately before readiness;
- environment or tooling: this session's shell had no network DNS, so the branch could not be cloned into the local container; GitHub connector writes succeeded;
- authority: external contact remains unauthorized; controlled upstream fork is absent.

## Files to read first

1. `README.md`
2. `TESTS.md`
3. `DEEP_DIVE.md`
4. `SOURCE_MAP.md`
5. `DECISIONS.md`
6. #29 and PR #46

## External-contact state

`false; none occurred`. The issue and pull-request text are drafts only.

## Do not repeat

- Do not revive #27 as a separate carrier; #29 owns the defect.
- Do not use PR #33's combined patch as unit 18's canonical proof; PR #46 superseded it.
- Do not accept the old patch hunk merely because `patch` exits 0; it applied with fuzz 2.
- Do not bundle active sparse rewriting, dotfile/path normalization, parent retention, transform dialect work, or PAX ID-shift repair into this unit.
- Do not treat a supplied transform as no-operation based on a particular archive's member names.
- Do not contact upstream without explicit authorization.
