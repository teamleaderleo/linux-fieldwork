# Current handoff

Updated: `2026-08-01 08:09 +08:00`  
Worker or variant: `ChatGPT`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-15-tarfilter-transform-metadata` |
| Linux Fieldwork packet base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Linux Fieldwork packet commit | the commit adding this bundle; exact SHA is recorded in the unit checkpoint on #397 |
| Upstream base repository/branch | `https://gitlab.mister-muffin.de/josch/mmdebstrap`, `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Upstream tarfilter file commit | prefix `87b9b385b3`, 2024-09-13 |
| Imported source blob | `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Candidate fork/branch | `NEEDS FORK` / `NEEDS BRANCH` |
| Candidate source identity | SHA-256 `adb1a8353bcd676a8acdba4318b198539820b890e2a96016b9909d382942e42e` |
| Patch | `patches/0001-tarfilter-transform-metadata.patch`; SHA-256 `4d8cb2f180cb7798a15195c2dcfac164b409f68a18c69d507cfc624d4725703c` |
| Owning issue/PR | #397 unit 15; parent #36; canonical composition PR #68 + PR #102 |
| Latest retained gate | packet wrapper PASS; JSON SHA-256 `325db677bba5b435c45de2f09f89b2f52fd88e62137660094457623adb1e8106` |

## Current bounded claim

The regenerated unit patch applies to the exact imported/current relevant tarfilter source with GNU patch 2.8 using zero fuzz and no offsets. On Python 3.13.5 and GNU tar 1.35, the focused candidate matches GNU tar for the retained replacement, target-scope, link, PAX, and numeric occurrence matrix, extracts hard links correctly, cleans temporary state, and produces identical results on repeated runs.

## Work completed in this pass

- refreshed issue #397, the packet protocol, index, and unit-15 carrier lineage;
- continued branch `upstream/unit-15-tarfilter-transform-metadata` from current Linux Fieldwork `main`;
- confirmed current public upstream `main` and visible overlap state;
- verified the exact PR #68 and PR #102 patch identities;
- composed both historical patches with Git and recorded their offsets;
- classified GNU patch 2.8 rejection of the historical PR #68 parser hunk as a carrier/application portability result;
- regenerated one clean patch from exact baseline to composed source;
- proved clean `patch --fuzz=0` application and byte-identical candidate output;
- ran the focused GNU tar differential matrix three direct times;
- created and executed the packet-owned materialization wrapper, producing the same JSON a fourth time;
- wrote the complete packet, decisions, drafts, artifacts, and handoff.

## Changed paths

- `upstream-packets/units/15-tarfilter-transform-metadata/README.md`
- `upstream-packets/units/15-tarfilter-transform-metadata/SOURCE_MAP.md`
- `upstream-packets/units/15-tarfilter-transform-metadata/DEEP_DIVE.md`
- `upstream-packets/units/15-tarfilter-transform-metadata/TESTS.md`
- `upstream-packets/units/15-tarfilter-transform-metadata/DECISIONS.md`
- `upstream-packets/units/15-tarfilter-transform-metadata/UPSTREAM_ISSUE.md`
- `upstream-packets/units/15-tarfilter-transform-metadata/UPSTREAM_PR.md`
- `upstream-packets/units/15-tarfilter-transform-metadata/HANDOFF.md`
- `upstream-packets/units/15-tarfilter-transform-metadata/patches/0001-tarfilter-transform-metadata.patch`
- `upstream-packets/units/15-tarfilter-transform-metadata/scripts/run_matrix.py`
- `upstream-packets/units/15-tarfilter-transform-metadata/scripts/materialize_and_run.sh`
- `upstream-packets/units/15-tarfilter-transform-metadata/artifacts/*`

## Distinguishing observations

- The visible current upstream source still has the same narrow parser and name-only transform mechanism as imported blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`.
- The canonical source state is PR #68 plus PR #102; PR #48 and PR #52 retain useful history but carry superseded composition choices.
- Historical Git patches apply in order but with offsets. GNU patch 2.8 rejects the historical PR #68 parser hunk.
- A regenerated one-file patch removes that release-carrier ambiguity and applies cleanly with zero fuzz and no offsets.
- Four matrix executions produced the same SHA-256, including the packet-owned wrapper.

## Gates completed

- exact source blob check;
- historical patch blob check;
- historical `git apply --check` and composition;
- regenerated clean patch application;
- baseline replacement negative controls;
- GNU tar replacement differential;
- target-scope differential;
- hard-link extraction and inode identity;
- long PAX path/linkpath regeneration;
- numeric occurrence differential and predecessor control;
- non-ASCII numeral rejection;
- cleanup and immediate reruns;
- public overlap recheck.

## Red or neutral runs classified

- GNU patch 2.8 historical PR #68 hunk failure: retained patch application portability, not candidate product behavior.
- Full upstream-native gates: unexecuted, neither pass nor fail.
- Controlled fork/branch: absent by design, awaiting repository-owner action.

## Cleanup state

All temporary materialization directories were removed. No retained process, socket, mount, container, image, package state, cache entry, or modified imported source remains. Intentional retained state consists only of this branch packet, patch, scripts, receipts, hashes, and drafts.

## First incomplete step

Materialize a full checkout of `josch/mmdebstrap` at `77ec9be5417ee44c96343d2347145585da1b1f94`, apply the clean packet patch, identify the project's accepted tarfilter test location, and convert the focused matrix into an upstream-native regression.

## Next safe action

```text
git clone https://gitlab.mister-muffin.de/josch/mmdebstrap.git /tmp/mmdebstrap-unit15
cd /tmp/mmdebstrap-unit15
git checkout 77ec9be5417ee44c96343d2347145585da1b1f94
patch --fuzz=0 -p1 -i /path/to/linux-fieldwork/upstream-packets/units/15-tarfilter-transform-metadata/patches/0001-tarfilter-transform-metadata.patch
# Inspect README.md, coverage.py, coverage.sh, and tests/ for the accepted focused test entry point.
# Port scripts/run_matrix.py into that native location, run the focused gate, then record the exact candidate commit and full commands in TESTS.md.
```

## Unresolved blockers

- technical: upstream-native regression and full-checkout gates remain;
- compatibility: final one-commit versus ordered-two-commit review form remains open;
- overlap: visible public overlap is clear as of 2026-08-01; recheck immediately before submission;
- environment or tooling: a controlled full upstream checkout and fork branch are absent;
- authority: external contact remains unauthorized.

## Files to read first

1. `README.md`
2. `SOURCE_MAP.md`
3. `DEEP_DIVE.md`
4. `TESTS.md`
5. `DECISIONS.md`
6. `artifacts/APPLICATION.txt`
7. owning issues and PRs listed in `SOURCE_MAP.md`

## External-contact state

`false; none occurred.` Internal Linux Fieldwork claim/checkpoint comments are repository coordination, not upstream contact.

## Do not repeat

- Do not revive PR #48's unchanged default symlink expectation.
- Do not use PR #52 as the canonical composition.
- Do not infer full GNU transform compatibility from this unit.
- Do not ship the historical PR #68 patch directly through GNU patch 2.8 without addressing its parser-hunk application failure.
- Do not use Python `str.isdigit()` for occurrence flags.
- Do not rerun the ad hoc source reconstruction; use `scripts/materialize_and_run.sh`.
- Do not contact upstream without explicit authorization.
