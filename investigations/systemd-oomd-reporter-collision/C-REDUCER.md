# Compile-first C policy and reporter-lifecycle models

Updated: `2026-08-04`  
Controlled fork PR: `teamleaderleo/systemd#3`  
Branch: `linux-fieldwork/oomd-policy-reducer`  
Independent review: `INDEPENDENT-REVIEW-2026-08-04.md`  
External contact: `false`

## Purpose

Validate source-aware ManagedOOM policy reduction and connection-generation semantics as isolated systemd C components before integrating `oomd-manager.c`, live Varlink callbacks, effective cgroup contexts, or timers.

## Current authoritative exact-head gate

```text
head:      76749bfd3dda498c15a88c4e572340d8ade3e82b
run:       30915443613
artifact:  8894962609
digest:    sha256:a9e87098bcd7c9ef5ad154e2e884150233ed0cb09a53c203b378a1dc28db5f37
build:     567/567
focused:   2/2 Meson tests passed
identity:  direct-controlled-fork-head
```

Focused targets:

```text
test-oomd-policy
test-oomd-reporter-lifecycle
```

Receipt:

```text
policy model:       typed-array copy-and-swap reducer
lifecycle model:    two-phase generation-safe reporter transitions
manager_integration=false
external_contact=false
```

Disposition:

`GREEN FOR THE BOUNDED POLICY-REDUCER AND REPORTER-LIFECYCLE MODEL SLICE; NOT INTEGRATED INTO LIVE SYSTEMD-OOMD.`

## Policy data model

```text
OomdReporterAuthority = (SYSTEM_MANAGER | USER_MANAGER, uid)
OomdPolicyProperty    = swap | memory-pressure | rules
OomdPolicyValue       = complete pressure tuple or complete rules list
OomdPolicyDecision    = winning authority plus owned copied value
```

The first implementation stores owned typed contributions in a compact array. That makes copy-and-swap ownership and transaction boundaries explicit; it is not a claim that O(n) lookup is the final indexing choice.

## Reduction rule

```text
SYSTEM_MANAGER > USER_MANAGER
```

One complete value wins. Pressure limit and duration are never mixed between reporters, and rules lists are never unioned.

Conflicting equal-rank user authorities for the same `(property, path)` return `-ENOTUNIQ` rather than selecting by arrival order.

## Policy atomicity

Incremental update:

1. validate authority, property, path, and value representation;
2. deep-copy a candidate store without the replaced exact key;
3. append the replacement when present;
4. publish only by swapping the complete candidate;
5. free old state after publication.

Complete snapshot:

1. validate authority;
2. deep-copy other authorities' contributions;
3. validate and deep-copy every snapshot entry;
4. reject duplicate `(property, path)` keys;
5. publish only after the whole snapshot succeeds.

Validation or allocation failure leaves the original store unchanged.

## Reporter lifecycle model

Per authority, the model retains:

```text
last_generation
active_generation
pending_generation
```

Transitions are prepared first and committed only after the caller applies the corresponding policy-store transaction.

Required behavior:

- a new connection receives a monotonic pending generation;
- its first complete snapshot promotes it to active and makes older generations stale;
- only the active stable generation may send incremental updates;
- stale updates and stale disconnects return `-ESTALE` without changing policy;
- disconnecting the current generation withdraws that authority;
- disconnecting a pending replacement does not disturb an older active generation;
- disconnecting an older active link while a replacement is pending does not allow that stale link to withdraw the authority;
- if the replacement also disappears before promotion and no valid current link remains, the old authority is withdrawn.

The model deliberately retains old active policy while a replacement connection is pending. Live integration must therefore guarantee an authoritative first snapshot—including empty state—or otherwise bound the pending handshake. This branch does not claim that wire behavior is implemented.

## Independent review findings and repairs

### Highest-rank insertion order

The original reducer returned `-ENOTUNIQ` immediately after two conflicting users, without considering a later higher-ranked system contribution. Ambiguity is now tracked only at the highest rank seen.

### Invalid snapshot iteration

`FOREACH_ARRAY(candidate + keep, ...)` did not compile. Duplicate detection now uses an indexed loop.

### Malformed typed values

The reducer now rejects:

- a system-manager authority with nonzero UID;
- an invalid user UID;
- pressure properties carrying rules;
- rules properties carrying pressure fields.

Incremental and complete-snapshot rejection are tested as atomic. Numeric policy ranges and wire-format parsing remain at the Varlink/parser boundary.

### Moving-head lifecycle failures

An incomplete commit first referenced lifecycle source files that did not exist. Those dangling references were removed at `731d633b05d29158ebcb78f59f42d943fab3930f`, whose reducer-only run `30914688124` passed.

Once lifecycle sources were added, their focused workflow requested `test-oomd-reporter-lifecycle` but Meson did not define or link the target. Commit `76749bfd3dda498c15a88c4e572340d8ade3e82b` wired the lifecycle source into the exported objects and added the test target. The exact-head gate above then compiled 567/567 steps and passed both tests.

Older green receipts remain historical and are not attributed to later heads.

## Focused test matrix

`test-oomd-policy` covers:

1. whole-tuple system precedence;
2. user withdrawal cannot remove system policy;
3. system withdrawal reveals live user fallback;
4. complete snapshot replacement;
5. empty snapshot withdrawal;
6. duplicate snapshot rollback;
7. complete OOMRules selection without union;
8. equal-rank ambiguity;
9. insertion-order-independent higher-rank selection;
10. malformed pressure rejection is atomic;
11. malformed rules rejection is atomic;
12. malformed snapshot rejection is atomic;
13. invalid authority rejection.

`test-oomd-reporter-lifecycle` covers first snapshot promotion, reconnect replacement, stale updates/disconnects, pending disconnects, current disconnect withdrawal, old active disconnect during replacement, and incremental acceptance only from the current stable generation.

## Deliberate boundary

This branch does not implement:

- `oomd-manager.c` receive-path integration;
- live Varlink connect/disconnect callbacks;
- authoritative snapshots on the wire;
- effective monitored cgroup maps;
- pressure/rules timer preservation;
- cgroup disappearance cleanup;
- `oomctl` source diagnostics.

## Authority

All code, review, and validation live in `teamleaderleo`-owned repositories. No action was taken in `systemd/systemd`.
