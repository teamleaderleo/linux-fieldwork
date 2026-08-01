# HANDOFF — unit 05 `run_qemu.sh` result precedence

Handoff date: 2026-08-01  
State: `HOLD`  
External contact authorized: `false`  
External contact made: `none`

## Exact branches and heads

### Linux Fieldwork packet

```text
repository: teamleaderleo/linux-fieldwork
branch: upstream/unit-05-run-qemu-result-precedence
packet: upstream-packets/units/05-run-qemu-result-precedence/
complete packet head immediately before this HANDOFF update: 523499647ec0003f5597cb5be056c94ec365453a
```

### Controlled mmdebstrap candidate

```text
repository: teamleaderleo/mmdebstrap
base branch: master
base commit: 574048f2a720057b75e56622003932f344dc700a
base run_qemu.sh blob: 426aeeb854173569b24e64d6eb85019f45bdf0b6
candidate branch: linux-fieldwork/unit-05-run-qemu-result-precedence
candidate head: 6efe6945f9f89cff57fe84086ede7bda747c3879
candidate run_qemu.sh blob: 1fc816d6fe982351f6519fd1458329112eebdcfb
candidate bytes: 3095
candidate SHA-256: 434e7b6b9c32e30b506ea6af121608414c42b668c329e6395e75e19dc09ff276
relation: five commits ahead, zero behind
changed files: run_qemu.sh only
compare: 64 additions, 10 deletions
```

## Current result

The canonical controlled candidate is now a five-commit series. Complete-diff review proved that the historical four-commit head still lost result ownership in two signal-handler setup windows. The fifth commit closes those windows while preserving the selected order:

```text
captured host failure
> completed guest or protocol failure
> first signal received during ordinary cleanup
> first cleanup failure
> success
```

The unit is `HOLD`, rather than `READY FOR AUTHORIZATION`, because current canonical Salsa identity/overlap and upstream-native QEMU execution remain unrecorded.

## Candidate commits

1. `614fb26a4f0724618a5eecd3ce1bee12454ff7de` — preserve primary result through cleanup.
2. `cb6ef6d6c2b1368b3603b2ec06635c3815f31e11` — retain first handled signal through cleanup.
3. `13cf34fd87d44b4d37c6767fdbd153b2ef535a57` — retain signals during ordinary EXIT cleanup.
4. `457095c6f89655ab12b7055307f519e71bb0dbca` — preserve completed guest failure before cleanup signal.
5. `6efe6945f9f89cff57fe84086ede7bda747c3879` — close explicit and ordinary handler-entry setup windows.

## First distinguishing result in this pass

Four-commit explicit handler setup window:

```text
first signal: TERM
second signal before trap replacement: INT
observed: 130
required: 143
```

Four-commit ordinary EXIT setup window:

```text
completed guest result: 1
TERM before cleanup recorder traps
observed: 143
required: 1
```

Both controls completed cleanup. The failure owner was product result precedence during handler transition.

## Selected repair

Patch 5:

- adds `cleanup_phase=running`;
- captures `$?` and marks ordinary cleanup in one assignment-only command: `rv=$? cleanup_phase=exit`;
- disables overlapping INT/TERM handling in each trap action before entering a handler;
- records an early signal that entered through the old action and returns to ordinary cleanup;
- retains first-writer cleanup signal behavior after recorder traps are installed.

Packet patch:

```text
patches/0005-close-signal-handler-setup-windows.patch
Git blob: f7e906d915c34db6e7546e4a9b1e4024e19d98d1
```

## Completed gates

### Controlled lifecycle matrix

```text
58 passed
0 failed
```

Includes baseline and intermediate losing controls, final result matrix, competing signals, cleanup failure, once-only cleanup, temporary-directory removal, and immediate clean rerun.

Receipt:

```text
artifacts/2026-08-01-controlled-fork-lifecycle-matrix.txt
```

### Setup-window repair controls

```text
repaired explicit TERM then INT: 143
repaired completed guest 1 then early TERM: 1
repaired early TERM then later INT: 143
cleanup sequence: rm, rmdir
successful repaired tmpdirs: removed
/bin/sh -n: pass
```

Receipt:

```text
artifacts/2026-08-01-handler-setup-window-repair.txt
```

### Durable regression

```text
tests/test_run_qemu_handler_setup_windows.py
Git blob: a58eb89029729a89208c72e30164bcfe3c0aa139
```

Equivalent reduced fixtures executed in this pass. The exact checked-in module still needs a complete-checkout or hosted-CI execution identity.

## Fixture interruptions classified

Two preliminary local harness runs were excluded:

1. synchronization waited for cleanup before sending the signal that begins cleanup;
2. the classifier expected ordinary baseline EXIT re-entry instead of explicit-signal re-entry.

Owner: fixture/classifier. Product code remained unchanged. The corrected run is the 58/58 receipt.

## Project-native test path

mmdebstrap documents:

```sh
./make_mirror.sh
CMD=./mmdebstrap ./coverage.sh
```

Individual cases use `coverage.py`; QEMU-classified cases execute `./run_qemu.sh`.

## HOLD gates — first incomplete step

1. Resolve current canonical Salsa `master` commit and live `run_qemu.sh` blob.
2. Search current Salsa issues, branches, and merge requests for equivalent active work.
3. Rebase or restack the five logical changes on that exact canonical head.
4. Execute `tests/test_run_qemu_handler_setup_windows.py` from a complete checkout or hosted CI.
5. Run current mmdebstrap QEMU-classified focused and ordinary tests on the exact candidate.
6. Clean the checkout and rerun focused controls after any rebase.
7. Refresh the final draft with exact canonical and run identities.

These are repository/hosted-environment actions. The user has no fetch, clone, patch, branch, or local test command to perform.

## Environment boundary

This runtime could read and write GitHub through the connector but could not resolve the GitHub or Salsa hosts through the container network. It also lacked a prepared mmdebstrap mirror/cache and disposable QEMU image environment. Therefore:

- exact controlled-fork source and reduced shell fixtures are demonstrated;
- current canonical Salsa reconciliation remains unresolved;
- upstream-native QEMU execution remains unresolved;
- no claim is made that historical four-patch CI validates patch 5.

## Cleanup state

All reduced fixture processes completed or were reaped. Successful repaired cases removed their temporary directories. No mount, guest image, network service, credential, or external project state was created.

## Durable records updated

- `README.md` — five-commit identity and HOLD state;
- `SOURCE_MAP.md` — patch 5, test ownership, and project-native path;
- `DEEP_DIVE.md` — setup-window mechanism and rejected repairs;
- `TESTS.md` — exact executed and queued gates;
- `DECISIONS.md` — five-commit selection and HOLD decision;
- `UPSTREAM_ISSUE.md` — refreshed internal issue draft;
- `UPSTREAM_PR.md` — refreshed internal five-commit merge-request draft;
- `upstream-packets/INDEX.md` — unit 05 marked HOLD;
- both raw artifacts and the new regression module.

## Publication state

`UPSTREAM_ISSUE.md` and `UPSTREAM_PR.md` remain `DRAFT — DO NOT SEND`.

No upstream issue, merge request, comment, review, email, or mailing-list post has been authorized or made.

## Resume with

Refresh issue #397, this handoff, the exact controlled candidate head `6efe6945f9f89cff57fe84086ede7bda747c3879`, and current canonical Salsa. Perform the canonical identity/overlap gate first. Do not change product code before classifying any rebase or test failure owner.
