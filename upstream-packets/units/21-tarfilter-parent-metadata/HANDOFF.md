# Current handoff

Updated: `2026-08-01 15:38 +08`  
Worker or variant: `GPT-5.6 Thinking`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-21-tarfilter-parent-metadata` |
| Linux Fieldwork substantive parent | `effc85d43a1fc8cca966dace5e900160504f0b0c` |
| Linux Fieldwork head | commit containing this handoff; exact SHA recorded in the #397 `UNIT CHECKPOINT` |
| Upstream repository/branch | `josch/mmdebstrap` Muffin Forgejo `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Current `tarfilter` blob | `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Candidate fork/branch | `NEEDS FORK` / `NEEDS BRANCH` |
| Patched `tarfilter` blob | `a7bdcb73e574aa1720b319b8531f65d10fbd2446` |
| Proposed test blob | `9212cb89dfcb954d84d2f7f8e6557755d59e1986` |
| Patch | `patches/0001-tarfilter-retain-parent-metadata.patch` |
| Patch SHA-256 | `8bdd156eb375114c3f3be80c4433a06f6ac8a6d8e189023a02d39774d80c2f74` |
| dpkg reference | `guillemj/dpkg main:src/main/filters.c@4fc1600a5717726faddc2fb556730f217e7f22a2` |
| dpkg comparison artifact | `artifacts/dpkg-comparison.json`, SHA-256 `65fbceebbb1b0dc7fdadcb13662dc039bc976adddb4989ee9dde4ba77281aa3b` |
| Local metadata artifact | `artifacts/local-matrix.json`, SHA-256 `f061350cf1e975dadad5e6e812ad0219cf664bfbfce6d4963e7459a45873a3b1` |
| Owning records | Linux Fieldwork #39; issue #397 unit 21 |

## Current bounded claim

Exact current mmdebstrap `tarfilter` drops explicit parent entries for nested includes. The retained patch applied to that exact source passes five focused cases and preserves directory and symlink metadata. The dpkg comparison establishes the intended compatibility boundary: keep conservative wildcard retention, add the missing exact-ancestor direction, and reject plain-prefix sibling aliases. Full repository application and native mmdebstrap execution remain unexecuted.

## Work completed in this pass

- resumed the existing unit branch and packet;
- refreshed issue #397, the packet runbook/index, issue #39, current mmdebstrap source identities, and current dpkg reference source;
- reviewed dpkg `filter_should_skip()` at exact file blob `4fc1600…`;
- implemented a deterministic eight-case model of dpkg's fixed-prefix `strncmp()` behavior and the selected unit-21 predicate;
- proved dpkg drops exact ancestors, preserves wildcard conservatism, and can over-include lexical siblings such as `/usr2`;
- proved the candidate adds exact ancestry and component boundaries while preserving wildcard and leading-wildcard conservatism;
- retained `scripts/compare-dpkg-parent-retention.py` and `artifacts/dpkg-comparison.json` with exact SHA-256 identities;
- updated README, source map, deep dive, tests, decisions, PR draft, and this handoff;
- made no upstream contact.

## Changed paths in this pass

All paths are below `upstream-packets/units/21-tarfilter-parent-metadata/`:

- `scripts/compare-dpkg-parent-retention.py`
- `artifacts/dpkg-comparison.json`
- `README.md`
- `SOURCE_MAP.md`
- `DEEP_DIVE.md`
- `TESTS.md`
- `DECISIONS.md`
- `UPSTREAM_PR.md`
- `HANDOFF.md`

## Distinguishing observations

- dpkg current source stores the raw pattern, unlike mmdebstrap's current tuple, but compares candidate path against the fixed prefix in one direction;
- dpkg model result for path `/usr` with include `/usr/bin/tool`: `false`;
- candidate result for the same exact ancestor: `true`;
- dpkg and candidate both retain `/usr/bin` for `/usr/*/tool` and retain all candidate parents for leading wildcard `*/tool`;
- dpkg model retains `/usr2` for include `/usr` or `/usr/*` through plain prefix matching;
- candidate rejects both sibling aliases through `/` component boundaries;
- the candidate follows dpkg's conservative intent and deliberately differs from its exact predicate.

## Gates completed

- exact current-source blob verification — PASS;
- baseline focused losing control — expected status 1;
- candidate focused five-case test — PASS;
- `python3 -m py_compile tarfilter` — PASS;
- `sh -n tests/tarfilter-parent-metadata` — PASS;
- `git diff --check` — PASS;
- local cleanup and immediate matrix rerun — PASS;
- `python3 -m py_compile scripts/compare-dpkg-parent-retention.py` — PASS;
- dpkg comparison, eight assertions — PASS;
- complete retained patch and compatibility review — PASS.

## Red or neutral runs classified

- Baseline focused test status 1: product-source failure, expected and distinguishing.
- Local `coverage.txt` apply check offset `-69`: fixture-line offset because the local fixture retained only the exact public registration window. Full-file application remains pending.
- dpkg exact-ancestor and sibling-prefix outcomes are reference behavior, neither candidate failures nor mmdebstrap integration results.

## Cleanup state

Temporary baseline, archive, extraction, comparison, and bytecode directories were removed. No process, socket, mount, lock, container, cache entry, or host mutation remains. Packet scripts, patches, drafts, and artifacts are intentional retained state.

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

Record the exact checkout head, complete patch application result, command output, cleanup, and immediate rerun in `TESTS.md`. A conflict or native-test failure becomes the next bounded repair. A green result advances to complete-diff review and broader gates.

## Unresolved blockers

- technical: full canonical checkout application and native focused gate;
- compatibility: maintainer acceptance of the explicit dpkg-intent-versus-predicate distinction;
- overlap: none surfaced on 2026-08-01; recheck immediately before authorized submission;
- environment or tooling: no controlled canonical checkout/fork was available in this pass;
- authority: external contact, fork publication, issue, PR, comment, email, or submission remains unauthorized.

## Files to read first

1. `README.md`
2. `TESTS.md`
3. `artifacts/exact-source-validation.txt`
4. `artifacts/dpkg-comparison.json`
5. `DEEP_DIVE.md`
6. `DECISIONS.md`
7. issue #39 and issue #397

## External-contact state

`false`; no public upstream action occurred. Internal Linux Fieldwork branch commits and the #397 checkpoint are the only writes.

## Avoid repeating

- translated-regex prefix diagnosis from issue #39;
- original-glob-only or ancestor-only designs;
- exact current-file losing control;
- local five-case candidate run;
- dpkg source-model comparison at blob `4fc1600…`;
- broad adjacent tarfilter discovery outside units 20, 22, 15, and 16.
