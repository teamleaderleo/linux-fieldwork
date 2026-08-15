# Reasoning radius can justify a broader local simplification

## In simple words

A small patch is often a good starting point, but line count and deletion count are poor proxies for review risk.

Sometimes the narrower patch preserves inherited bookkeeping that creates extra intermediate states and extra failure windows. If a slightly broader local change removes those states, stays inside one owner, and makes the lifecycle easier to prove, the broader edit can be the more conservative correctness choice.

This lesson became concrete during review of Cloud Hypervisor QCOW L2 refcount ordering in [PR 8721](https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8721), then repeated in current-main QCOW cache composition and generic bus-map experiments.

## The first case: PR 8721

The original defect was a publication-order problem:

```text
allocate new L2
-> publish L1 pointer
-> apply refcount=1 later
```

A later failure could discard the deferred refcount update while the L1 pointer survived. The first candidate fixed that direct defect by moving new-L2 ownership earlier:

```text
allocate new L2
-> refcount=1
-> publish L1 pointer
```

That first candidate deliberately kept the existing deferred release of an old relocated L2. The reason was ordinary scope discipline: preserve surrounding behavior while repairing the proven ownership gap.

Maintainer review then asked what the remaining deferral actually bought. Once examined as one handoff, the answer was weak. The deferred old-L2 release added caller state and an error window without protecting a distinct compatibility contract.

The surviving implementation therefore became:

```text
allocate replacement L2
-> refcount=1
-> prepare replacement L2 contents
-> switch L1
-> release old L2
```

The transition now lives in `update_cluster_addr()` with no deferred caller bookkeeping.

The compressed-cluster path also moved its data population before this metadata handoff, so the handoff begins only after the replacement data is ready.

## What changed in the review judgment

The first candidate was reasonable. It enforced the proven invariant while minimizing semantic movement.

The later revision became better after review supplied a new discriminator:

> What property does the remaining deferred state protect?

That question turned the scope discussion from “small patch versus rewrite” into “which version has fewer meaningful states?”

The local simplification won because it:

- kept the same operation owner;
- stayed inside the same L1/L2/refcount lifecycle;
- removed a local deferred collection and its unwind behavior;
- reduced the number of partially completed handoff states;
- made failure direction easier to classify;
- retained the existing flush-before-reuse rule;
- remained testable with failure and successful-lifecycle controls.

So the useful size measure was the **reasoning radius**, not the number of deleted lines.

## What later experiments added

PR 8721 supplied the “go one step broader” example. The next Cloud Hypervisor experiments added equally useful stop and split examples.

### QCOW cache composition: broaden until the failure owner changes

Fieldwork #645 repairs a lower-level cache-eviction failure where dirty metadata can disappear before its fallible write succeeds. Composing that repair with PR 8721 required one additional fresh-L2 ordering refinement:

```text
allocate L2
-> refcount=1
-> complete fallible L2-cache insertion
-> publish L1
```

That composition stayed inside the same publication handoff and passed the combined QCOW regression/full-suite matrix.

The next tempting step was rollback: if cache insertion fails after `refcount=1`, undo the refcount too. That would cross into Fieldwork #634, where refcount ownership can recursively allocate and publish refcount blocks. The rollback is therefore no longer a local L2-cache decision.

This gives a clean stop rule:

> Broaden while the change removes a state inside the same failure owner. Stop when cleanup or rollback requires a different transaction owner.

### `Bus::update_range()`: validate before destructive mutation

Current-main Fieldwork #677 found a generic bus move implemented as:

```text
resolve OLD
-> remove OLD
-> insert NEW
```

If NEW overlaps another route, insertion fails after OLD has disappeared. The local repair holds one bus-map write lock, validates NEW against every range except OLD, and only then replaces OLD.

That is another state-deletion win:

```text
historical failure state:
OLD absent + NEW rejected

candidate:
validation failure -> map unchanged
```

The proof gets shorter because the invalid intermediate map no longer exists.

### `Bus::insert()`: check and commit under one lock

Current-main Fieldwork #678 found a sibling concurrency window:

```text
read lock -> validate no overlap
unlock
write lock -> insert
```

A deterministic barrier between validation and insertion lets two concurrent overlapping ranges both pass validation and both commit. Keeping overlap validation and insertion under one write guard closes that window.

The important process decision was to split #678 from #677 even though both live in `vm-device/src/bus.rs`. They share an owner but have different losing mechanisms and discriminators:

```text
#677: failed relocation mutates state before returning an error
#678: concurrent insert separates validation from commit
```

Same file is not sufficient reason to combine claims.

## A practical green light for slightly more ambition

When a bounded correctness fix exposes nearby inherited machinery, inspect one level deeper before freezing the patch boundary.

A local simplification deserves serious consideration when most of these are true:

1. **Same owner.** The original fix and the possible simplification live in the same function, object, lock domain, or tightly coupled caller/callee pair.
2. **Same handoff.** Both changes govern the same resource birth, ownership, publication, replacement, release, or reuse transition.
3. **Same failure boundary.** The extra machinery exists between steps whose partial failure is already part of the bug analysis.
4. **State deletion.** The broader version removes a deferred list, temporary mode, split validation/commit window, callback obligation, duplicated cleanup path, rollback burden, or other intermediate state.
5. **Shorter proof.** The lifecycle can be described with fewer valid intermediate states and fewer special cases after the change.
6. **Bounded compatibility surface.** External formats, APIs, policy, architecture behavior, and unrelated callers stay unchanged.
7. **Executable controls exist.** The historical failure stays dead and the ordinary successful lifecycle remains covered.
8. **Review supplies a real opening.** A maintainer asks why the old mechanism exists, questions its benefit, or explicitly invites cleanup.

