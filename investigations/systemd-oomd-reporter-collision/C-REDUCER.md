# Compile-first C policy reducer

Updated: `2026-08-02`  
Controlled fork PR: `teamleaderleo/systemd#3`  
Branch: `linux-fieldwork/oomd-policy-reducer`  
Current reviewed head: `0209288b98cefb2add224f26fba88187aba45b77`  
External contact: `false`

## Purpose

Validate the source-aware policy model as a standalone systemd C component before integrating `oomd-manager.c`, Varlink sessions, live cgroup contexts, or timers.

The branch is intentionally compile-first and manager-independent. It should answer:

- whether the authority/property/value API fits systemd conventions;
- whether complete snapshot replacement can be made atomic with simple ownership;
- whether source precedence and fallback are expressible without live cgroup state;
- whether focused unit tests can define the product semantics before manager integration.

## Files

```text
src/oom/oomd-policy.h
src/oom/oomd-policy.c
src/oom/test-oomd-policy.c
src/oom/meson.build
.github/workflows/fieldwork-oomd-policy-reducer.yml
```

## Data model

Public types:

```text
OomdReporterAuthority = (SYSTEM_MANAGER | USER_MANAGER, uid)
OomdPolicyProperty    = swap | memory-pressure | rules
OomdPolicyValue       = pressure limit, duration, complete rules list
OomdPolicyDecision    = winning authority plus copied complete value
```

The first implementation stores owned typed contributions in a compact array.

This is not the intended final indexing structure. The array keeps the first compile boundary small and makes copy-and-swap transactions obvious. A typed hashmap can replace it after semantics and ownership compile cleanly.

## Atomicity

Incremental update:

1. allocate a candidate array;
2. deep-copy every contribution except the exact replaced/withdrawn key;
3. append the replacement if present;
4. publish by swapping the candidate into the store only after all copies succeed;
5. free the old array after publication.

Complete snapshot:

1. allocate a candidate array;
2. copy contributions belonging to other authorities;
3. validate and deep-copy every snapshot entry;
4. reject duplicate `(property, path)` keys;
5. publish only after the full snapshot succeeds.

Any validation or allocation failure leaves the original store unchanged.

## Reduction rule

```text
SYSTEM_MANAGER > USER_MANAGER
```

One complete value wins. Pressure limit and duration are never mixed between reporters, and rules lists are never unioned.

Equal-rank contributions from different user UIDs for the same `(property, path)` return `-ENOTUNIQ` rather than using message arrival order.

## Focused tests

`test-oomd-policy` covers:

1. system policy selects one complete pressure tuple;
2. user withdrawal cannot remove system policy;
3. system withdrawal reveals the existing user contribution;
4. complete snapshot replacement;
5. empty snapshot withdrawal;
6. duplicate snapshot rejection with old-state preservation;
7. complete OOMRules selection without union;
8. equal-rank different-user ambiguity.

## Validation workflow

The focused workflow:

- checks out the exact PR head;
- verifies `git rev-parse HEAD == EXPECTED_HEAD`;
- uses systemd's pinned mkosi action;
- configures an Arch tools tree with tests and `--werror`;
- compiles only `test-oomd-policy`;
- runs only `test-oomd-policy`;
- runs `git diff --check`;
- uploads compile/test logs and a direct-head receipt.

Initial focused run from head `0d2037f46fc89d676d33df5080f4d43ee5ae1571`:

```text
30756149846 — queued at the last check
```

Header dependency cleanup moved the branch to:

```text
0209288b98cefb2add224f26fba88187aba45b77
```

Use the newest workflow run attached to that head as the authoritative reducer result. Do not treat `30756149846` as final if it executes the older head.

## Pre-CI review

Confirmed against current systemd source:

- `ASSERT_ERROR(expression, ERRNO)` usage matches the new tests;
- the Meson test target should be inferred as `test-oomd-policy` from the source filename;
- the public header now explicitly includes fixed-width, size, time, and UID helpers;
- rules are deep-copied with `strv_copy()` and decisions own their copied result;
- invalid or duplicate snapshots are staged and cannot mutate the current store.

Open compile-risk items are intentionally left to the focused compiler:

- exact zero-length allocation behavior under systemd allocation macros;
- whether imported `systemd-oomd` export sources expose the new reducer target exactly as expected;
- warnings produced by pointer arithmetic in the duplicate-snapshot loop;
- any style or signedness diagnostics under `--werror`.

No green claim is made before logs exist.

## Local execution limitation

The container cannot resolve `github.com`:

```text
fatal: unable to access 'https://github.com/teamleaderleo/systemd.git/':
Could not resolve host: github.com
```

Therefore no independent local clone or compile receipt exists. The direct-head GitHub workflow is the authoritative compile gate.

## Deliberate boundary

This branch does not modify:

- `oomd-manager.c` receive behavior;
- Varlink connect/disconnect handling;
- initial snapshot messages;
- reporter session generations;
- effective monitored cgroup maps;
- pressure/rules timing state;
- cgroup disappearance cleanup;
- `oomctl` diagnostics.

Those remain follow-on integration layers after the reducer compiles.

## Authority

All code and validation live in `teamleaderleo`-owned repositories. No action was taken in `systemd/systemd`.
