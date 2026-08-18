# OOMD reporter link adapter

Updated: `2026-08-05`  
Controlled draft: `teamleaderleo/systemd#23`  
Branch: `linux-fieldwork/oomd-link-adapter`  
External contact: `false`

## Purpose

This lane is the boundary between the exact-head-green reporter registry/grace components and a future live `oomd-manager.c` Varlink integration.

It does not yet bind `sd_varlink_server` callbacks or schedule real `sd_event` timers. It proves the state machine that those callbacks must drive.

## Input and output contract

A live link is identified by an adapter link ID and mapped to a registry-generated reporter session:

```text
(authority, generation)
```

The adapter classifies operations as:

- connection begin;
- first complete snapshot, including empty state;
- later incremental update;
- link disconnect;
- generation-keyed compatibility-grace expiry.

Timer events are explicit:

```text
NO_ACTION
ARM_OR_REPLACE_GRACE(authority, generation)
CANCEL_GRACE(authority, generation)
```

Both arm and cancel identify the exact token. A timer owner must never cancel or expire grace by authority alone.

## Required behavior

- a new link is pending until its first complete snapshot;
- the pending link cannot send incrementals;
- a still-connected old active link remains writable during the pending handshake;
- first-snapshot commit atomically promotes the new generation and makes the old generation stale;
- active disconnect with a pending replacement arms grace for the pending generation;
- a newer pending link replaces that grace token;
- matching expiry withdraws disconnected old policy but leaves the pending link able to initialize later;
- stale expiry, stale disconnect, and stale snapshot operations do not alter current policy;
- pending disconnect preserves a connected active reporter but withdraws retained disconnected policy;
- link records are removed after successful disconnect;
- link IDs remain reserved while still referenced as active or pending authority identity, including the retained-active grace interval.

## Independent repairs before first receipt

### Unbounded disconnected-link storage

The first adapter kept every disconnected link forever in order to reject ID reuse. That would grow without bound in a long-running daemon.

The adapter now removes the live link record after the registry disconnect transaction succeeds. A separate generation in the registry remains the stale-session guard.

### Retained-active ID alias

Releasing the link record alone was insufficient. During grace, the authority still refers to the disconnected active link identity. Reusing that ID for a new pending link could alias active and pending bookkeeping.

Connection admission now rejects an ID referenced by either a live link or an authority's active/pending identity. The ID becomes reusable only after snapshot promotion, matching grace expiry, pending disconnect, or ordinary final disconnect clears the reference.

### Ambiguous timer cancellation

The first cancel event did not identify which generation to cancel. This is unsafe with multiple authorities or superseded queued timers.

Arm and cancel events now both carry the exact reporter session token.

### False dirty-tree workflow failure

The first workflow wrote compiler/test logs inside the checkout and then required an empty `git status`. Evidence now lives under the runner temporary directory.

### Stacked-PR trigger dependence

The focused workflow did not reliably re-run for every stacked-branch update. It now also runs on exact branch pushes.

## Focused tests

```text
test-oomd-reporter-adapter
test-oomd-reporter-adapter-reuse
test-oomd-reporter-adapter-events
```

The matrix covers:

- explicit empty first snapshot;
- connected-active continuity while replacement is pending;
- pending-generation incremental rejection;
- complete snapshot promotion and old-generation rejection;
- grace arm, replacement, cancellation, expiry, and stale expiry;
- late first snapshot after grace expiry;
- pending disconnect before and after active disconnect;
- bounded link-record lifetime;
- safe ID reuse after all references clear;
- ID reservation during retained-active grace;
- exact cancellation-token identity.

## Current head and gate

```text
head: 6180f35f349a65856ec51bf59e7297cae617cf0a
workflow: Fieldwork OOMD link adapter
status: exact-head result pending at this checkpoint
```

No compile or behavioral pass is claimed for this head until the focused workflow completes and its artifact is inspected.

## Production boundary still remaining

The next live lane must:

1. allocate/store adapter identity in each accepted Varlink link;
2. derive user authority from authenticated peer UID;
3. classify the first method call as a complete snapshot;
4. route later calls as incrementals;
5. translate adapter timer actions into one generation-qualified `sd_event` timer per authority;
6. bind disconnect callbacks and cancel/re-arm timers exactly;
7. model PID 1's subscription as the system reporter;
8. publish registry effective decisions into existing monitored maps without losing timer state;
9. add contributor diagnostics;
10. run a native VM matrix.

## Authority

Internal controlled-fork work only. No action has occurred in `systemd/systemd`.
