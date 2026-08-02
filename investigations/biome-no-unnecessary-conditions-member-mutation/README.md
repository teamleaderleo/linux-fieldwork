# Biome `noUnnecessaryConditions`: mutated member retains literal truthiness

State: `ACTIVE — LOSING TEST MATERIALIZED`  
Programme: `ecosystem-contributions` + `services-resources`  
LF-35 round: `002`  
Worker or variant: `LF-R02`  
External contact authorized: `false`

## TL;DR

Biome issue #11174 reports that `noUnnecessaryConditions` treats a mutable object property as permanently equal to its literal initializer. A guard initialized with `false`, checked, and later assigned `true` is reported as always false, while the equivalent reassigned binding is already exempted.

A controlled branch now adds only a valid-rule fixture covering direct properties, generic ref-like properties, numeric truthiness, and a true-to-false mutation. No implementation has been selected and no test run has been claimed.

## Explain like I'm five

A light starts off. The program can turn it on later. The linter sees that it started off and says checking the light is pointless, even though the switch works.

## Why care

The diagnostic is a false positive on real guard patterns such as `useRef(false)`. Acting on it can remove a working re-entry or duplicate-submission guard. The rule has no safe automatic fix here, so users must suppress a diagnostic that contradicts reachable runtime state.

## Exact identities

| Item | Exact value |
| --- | --- |
| Upstream repository | `biomejs/biome` |
| Current upstream base | `9847e680ff8bb891a6c910e881af98a4fffa33c2` |
| Base message | `feat(lint): add noNonScalableViewport rule (#11168)` |
| Controlled fork | `teamleaderleo/biome` |
| Snapshot branch | `linux-fieldwork/upstream-main-20260802` |
| Investigation branch | `linux-fieldwork/biome-11174-member-mutation` |
| Test-only head | `468b97947271255528cbb53caddb10831db18ea7` |
| Changed-file fence | `crates/biome_js_analyze/tests/specs/suspicious/noUnnecessaryConditions/memberMutationValid.ts` |
| Source owner | `crates/biome_js_analyze/src/lint/suspicious/no_unnecessary_conditions.rs` |
| Source blob | `1fffe5c730b59829683bb706c34ccae4edc5b4c0` |
| Existing valid-fixture owner | `crates/biome_js_analyze/tests/specs/suspicious/noUnnecessaryConditions/valid.ts` |
| Existing valid-fixture blob | `f5ec598be408a63e713e03e53b1ad0ff626482e4` |

## Current public state

Checked 2026-08-02:

- issue #11174 is open;
- no assignee is recorded;
- labels are `S-Needs response` and `S-Needs triage`;
- seven comments are recorded;
- no pull request referencing `11174` was found in the repository search.

This is recent, unowned public work. The investigation must still recheck overlap immediately before selecting or publishing a correction.

## Observed mechanism

The rule documentation already states that reassigned bindings with different truthiness should not be reported because their narrowing cannot be inferred reliably. The issue demonstrates that this exemption does not extend to mutable member expressions: the inferred property type remains the initializer literal while later writes are ignored for the condition decision.

The correction boundary is not automatically “widen every property.” That could suppress valid diagnostics on immutable object literals or properties whose writes cannot affect the observed object. The first source question is narrower:

> Can the existing reassignment safety policy recognize writes to the same statically resolved member without broadening unrelated member types?

## Losing test branch

Commit `468b97947271255528cbb53caddb10831db18ea7` adds one fixture intended to produce no diagnostics. It covers:

- `{ current: false }`, tested before assignment to `true`;
- a declared `useRef<boolean>(false)` shape;
- numeric `0` to `1` mutation;
- `true` to `false` mutation.

Comparison against exact upstream base is one commit ahead, zero behind, and adds only the 28-line fixture.

## First distinguishing probe

On a clean checkout of exact base and then the test-only branch:

```sh
cargo test -p biome_js_analyze no_unnecessary_conditions
```

Required interpretation:

- baseline existing suite passes;
- test-only branch must fail because the new “valid” fixture emits one or more diagnostics;
- retain the exact generated snapshot or diagnostic text;
- rerun immediately to prove deterministic output;
- remove generated unapproved snapshots before stopping.

The project requires tests for every code change, `just f`, and `just l` before committing an implementation. A user-facing bug fix also requires a patch changeset. Those gates remain unexecuted.

## Candidate design discriminators

A correction is acceptable only if it passes all of these controls:

1. mutated direct and ref-like members are not reported as constant;
2. an immutable or never-mutated literal property remains reportable;
3. a property assigned only values with the same truthiness remains reportable when analysis can prove that safely;
4. plain binding reassignment behavior remains unchanged;
5. optional-chain, comparison, switch-case, and nullish checks owned by the same rule remain unchanged;
6. the implementation does not globally widen object property inference.

## Stop and promotion rules

Promote to a source candidate when the losing test runs on exact current head and one bounded write-tracking or conservative-suppression rule wins the controls above.

Stop duplicate implementation if an equivalent current PR appears. Convert to a type-inference investigation if the rule cannot distinguish member mutation without changing shared inferred-type ownership.

## Authority

Internal reads, branches, test fixtures, source experiments, and Fieldwork records are authorized. No upstream issue, pull request, comment, review, reaction, or other contact has been made or authorized.
