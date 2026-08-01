# Handoff — systemd-oomd reporter collision

Updated: `2026-08-01`  
State: `ACTIVE — CURRENT-MAIN VM GATE QUEUED`  
Linux Fieldwork issue: `#140`  
Linux Fieldwork PR: `#245`  
Controlled systemd fork PR: `teamleaderleo/systemd#1`  
External contact: `false`

## Exact current source

- canonical systemd main: `6a863b4dc31adc49fdfdd5deba32ed1b115adda3`;
- canonical `TEST-55-OOMD.sh` blob: `43937c6ec7877df23f66ccd3827a1b6f154943ff`;
- controlled fork main was fast-forwarded to the same canonical commit;
- controlled fork branch: `linux-fieldwork/oomd-reporter-collision-current-main`;
- controlled fork probe head at launch: `cd8d4b0873da68866585a610865248d0ed98ef56`.

The controlled fork PR compares as exactly two commits and two files ahead of current main:

- `.github/workflows/fieldwork-oomd-reporter-collision-vm.yml`;
- `tools/fieldwork-inject-oomd-reporter-collision.py`.

No systemd product source is changed.

## Corrected prior evidence

The earlier focused Linux Fieldwork run `30591852103` failed before applying the regression. The exact failure was:

```text
error: corrupt patch at .../0001-test-preserve-system-registration-across-user-reload.patch:89
```

The old hunk declared 60 inserted lines and a 66-line new hunk, while it actually contained 57 inserted lines and 63 new hunk lines. The retained mail patch is now structurally repaired and checked with:

```text
git apply --check --whitespace=error-all
bash -n test/units/TEST-55-OOMD.sh
git diff --check
```

The source verifier is upgraded to schema 2 and pinned to current main plus the exact integration-test blob.

## Current VM discriminator

The controlled fork workflow uses systemd's own pinned mkosi action and integration-test commands on an Arch Linux QEMU VM. It injects one testcase into `TEST-55-OOMD.sh` and runs only:

```text
TEST_MATCH_TESTCASE=user_manager_reload_preserves_system_oomd_registration
```

The testcase records:

- the exact `oomctl` block for `user@<uid>.service` before reload;
- the exact block after 1, 5, and 10 seconds;
- `ActiveEnterTimestampMonotonic` before and after;
- `NRestarts` before and after;
- `ManagedOOMMemoryPressure` before and after;
- systemd-oomd and user-manager journal entries after a captured journal cursor.

The classifier emits one of:

- `reproduced` — the exact registration vanished while service identity and configured policy stayed stable;
- `not-reproduced` — the registration remained with stable controls;
- `control-failure`, `missing-journal`, or `unclassified` — the experiment is invalid and the workflow fails.

The test process may exit nonzero when the bug is reproduced. The workflow treats a classified reproduction as a successful experiment and preserves the full journal and receipt.

## Current runs

Controlled fork exact head `cd8d4b0873da68866585a610865248d0ed98ef56`:

- focused VM: run `30693755971` — queued at handoff time;
- build test: run `30693755963` — queued;
- upstream mkosi matrix: run `30693755969` — queued;
- unit tests: run `30693755973` — queued;
- lint: run `30693755993` — queued;
- differential shellcheck: run `30693756012` — queued.

Linux Fieldwork source/patch verification has been retriggered on the repaired branch and current-main pin; record its exact run once GitHub associates the newest head.

## First incomplete step

Retrieve the focused VM result and artifact for run `30693755971`.

If the outcome is `reproduced`:

1. retain the first current-main journal and receipt without rewriting it;
2. extract the exact sender/update sequence around the reload;
3. add temporary controlled-fork instrumentation that records reporter identity, path, property, mode, and limit at the oomd receive boundary;
4. rerun only the focused testcase;
5. use the resulting trace to select and test the effective-policy model.

If the outcome is `not-reproduced`, compare current main with the public reproducer's versions and identify the commit or environmental condition that changed the behavior.

If the outcome is a control or infrastructure failure, repair the experiment before any product design claim.

## Ambitious product boundary

The preferred architecture remains source-aware subscriptions keyed by at least:

```text
(property, cgroup path, reporter identity)
```

An `auto` update should remove only the sending reporter's contribution. One effective cgroup policy is then derived from all live contributions.

Before selecting a product patch, the controlled test matrix must cover:

- PID 1 `kill` plus user-manager `auto` for the same path;
- two explicit reporters with equal limits;
- conflicting pressure limits;
- reporter disconnect and reconnect;
- explicit policy withdrawal by one reporter;
- cgroup disappearance;
- dump/diagnostic visibility of overlapping sources.

The effective-policy rule—PID 1 precedence, strictest limit, explicit conflict rejection, or another documented policy—must be chosen deliberately and encoded in tests.

## Scope guard

Keep this lane on ManagedOOM reporter ownership and effective policy. Do not mix in pressure calculation, victim selection, prekill hooks, swap policy, generic Varlink refactors, or unrelated cgroup cleanup.

## Authority

All writes are inside `teamleaderleo/linux-fieldwork` and the controlled `teamleaderleo/systemd` fork. No comment, pull request, review, reaction, patch submission, email, or other action was made in `systemd/systemd`.