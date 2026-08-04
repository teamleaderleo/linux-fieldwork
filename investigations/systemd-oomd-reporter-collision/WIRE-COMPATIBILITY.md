# Wire initialization and mixed-version compatibility

## Status

The policy reducer, lifecycle model, transactional registry, and bounded live source-precedence prototype are independently green in controlled `teamleaderleo/systemd` branches.

The remaining wire problem is not only adding an explicit authoritative snapshot. It is preserving correct behavior when new `systemd-oomd` receives connections from an older user manager.

## Current protocol gap

The current user-manager sender builds its initial complete set with `allow_empty=false`. If no explicit ManagedOOM policy exists, it sends no method call.

A new protocol can add an authoritative snapshot operation that accepts:

```json
{"cgroups": []}
```

That solves empty initialization for new clients. It does not solve an old-client/new-server reconnect by itself.

## Mixed-version failure mode

Consider:

1. generation N is active and owns policy P;
2. generation N+1 connects and becomes pending;
3. the old active connection disconnects;
4. generation N+1 is an older client with an empty policy set, so it sends nothing.

Retaining P forever is stale. Withdrawing P immediately creates an avoidable reconnect gap for clients that will send a complete report shortly.

## Bounded compatibility rule

When an active generation disconnects while a replacement generation is pending:

- retain the old contribution for a bounded initialization grace;
- key the timer to the pending generation;
- cancel the timer when the pending generation completes an explicit snapshot or sends its first legacy non-empty complete report;
- on grace expiry, withdraw the disconnected old contribution while leaving the pending connection alive;
- ignore stale timers after promotion, replacement, or disconnect;
- if the pending connection disconnects after the old active connection, withdraw immediately.

The grace is compatibility behavior only. New clients should send their complete snapshot, including empty, immediately after connect.

## Controlled model

Draft PR: `teamleaderleo/systemd#20`

```text
branch: linux-fieldwork/oomd-wire-init-compat
base:   linux-fieldwork/oomd-reporter-registry@f9bcf18a8ffc6946736791f59c15c35835eba01a
head:   0008f2e6da5073adf6c80945735dfef3f1581cde
run:    30943457230
status: queued
```

The standalone C model covers ten cases:

- new explicit empty snapshot;
- new non-empty replacement;
- replacement after old disconnect without policy gap;
- first legacy non-empty report promotion;
- legacy-empty withdrawal after grace;
- stale grace after successful promotion;
- stale grace after a newer pending generation;
- pending disconnect after old disconnect;
- pending disconnect while old active remains;
- stale disconnect after promotion.

Local compilation used:

```text
cc -std=c11 -O2 -Wall -Wextra -Werror
```

and produced:

```text
FIELDWORK_OOMD_WIRE_INIT_COMPAT=PASSED
```

The GitHub exact-head run is queued and is not yet an authoritative result.

## Integration requirements

A live implementation needs:

1. explicit snapshot method supporting an empty array;
2. legacy first-report detection on a pending link;
3. per-link generation userdata;
4. generation-keyed initialization timer;
5. cancellation before publishing the promoted generation;
6. stale callback and stale timer rejection;
7. transactional policy replacement and lifecycle promotion;
8. contributor diagnostics showing authority, generation, initialization mode, and effective winner.

## Authority

Internal controlled-fork work only. No public upstream contact is authorized or performed.
