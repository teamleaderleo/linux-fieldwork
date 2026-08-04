# Compile-first C policy reducer

Updated: `2026-08-04`  
Controlled fork PR: `teamleaderleo/systemd#3`  
Branch: `linux-fieldwork/oomd-policy-reducer`  
Independent review: `INDEPENDENT-REVIEW-2026-08-04.md`  
External contact: `false`

## Purpose

Validate the source-aware ManagedOOM policy model as a standalone systemd C component before integrating `oomd-manager.c`, Varlink sessions, live cgroup contexts, or timers.

The branch deliberately answers the ownership and reduction questions first:

- can reporter authority be represented explicitly;
- can complete pressure/rules values be selected without field mixing;
- can incremental updates and complete snapshots be atomic;
- can system precedence, user fallback, and equal-rank ambiguity be tested without live daemon state.

## Last proven exact head

```text
head:      d9b5cd00c0899bacd9637fcc466ac01a9b841bca
run:       30913524283
artifact:  8894149501
digest:    sha256:db18d59e172da1b3d537cbd055685b4b5191d1f48607a845374edae29b52f5bc
build:     564/564
focused:   1/1 Meson test passed
identity:  direct-controlled-fork-head
```

The retained receipt says:

```text
model=typed-array copy-and-swap reducer
manager_integration=false
external_contact=false
```

Disposition at that head:

`GREEN FOR THE BOUNDED REDUCER SEMANTIC SLICE; NOT INTEGRATED INTO LIVE SYSTEMD-OOMD.`

## Current branch head

An incomplete follow-on commit temporarily moved the branch to `fb8fcebb3ab0e8a7d32a6298048e6ba13f02162a` and added Meson references to:

```text
oomd-reporter-lifecycle.c
test-oomd-reporter-lifecycle.c
```

Neither file existed at that head. The dangling target made the branch unbuildable and also violated this branch's declared reducer-only boundary.

The references were removed at:

```text
731d633b05d29158ebcb78f59f42d943fab3930f
```

That repair head requires its own exact-head workflow result. The green receipt for `d9b5cd0…` must not be attributed to `731d633…` until the new run completes.

## Files in the reducer slice

```text
src/oom/oomd-policy.h
src/oom/oomd-policy.c
src/oom/test-oomd-policy.c
src/oom/meson.build
.github/workflows/fieldwork-oomd-policy-reducer.yml
```

## Data model

```text
OomdReporterAuthority = (SYSTEM_MANAGER | USER_MANAGER, uid)
OomdPolicyProperty    = swap | memory-pressure | rules
OomdPolicyValue       = complete pressure tuple or complete rules list
OomdPolicyDecision    = winning authority plus owned copied value
```

The first implementation stores owned typed contributions in a compact array. This is deliberate: the array makes copy-and-swap ownership and transaction boundaries obvious. It is not a claim that O(n) lookup is the final indexing choice.

## Reduction rule

```text
SYSTEM_MANAGER > USER_MANAGER
```

One complete value wins. Pressure limit and duration are never mixed between reporters, and rules lists are never unioned.

Conflicting equal-rank user authorities for the same `(property, path)` return `-ENOTUNIQ` rather than selecting by message order.

## Atomicity

Incremental update:

1. validate the authority, property, path, and value representation;
2. allocate and deep-copy a candidate array without the exact replaced key;
3. append the replacement when present;
4. publish only by swapping the complete candidate into the store;
5. free old state after publication.

Complete snapshot:

1. validate the authority;
2. deep-copy contributions from other authorities;
3. validate and deep-copy every snapshot entry;
4. reject duplicate `(property, path)` keys;
5. publish only after the complete snapshot succeeds.

Validation or allocation failure leaves the original store unchanged.

## Independent review findings and repairs

### Highest-rank insertion order

The original effective-selection loop returned `-ENOTUNIQ` immediately after encountering two conflicting user authorities. A higher-ranked system contribution stored later was never considered.

The reducer now tracks ambiguity only at the highest rank seen. Discovering a higher rank resets lower-rank ambiguity. A regression inserts two conflicting users first and the system contribution last.

### Invalid snapshot iteration

The first duplicate check used:

```c
FOREACH_ARRAY(existing, candidate + keep, n_candidate - keep)
```

That macro requires an array/pointer identifier form and did not compile. The duplicate check now uses an indexed loop.

### Malformed typed values

The reducer originally accepted invalid authority/value combinations. It now rejects:

- a `SYSTEM_MANAGER` authority with nonzero UID;
- an invalid user UID;
- pressure properties carrying a rules list;
- rules properties carrying pressure fields.

Incremental and complete-snapshot rejection are tested as atomic.

The reducer validates representation and ownership invariants. Numeric policy ranges and wire-format parsing remain the responsibility of the Varlink/parser boundary rather than being duplicated here.

## Focused test matrix

`test-oomd-policy` covers:

1. system precedence selects a complete pressure tuple;
2. user withdrawal cannot remove system policy;
3. system withdrawal reveals an existing user contribution;
4. complete snapshot replacement;
5. empty snapshot withdrawal;
6. duplicate snapshot rejection with old-state preservation;
7. complete OOMRules selection without union;
8. equal-rank user ambiguity;
9. later system authority resolves earlier user ambiguity independent of insertion order;
10. malformed incremental pressure rejection is atomic;
11. malformed incremental rules rejection is atomic;
12. malformed complete-snapshot rejection is atomic;
13. invalid authorities are rejected.

## Deliberate boundary

This branch does not implement:

- `oomd-manager.c` receive-path integration;
- Varlink connect/disconnect handling;
- authoritative first snapshots;
- reporter connection generations;
- effective monitored cgroup maps;
- pressure/rules timer preservation;
- cgroup disappearance cleanup;
- `oomctl` source diagnostics.

Those remain integration work after the reducer's current repair head is independently green.

## Authority

All code and validation live in `teamleaderleo`-owned repositories. No action was taken in `systemd/systemd`.
