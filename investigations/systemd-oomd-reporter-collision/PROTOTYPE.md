# Current-main reproduction and product prototype

Updated: `2026-08-02 23:40 +08:00`  
State: `ACTIVE — PRODUCT VALIDATION QUEUED`  
Linux Fieldwork issue: `#140`  
External contact: `false`

## Current-main runtime result

The focused controlled-fork VM reproduced the reporter collision with no systemd product-source change.

| Item | Exact value |
| --- | --- |
| Controlled fork | `teamleaderleo/systemd` |
| Source base | `main@6a863b4dc31adc49fdfdd5deba32ed1b115adda3` |
| Probe branch | `linux-fieldwork/oomd-reporter-collision-current-main` |
| Probe branch head | `cd8d4b0873da68866585a610865248d0ed98ef56` |
| PR checkout head recorded by the VM | `ef608bce10e19f55ff355ec893945ec77bd09ab6` |
| Workflow run | `30693755971` |
| Job | `91352945746` |
| Artifact | `8817102322` / `fieldwork-oomd-reporter-collision-30693755971-1` |
| Artifact digest | `sha256:c5257b5e3f230722d50f4f2f8a5a98ff94fc2fdc2644deecd4e9de5cd07c5aa9` |
| Test | `TEST-55-OOMD` |
| Testcase | `user_manager_reload_preserves_system_oomd_registration` |
| Classified outcome | `reproduced` |

The exact runtime sequence was:

1. PID 1 published `/user.slice/user-4711.slice/user@4711.service` with `ManagedOOMMemoryPressure=kill` and a 50% limit.
2. The nested user manager reloaded and published `auto` for its root `-.slice`, which resolves to the same kernel cgroup path.
3. `systemd-oomd` removed the path from its monitored map.
4. `user@4711.service` retained the same `ActiveEnterTimestampMonotonic` value.
5. `NRestarts` remained `0`.
6. PID 1's unit property remained `ManagedOOMMemoryPressure=kill`.
7. The path stayed absent rather than being repopulated after later event-loop turns.

This proves a live policy record was deleted by a different reporting manager. It is more than a display inconsistency.

## Product direction selected

Reject a reload-specific suppression or periodic reassertion workaround. The receive layer needs source ownership.

The first bounded product slice keeps six contribution maps:

```text
SYSTEM_MANAGER × {swap, memory pressure, rules}
USER_MANAGER   × {swap, memory pressure, rules}
```

The three existing monitored maps remain the effective runtime view used by polling, candidate discovery, and action code.

Update contract:

- explicit messages update only the sending source map;
- `auto` removes only the sending source's contribution;
- the affected effective path is recomputed immediately;
- `SYSTEM_MANAGER` wins when both source classes contribute;
- the complete pressure tuple or rules list is selected from one source;
- system withdrawal reveals an already-live user contribution without another user message;
- pressure timing is reset only when the effective pressure tuple changes;
- rule timers are cleared only for rules that leave the effective list.

## Controlled-fork prototype

| Item | Exact value |
| --- | --- |
| Branch | `linux-fieldwork/oomd-reporter-source-precedence` |
| Current head | `7186e5a140df4f646e9bd0ceb90302c6c362dc16` |
| Internal draft PR | `teamleaderleo/systemd#2` |
| Product injector | `tools/fieldwork-apply-oomd-reporter-source-precedence.py` plus corrected call-anchor wrapper `...-v2.py` |
| Reload regression injector | `tools/fieldwork-inject-oomd-reporter-collision.py` |
| Transition regression injector | `tools/fieldwork-inject-oomd-source-precedence-transitions.py` |
| Focused workflow | `.github/workflows/fieldwork-oomd-reporter-source-precedence.yml` |
| Exact focused run | `30755078046` |

The injector fails closed when source anchors drift. It modifies only:

- `src/oom/oomd-manager.c`;
- `src/oom/oomd-manager.h`.

The workflow applies the product prototype in a disposable checkout, compiles `systemd-oomd` with `--werror`, runs existing `test-oomd-util`, builds the integration image, and runs two focused VM testcases.

## Focused regression matrix

### Reported reload case

- PID 1: `kill`, 50%;
- user-manager reload: `auto` for the same path;
- expected: 50% remains effective, unit identity and configured property stay stable.

### Authority and fallback transitions

1. PID 1 contributes `kill`, 50%.
2. The user manager contributes `kill`, 70% for the same path through root `-.slice`.
3. Expected: 50% remains effective.
4. PID 1 changes only its contribution to `auto`.
5. Expected: the existing 70% user contribution becomes effective without a new user update.
6. The user manager changes its contribution to `auto`.
7. Expected: the path leaves the monitored set.

This test fails the old path-only representation both when the user contribution overwrites PID 1 and when PID 1 withdrawal deletes the user's still-live contribution.

## Source-review findings

- `oomd_cgroup_ctx_hash_ops` owns values through `oomd_cgroup_context_unref`, so the additional maps have the same cleanup contract as existing monitored maps.
- `oomd_insert_cgroup_context()` preserves policy fields when refreshing runtime metrics.
- the polling and action paths can remain on the existing effective maps;
- root user managers are classified by Varlink channel, not UID, so UID 0 does not acquire system-manager authority;
- field-wise minimum merging was rejected because it can synthesize a pressure policy no reporter requested.

A pre-run review found and corrected one injector defect: the source has one return-site and one assignment-site for `process_managed_oom_message()`. The first injector expected two return-sites and would have failed closed before changing source. The corrected wrapper matches the common call expression while preserving each surrounding statement.

## Known incomplete boundary

The first slice models source class and precedence, but it does not yet withdraw contributions when a reporter connection disappears.

Required follow-on before an upstream-shaped patch is complete:

- track user-manager authority by `(USER_MANAGER, uid)` rather than one shared user map;
- retain live connection generations;
- withdraw an authority's contributions on its last disconnect;
- withdraw PID 1 contributions when the observed subscription terminates;
- reveal surviving lower-authority contributions after disconnect;
- remove stale contributions when the cgroup disappears;
- expose effective source and live contributors in `oomctl` diagnostics.

The current prototype is therefore a testable first product slice, not a final submission candidate.

## Current gate

Run `30755078046` is queued. Success requires all of:

- fail-closed source injection;
- `git diff --check`;
- `systemd-oomd` compile with `--werror`;
- existing `test-oomd-util` pass;
- reported reload testcase pass;
- source precedence and fallback transition testcase pass;
- exact guest journal and generated product diff retained as an artifact.

No pass is claimed until the exact run and artifact are inspected.

## Authority

All mutations are confined to `teamleaderleo/linux-fieldwork` and `teamleaderleo/systemd`. No issue comment, pull request, review, reaction, email, or other contact was made in `systemd/systemd`.
