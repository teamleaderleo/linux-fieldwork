# Current-main VM baseline — reporter collision reproduced

Date: `2026-08-01`  
Controlled fork: `teamleaderleo/systemd`  
Fork PR: `#1`  
Focused workflow run: `30693755971`, attempt `1`  
Artifact: `8817102322`  
Artifact name: `fieldwork-oomd-reporter-collision-30693755971-1`  
Artifact ZIP SHA-256: `c5257b5e3f230722d50f4f2f8a5a98ff94fc2fdc2644deecd4e9de5cd07c5aa9`

## Result

`REPRODUCED` on the current-main product source used by the controlled fork.

The focused `TEST-55-OOMD` testcase exited `1` because the monitored entry vanished. The classifier treated that expected nonzero test result as a successful experiment after validating the service-identity and configured-policy controls.

## Baseline before reload

The exact monitored block existed for:

```text
/user.slice/user-4711.slice/user@4711.service
```

with:

```text
Memory Pressure Limit: 50.00%
Memory Pressure Duration: 2s
```

## Exact causal ordering

The guest journal establishes reporter and receive order without relying only on source inference:

1. At `9.523264`, the user manager (`systemd[252]`) queued a one-way `ReportManagedOOMCGroups` call for its root path with `ManagedOOMMemoryPressure=auto`.
2. At `9.526873`, PID 1 queued its continued-subscription update for the same path with `ManagedOOMMemoryPressure=kill` and the encoded 50% limit.
3. At `9.527279`, `systemd-oomd[387]` received PID 1's `kill` update.
4. At `9.552473`, `systemd-oomd[387]` received the user manager's `auto` method call.
5. The later user-manager update therefore won solely because the effective map is keyed by property and path, not reporter.
6. At `10.524699`, the +1 second `oomctl` lookup returned no block for the path.

The destructive receive ordering is therefore:

```text
PID 1 KILL received
        ↓ 25.194 ms
user-manager AUTO received
        ↓
effective path removed
```

## Controls

The monitored entry disappeared without a service or property transition:

```text
ActiveEnterTimestampMonotonic before=6615081 after=6615081
NRestarts before=0 after=0
ManagedOOMMemoryPressure before=kill after=kill
```

The final guest marker was:

```text
FIELDWORK_OOMD_REPORTER_COLLISION=REPRODUCED
```

## Exact receipt

The raw receipt is retained beside this note as:

```text
artifacts/2026-08-01-current-main-vm-receipt.json
```

The normalized causal trace is retained as:

```text
artifacts/2026-08-01-current-main-causal-trace.txt
```

Downloaded artifact file hashes:

```text
receipt.json          647d9312a372f4b48105f76249bbfcef0cfae1e482da7a98dedbedf6c43dceae
regression.diff       057b19dd2a184e411ff6454eddda9c38ed98159f0440382ad564365da6bc0ea4
meson-test.txt        eba222a6789fa578c84caf2712174e55c655cfbc514bb4c85ebc5bd8e9284156
guest-journal.txt     65ab299cf8b03024d8a995d35317da3fbb1e5851f5a188818c7d8a13e94e6d7f
test-exit-status.txt  4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865
```

## Source identity qualification

The pull-request workflow used the default checkout behavior and therefore ran at GitHub's synthetic merge commit:

```text
ef608bce10e19f55ff355ec893945ec77bd09ab6
```

Its base parent was canonical systemd main:

```text
6a863b4dc31adc49fdfdd5deba32ed1b115adda3
```

The controlled head contribution contained only the Fieldwork workflow and injector files; product source was unchanged. The receipt correctly records the synthetic merge SHA. Future runs must explicitly check out the PR head SHA so execution identity is direct rather than merge-derived.

## Public overlap check

At the time this evidence was folded back, `systemd/systemd#43174` remained open, unassigned, and had no comments. No competing patch or maintainer direction was present.

## Consequence for design

The runtime result confirms the source-aware model is necessary. A receive-path exception such as “ignore user `auto` for this path” would fix one manifestation but leave unresolved:

- conflicting explicit policies;
- reporter disconnect and reconnect;
- stale contributions after connection loss;
- authority transitions;
- diagnostic visibility.

Proceed with reporter-aware contributions and derived effective policy as specified in `DESIGN.md`.

## Authority

All execution and writes occurred in `teamleaderleo`-owned repositories. No upstream issue comment, pull request, review, reaction, email, or other contact was made.