This is a green light to investigate the stronger local endpoint. It does not require taking it. Source and tests decide.

## Signals to keep the patch narrow

Scope should stay tight when the next step changes the operation owner or expands the proof dramatically.

Examples:

- externally visible API or format semantics change;
- compatibility depends on old downstream behavior;
- several independent callers rely on the mechanism for different reasons;
- architecture, backend, privilege, or deployment modes gain different behavior;
- deletion crosses into a separate policy decision;
- rollback requires a lower-level transaction owner with its own failure semantics;
- the candidate starts fixing a neighboring defect with a different invariant;
- proving equivalence requires a much larger integration surface than the original bug.

Those cases deserve a successor investigation or separate patch.

## “Rewrite tier” is a reasoning question

Deleting an old mechanism can look like rewrite-tier work during the first source pass. That appearance can discourage a useful simplification before its real radius is understood.

A better question is:

> How many owners, contracts, and lifecycle states must a reviewer understand before and after this change?

A twenty-line deletion inside one serialized metadata handoff can have a smaller review burden than preserving five lines of deferred state whose correctness depends on caller unwinding, later cleanup, flush order, and free-list publication.

Conversely, a tiny edit in a graphics stack, emulator boundary, packaging wrapper, or compatibility layer can have a huge reasoning radius because many consumers and representations meet there.

Treat “rewrite” as a description of changed responsibility and proof radius, not as a synonym for deleting code.

## Why Cloud Hypervisor has been productive for this style of work

Recent Cloud Hypervisor work suggests a useful target characteristic: some high-consequence paths have comparatively compact ownership loops.

QCOW metadata is a strong example. Important questions can often be reduced to explicit state transitions among:

```text
allocation
ownership/refcount
pointer publication
cache dirtiness
flush
release
allocator reuse
reopen/recovery
```

The generic device bus offers another compact loop:

```text
validate range
-> publish route
-> relocate route
-> reject conflict
```

Metadata and routing mutation are concentrated enough that a reviewer can often identify the owner of each transition, force a specific failure or schedule, inspect surviving state, and ask whether the owner’s map still satisfies its own invariant.

That produces an unusually favorable ratio:

```text
bounded local reasoning
+ deterministic failure/schedule injection
+ severe integrity or routing consequence
= high-value investigation
```

The codebase also contains inherited machinery whose original rationale may have weakened as surrounding synchronization, callers, or ownership models changed. That makes “what invariant does this mechanism buy today?” a productive recurring question.

This observation should remain target-specific evidence rather than a promise that every Cloud Hypervisor subsystem is simple. Migration, architecture-specific behavior, device models, firmware, and external interfaces can have much wider compatibility surfaces.

## Process adjustment to use

For future bounded fixes, use a two-pass scope decision.

### Pass 1: prove and repair the invariant

Find the smallest clear owner and establish the direct safe ordering or contract.

### Pass 2: challenge one nearby intermediate state

Before freezing the candidate, ask:

```text
Which surviving intermediate states exist only because the old implementation had them?
What invariant does each one protect today?
Would deleting one make failure reasoning shorter while staying inside the same owner and contract?
```

If the answer points to a smaller state machine, build the slightly broader variant and compare it against the narrow candidate. Keep whichever has the stronger proof and cleaner lifecycle.

Then ask one stop question:

```text
Does the next cleanup, rollback, or adjacent fix still belong to this owner and this invariant?
```

If the answer changes owner or requires a different discriminator, split it.

This keeps the initial discipline that prevents wandering patches while allowing confidence and accumulated project knowledge to produce better local designs.

## Durable rule

Start narrow enough to prove the bug. Then permit one deliberate local scope challenge.

When the broader variant stays inside the same ownership loop and **deletes failure-bearing intermediate state**, judge it by reasoning radius and executable lifecycle evidence. A few more changed lines can produce a smaller correctness problem for both maintainers and future reviewers.

When the next step changes the failure owner or introduces another independently testable invariant, stop and create a successor.

## Related work

- [`lifecycle-tests-cover-failure-and-success.md`](lifecycle-tests-cover-failure-and-success.md) — PR 8721 showed that tests should preserve behavioral lifecycle contracts while implementation-only deferred-state tests can disappear when the staging disappears.
- [`history-can-change-the-repair-boundary.md`](history-can-change-the-repair-boundary.md) — a related lesson from runc: the first correct local repair can be superseded by a cleaner invariant owner after deeper review.
- [`../../investigations/cloud-hypervisor-qcow-r609-review/README.md`](../../investigations/cloud-hypervisor-qcow-r609-review/README.md) — exact-head review record for the QCOW L2 ownership handoff.
- [Fieldwork #645](https://github.com/teamleaderleo/linux-fieldwork/issues/645) — cache-eviction composition proved the failure-owner stop boundary.
- [Fieldwork #677](https://github.com/teamleaderleo/linux-fieldwork/issues/677) — failed `Bus::update_range()` must leave the old route intact.
- [Fieldwork #678](https://github.com/teamleaderleo/linux-fieldwork/issues/678) — concurrent `Bus::insert()` must make overlap validation and insertion one decision.
- [`../../FIELD_GUIDE.md`](../../FIELD_GUIDE.md) — central review guidance; the compact version of this rule belongs there now that it has repeated across several executed cases.

Version boundary: lessons retained through Cloud Hypervisor current main `69d4c0a82ef15b2660906013bd87ae32668e7998` on 2026-08-15.
