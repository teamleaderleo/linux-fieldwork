# Tests and receipts — unit 11

## Evidence policy

Historical CI receipts are preserved as exact carrier evidence. This workspace does not relabel them as execution on the current upstream head. Current-upstream gates remain explicit until a network-capable worktree or controlled fork exists.

## Historical executed matrix

### Status-only predecessor

| Evidence | Exact identity | Result |
| --- | --- | --- |
| PR #143 candidate | `96ddac76ab9dead7875937a6edfa37137bc52eb9` | source change reviewed |
| Linux Fieldwork CI | run `30577412842` | success |
| Clean internal carrier | PR #204 head `b5efc8faf35c1da725a3b995a344fadc078ad5d2` | merged internally |
| Execution carrier | PR #201 run `30579465025` | exact four-test matrix ran twice successfully |

Proven controls:

- imported baseline parent-only SIGINT returned 0;
- status-only candidate returned 130 with `interrupted by SIGINT`;
- immediate worker PID was gone;
- interrupted run produced no success marker;
- unsignaled candidate returned 0 and reported success;
- temporary roots were removed.

### Selected group candidate

| Evidence | Exact identity | Result |
| --- | --- | --- |
| PR #313 executed mechanism | `e90fc438f530f7bd78ffd6fd1ba24c665bd96913` | product matrix executed |
| Linux Fieldwork CI | run `30632491641`, job `91161937871` | success |
| PR #313 current evidence head | `dfc6d0503fb844f4c428ce16a567a9fdcd35280a` | current-head CI below |
| Current-head repository gate | run `30633602052` / 943 | success |
| QEMU evidence refinement | PR #339 `8253ab2ef6fed22b34fc5f5d6d20cda75c25e2c7` | one-file test-only refinement |
| Refinement gate | run `30633578396` / 942, job `91165522248` | success |

Mechanism CI validated:

- two retained patch carriers and three hunks;
- Python compilation;
- all 359 discovered repository tests;
- shell syntax and command-help checks;
- null baseline, status-only, group candidate, ordinary foreground-group, source-shape, and unsignaled controls;
- QEMU-wrapper baseline, status-only, group candidate, and unsignaled controls;
- actual passwordless-sudo baseline, status-only, group candidate, and unsignaled controls.

Distinguishing result:

| Variant | Parent-only SIGINT status | Responsive backend state | Later work |
| --- | ---: | --- | --- |
| imported baseline | 0 after deliberate release | alive before release | yes |
| status-only predecessor | 130 after deliberate release | alive before release | yes |
| selected group candidate | 130 | no live in-group process | no |

PR #339 strengthens the QEMU losing controls by recording exact Python SIGINT-handler entry before deliberate survivor release. It changes no product source or patch.

### Stronger policy research

| Evidence | Exact identity | Result |
| --- | --- | --- |
| Issue #341 retained carrier | PR #347 head `615bd4f5256d9851f682e48e037169ceeb7bb98c` | closed, no product patch |
| Composed gate | run `30637202171` / 978 | success |
| Generated merge | `c3aa75065021c32203c82811e115c2b39028436b` | five-file research surface |
| Finalization successor | PR #353 head `55bf9e9c8b511399647658139c006afc4ed1fc52` | composed into research carrier |
| Successor gate | run `30636171624` / 966 | success |

The research proved synthetic TERM-to-KILL sufficiency and also proved why it stays unselected: no real backend supplied necessity, grace-period, or state-loss evidence.

## Work performed in this unit session — 2026-08-01

### Carrier and source inspection

Executed through repository APIs and public source pages:

1. read issue #397 and its workflow comment;
2. read `upstream-packets/README.md` and `INDEX.md`;
3. read issues #141, #306, and #341 plus comments;
4. read PRs #143, #204, #313, #332, #336, #339, #347, and #353;
5. read the exact retained product patches from PR #313;
6. fetched Linux Fieldwork `main` `coverage.py` lines 400–430 and recorded blob `9a522484aef05deae514a98e4b6adf5feb6c886d`;
7. confirmed the imported source still contains the original immediate-child launch and `break` handler;
8. confirmed canonical upstream advertises `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`;
9. created the upstream-root retained patch in this packet.

Result: static current-local context check passed. No candidate execution occurred in this session.

### Shell worktree attempt

A shell-side remote fetch was attempted before connector-only work continued. DNS resolution was unavailable in the execution container, so no canonical upstream checkout, patch application, compilation, or focused runtime test was claimed.

## Current-upstream gate — exact next commands

Run from a clean canonical mmdebstrap checkout at `77ec9be5417ee44c96343d2347145585da1b1f94`:

```sh
set -eu
git status --short
test "$(git rev-parse HEAD)" = 77ec9be5417ee44c96343d2347145585da1b1f94
patch --batch --forward --fuzz=0 -p1 \
  < /path/to/linux-fieldwork/upstream-packets/units/11-coverage-backend-cancellation/patches/0001-coverage-own-selected-backend-group.patch
python3 -m py_compile coverage.py
git diff --check
git diff -- coverage.py
```

Then port or apply the focused lifecycle fixture and run its null, QEMU-wrapper, sudo, and unsignaled controls. Preserve exact commands chosen by the upstream worktree in this file before execution.

## Required candidate assertions

- parent-only SIGINT reaches the coverage driver after nested backend work starts;
- driver exits 130 and emits the interruption diagnostic;
- wrapper is reaped;
- all modeled responsive processes in the selected group are gone;
- no later-work marker appears;
- ordinary unsignaled candidate returns 0;
- temporary roots, FIFOs, markers, and helper processes are cleaned;
- immediate rerun succeeds;
- the exact patch applies with zero fuzz and `coverage.py` compiles.

## Unexecuted gates

- canonical upstream checkout at exact head `77ec9be...`;
- zero-fuzz patch application to that worktree;
- exact candidate compilation in that worktree;
- focused lifecycle matrix on that candidate;
- full upstream test suite;
- current Forgejo CI;
- real QEMU/debvm execution;
- non-Linux execution;
- upstream maintainer review.

## Cleanup and rerun state

Historical selected-candidate controls reported cleaned temporary state and successful unsignaled reruns. This session created no backend processes or temporary test roots. The current-upstream runtime cleanup gate remains pending.
