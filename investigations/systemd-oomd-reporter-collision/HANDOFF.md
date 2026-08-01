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

Replacement Linux Fieldwork runs on the repaired branch:

- source/patch verification: `30693896488` — queued at this handoff update;
- repository CI: `30693896504` — queued.

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

## Current controlled-fork runs

Exact probe head `cd8d4b0873da68866585a610865248d0ed98ef56`:

- focused VM: run `30693755971` — queued;
- build test: run `30693755963` — queued;
- upstream mkosi matrix: run `30693755969` — queued;
- unit tests: run `30693755973` — queued;
- lint: run `30693755993` — queued;
- differential shellcheck: run `30693756012` — queued.

## Source-aware product design

`DESIGN.md` now specifies the product contract against exact current main.

### Representation

Keep the existing effective path-to-`OomdCGroupContext` maps used by polling and action code. Add a source layer beside them:

```text
reporter authority = (SYSTEM_MANAGER | USER_MANAGER, uid)
contribution key   = (reporter authority, property, cgroup path)
```

Varlink connections are liveness/generation objects. An authority can have multiple live links during reconnect overlap. A stale old-link disconnect therefore cannot delete policy reasserted through a newer link.

### Update and lifecycle rules

- `auto` removes only the sending authority's contribution;
- an explicit update replaces only that authority's complete tuple;
- recompute only the affected `(property, path)` effective policy;
- on the last user-manager link disconnect, withdraw that authority's contributions;
- on PID 1 subscription loss, withdraw system-manager contributions and reveal any surviving user contribution;
- reconnect initial snapshots repopulate contributions normally.

### Effective policy

```text
SYSTEM_MANAGER > USER_MANAGER
```

Select the winning complete contribution tuple. Never combine a limit from one reporter with a duration or rules list from another reporter. Field-wise “strictest” merging can synthesize a more aggressive policy than either source requested.

### Required matrix

- reported PID 1 `kill` plus user-manager `auto` collision;
- conflicting explicit limits;
- system and user withdrawal;
- last-link disconnect;
- reconnect generation overlap;
- PID 1 disconnect/reconnect;
- OOMRules timer transitions;
- cgroup disappearance;
- diagnostic source visibility;
- identical no-op updates preserving pressure timing state.

### Proposed review series

1. model ManagedOOM reporter authorities;
2. derive effective policy from source contributions;
3. withdraw contributions on disconnect;
4. expose policy sources in dump output;
5. cover overlapping reporters across reload.

## First incomplete step

Retrieve the focused VM result and artifact for run `30693755971`.

If the outcome is `reproduced`:

1. retain the first current-main journal and receipt without rewriting it;
2. extract the exact sender/update sequence around the reload;
3. add temporary controlled-fork instrumentation that records reporter identity, path, property, mode, and limit at the oomd receive boundary;
4. rerun only the focused testcase;
5. implement the source-aware model behind unit-tested recomputation helpers;
6. run the complete controlled matrix before shaping a submission series.

If the outcome is `not-reproduced`, compare current main with the public reproducer's versions and identify the commit or environmental condition that changed the behavior.

If the outcome is a control or infrastructure failure, repair the experiment before any product design claim.

## Internal checkpoint

Linux Fieldwork issue `#140` comment `5150858304` records the current-main fork, run identities, corrected prior failure, and source-aware design. This is internal coordination only.

## Scope guard

Keep this lane on ManagedOOM reporter ownership and effective policy. Do not mix in pressure calculation, victim selection, prekill hooks, swap policy, generic Varlink refactors, or unrelated cgroup cleanup.

## Authority

All writes are inside `teamleaderleo/linux-fieldwork` and the controlled `teamleaderleo/systemd` fork. No comment, pull request, review, reaction, patch submission, email, or other action was made in `systemd/systemd`.