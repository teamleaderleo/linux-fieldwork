# Current handoff

Updated: `2026-08-01 08:10 +08`  
Worker or variant: `GPT-5.6 Thinking`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-21-tarfilter-parent-metadata` |
| Linux Fieldwork substantive parent | `802fe768532559d009a1456247e8ce0bc0724d5c` |
| Linux Fieldwork head | commit containing this handoff; exact SHA recorded in the #397 `UNIT CHECKPOINT` |
| Upstream repository/branch | `josch/mmdebstrap` Muffin Forgejo `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Current `tarfilter` blob | `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Candidate fork/branch | `NEEDS FORK` / `NEEDS BRANCH` |
| Patched `tarfilter` blob | `a7bdcb73e574aa1720b319b8531f65d10fbd2446` |
| Proposed test blob | `9212cb89dfcb954d84d2f7f8e6557755d59e1986` |
| Patch | `patches/0001-tarfilter-retain-parent-metadata.patch` |
| Patch SHA-256 | `8bdd156eb375114c3f3be80c4433a06f6ac8a6d8e189023a02d39774d80c2f74` |
| Owning records | Linux Fieldwork #39; issue #397 unit 21 |
| Latest artifacts | `artifacts/exact-source-validation.txt`; `artifacts/local-matrix.json` SHA-256 `f061350c…` |

## Current bounded claim

Exact current `tarfilter` source drops explicit parent entries for nested includes. The retained patch applied to that exact source passes five focused cases and preserves directory and symlink metadata. Full repository integration remains unexecuted.

## Work completed in this pass

- refreshed issue #397, packet runbook/index, issue #39, canonical upstream head, and public overlap listings;
- confirmed issue #39 links no additional source carrier;
- resumed the existing unit branch and earlier packet;
- reconstructed current full `tarfilter` and verified Git blob `ad776…`;
- reran the losing baseline against that exact blob;
- applied the source patch to the exact current file;
- expanded the candidate regression from four cases to five with a symlink-parent control;
- verified symlink target, mode, ownership, timestamp, and PAX marker retention;
- ran Python compilation, shell syntax, focused execution, and diff whitespace checks;
- replaced the synthetic source excerpts with exact current source hunk coordinates and blob identities;
- updated the patch, reproducer, matrix, README, tests, PR draft, exact-source receipt, and this handoff;
- made no upstream contact.

## Changed paths

- `README.md`
- `TESTS.md`
- `UPSTREAM_PR.md`
- `HANDOFF.md`
- `patches/0001-tarfilter-retain-parent-metadata.patch`
- `scripts/reproduce-parent-metadata.py`
- `artifacts/local-matrix.json`
- `artifacts/exact-source-validation.txt`

All paths are below `upstream-packets/units/21-tarfilter-parent-metadata/`.

## Distinguishing observations

- exact baseline blob: status 1, actual members `['usr/bin/tool']`;
- exact patched source: status 0 across five focused cases;
- storing the original glob alone leaves exact ancestry broken because the old comparison points the opposite way;
- ancestor-only comparison loses `/usr/*/tool` at `usr/bin`;
- both directions plus component boundaries pass the selected matrix;
- the symlink candidate retains `linkroot -> usr/bin`, mode `0777`, mtime `1700000008`, and PAX marker `symlink-parent`;
- public overlap review exposed no equivalent unit as of 2026-08-01.

## Gates completed

- exact source Git-blob verification — PASS;
- baseline focused losing control — expected status 1;
- candidate focused five-case test — PASS;
- `python3 -m py_compile tarfilter` — PASS;
- `sh -n tests/tarfilter-parent-metadata` — PASS;
- `git diff --check` — PASS;
- local cleanup and immediate matrix rerun — PASS;
- exact source/test patch review — PASS.

## Red or neutral runs classified

- Baseline focused test status 1: product-source failure, expected and distinguishing.
- Local `coverage.txt` apply check offset `-69`: fixture-line offset because the local fixture retained only the exact public registration window. Full-file application remains pending.

## Cleanup state

Temporary baseline, archive, extraction, and bytecode directories were removed. No process, socket, mount, lock, container, cache entry, or host mutation remains. Packet artifacts are intentional retained state.

## First incomplete step

Apply the complete three-file patch to a full canonical checkout at `77ec9be5417ee44c96343d2347145585da1b1f94` and run the native focused selector.

## Next safe action

```sh
git clone <controlled-or-read-only-canonical-mmdebstrap-checkout> mmdebstrap-unit21
cd mmdebstrap-unit21
git checkout 77ec9be5417ee44c96343d2347145585da1b1f94
git apply --check /path/to/patches/0001-tarfilter-retain-parent-metadata.patch
git apply /path/to/patches/0001-tarfilter-retain-parent-metadata.patch
CMD=./mmdebstrap ./coverage.py tarfilter-parent-metadata
black --check ./tarfilter
git diff --check
```

Record the exact checkout head, output, cleanup, and rerun in `TESTS.md`. A conflict or native-test failure becomes the next bounded repair; a green result advances to complete-diff review and broader gates.

## Unresolved blockers

- technical: full-checkout application and native focused gate;
- compatibility: upstream acceptance of conservative leading-wildcard parent retention;
- overlap: none surfaced; recheck immediately before authorized submission;
- environment/tooling: no controlled canonical checkout/fork was available in this pass;
- authority: external contact and public submission remain unauthorized.

## Files to read first

1. `README.md`
2. `TESTS.md`
3. `artifacts/exact-source-validation.txt`
4. `DEEP_DIVE.md`
5. `SOURCE_MAP.md`
6. `DECISIONS.md`
7. issue #39 and issue #397

## External-contact state

`false`; no public upstream action occurred.

## Avoid repeating

- translated-regex prefix diagnosis from issue #39;
- original-glob-only or ancestor-only designs;
- exact current-file losing control;
- local five-case candidate run;
- broad adjacent tarfilter discovery outside units 20, 22, 15, and 16.
