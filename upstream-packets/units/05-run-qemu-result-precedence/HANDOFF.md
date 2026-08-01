# HANDOFF — unit 05 `run_qemu.sh` result precedence

Handoff date: 2026-08-01  
State: `ACTIVE`  
External contact authorized: `false`  
External contact made: `none`

## Current branches

### Linux Fieldwork packet

```text
repository: teamleaderleo/linux-fieldwork
branch: upstream/unit-05-run-qemu-result-precedence
packet: upstream-packets/units/05-run-qemu-result-precedence/
complete packet head before this HANDOFF update: 9e67661be8a12e79c4f6de079bcd48756911babf
```

### Controlled mmdebstrap candidate

```text
repository: teamleaderleo/mmdebstrap
base branch: master
base commit: 574048f2a720057b75e56622003932f344dc700a
candidate branch: linux-fieldwork/unit-05-run-qemu-result-precedence
candidate head: 457095c6f89655ab12b7055307f519e71bb0dbca
relation: four commits ahead, zero behind
changed files: run_qemu.sh only
```

## Current result

The user-created GitHub mirror supplied the exact missing controlled candidate surface.

Mirror `master` contains repository-root `run_qemu.sh` as Git blob `426aeeb854173569b24e64d6eb85019f45bdf0b6`. That is exactly the imported Linux Fieldwork source blob used by the canonical four-patch work.

The candidate branch applies the four corrections as four source commits and ends at:

```text
head: 457095c6f89655ab12b7055307f519e71bb0dbca
run_qemu.sh blob: 3e8d4dc07f91d246a372749eb49ff9489c21c7b7
bytes: 2924
SHA-256: 8d2b0fdef2c93fcd3d97f296dfe58d3cbe198e8a02ac85930aa8c3c89aedb90f
/bin/sh -n: success
```

Selected result order:

```text
captured host failure
> completed guest or protocol failure
> first signal received during ordinary cleanup
> first cleanup failure
> success
```

## Candidate commits

1. `614fb26a4f0724618a5eecd3ce1bee12454ff7de` — preserve primary result through cleanup.
2. `cb6ef6d6c2b1368b3603b2ec06635c3815f31e11` — retain first handled signal through cleanup.
3. `13cf34fd87d44b4d37c6767fdbd153b2ef535a57` — retain signals during ordinary EXIT cleanup.
4. `457095c6f89655ab12b7055307f519e71bb0dbca` — preserve completed guest failure before cleanup signal.

GitHub compare reports four commits ahead, zero behind, with one modified file, 61 additions, and 10 deletions.

## Completed work

- Read issue #397, packet guidance, index, and every unit-05 carrier.
- Created and maintained the Linux Fieldwork unit branch and required packet bundle.
- Retained all four canonical patches byte-identically.
- Proved ordered patch application and shell syntax on the exact imported source.
- Located the user-controlled mirror `teamleaderleo/mmdebstrap`.
- Verified mirror `master`, exact base commit, and exact source blob.
- Created the controlled candidate branch.
- Applied the four changes as four reviewable commits.
- Verified the final GitHub blob equals the locally validated composed blob.
- Recorded compare, blob, SHA-256, byte, and syntax receipts.
- Kept external contact at zero.

## User action

No fetch command, clone command, branch setup, patch command, or test command is required from the user.

The next user decision comes after the remaining technical gates:

```text
authorize upstream submission
hold for more testing
retire because canonical upstream already has equivalent work
```

## First incomplete step

Search current canonical Salsa issues, branches, and merge requests for equivalent active work, and resolve the current canonical `master` commit/file identity before any submission.

This requires canonical-host visibility. It does not require the user to operate Git locally.

## Next safe technical actions

1. Reconcile controlled mirror base `574048f2…` with current canonical Salsa `master` when access is available.
2. Search for equivalent active upstream work.
3. Run current upstream ordinary checks on candidate head `457095c6…`.
4. Run a bounded QEMU/`debvm-run` smoke test only in an authorized disposable environment.
5. Rebase and rerun when canonical `master` differs.
6. Refresh `UPSTREAM_PR.md` with exact canonical identities.
7. Move to `READY FOR AUTHORIZATION` only after the exact candidate head passes the remaining gates.

## Historical evidence

```text
canonical PR: #319
head: 2fe3f99364df29de217536dc35a4d03b10f49640
merge: b196d6b45f496d8eb2d763922532ad257f24bba8
CI: 30628645668 / job 889
result: success
repository tests: 276 passed
```

The candidate bytes on the controlled mirror equal the bytes validated by that composition.

## Known limits

- Canonical Salsa `master` identity remains unresolved in this runtime.
- Current Salsa equivalent-carrier search remains unresolved.
- Upstream-native ordinary checks have yet to run on the controlled candidate branch.
- Real QEMU/`debvm-run` execution requires a disposable authorized environment.
- Patch 4 depends on guest status becoming complete and durable before host cleanup begins.
- Later INT/TERM suppression assumes bounded cleanup.

## Publication state

`UPSTREAM_ISSUE.md` and `UPSTREAM_PR.md` remain internal drafts marked `DRAFT — DO NOT SEND`.

No upstream issue, merge request, comment, review, email, or mailing-list post has been authorized or created.

## Exit criteria

Move from `ACTIVE` to `READY FOR AUTHORIZATION` after recording:

- current canonical base identity;
- current source identity or clean rebase;
- current equivalent-carrier search;
- focused behavior gate;
- upstream ordinary checks;
- cleanup and immediate rerun;
- final draft matching the exact delta.
