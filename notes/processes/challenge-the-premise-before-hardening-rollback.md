# Challenge the premise before hardening rollback

## In simple words

When a failure path needs more locks, rollback bookkeeping, compensation, or transaction state, ask one question before making that machinery stronger:

> **Why does the destructive step have to happen before the fallible work at all?**

Sometimes the rollback exists only because inherited ordering destroys a still-useful state too early. If the later operation can be prepared while the old state remains owned, reversing the order can delete both the failure window and the rollback burden.

This became concrete in Cloud Hypervisor Fieldwork #599.

## The BAR example

Current MMIO BAR relocation inherited this allocator sequence:

```text
free OLD
-> allocate NEW
-> move bus / metadata / KVM / device state
```

That ordering created two classes of repair work:

1. the old address became reusable before old-address ioevent or memslot state was gone;
2. if NEW allocation failed, code had to re-allocate OLD to restore allocator/bus consistency.

The first candidate response was reasonable: use the existing allocator mutex as a long-lived publication lease and re-reserve addresses on error.

Then the scope challenge asked:

> Why must OLD be free for NEW to be allocated?

For MMIO BARs the answer is: it does not.

The source contract gives the missing proof:

```text
BAR size is a power of two
NEW allocator request is aligned to BAR size
OLD and NEW have equal size
```

Two distinct equal-size ranges aligned to their own size cannot partially overlap. A successful NEW MMIO target is therefore disjoint from OLD.

That permits the smaller lifecycle:

```text
OLD stays reserved
-> reserve NEW
-> perform relocation
-> success: free OLD last
```

The long-held allocator mutex disappears. The NEW-allocation failure rollback disappears. The address-reuse publication window disappears.

## History can reveal rollback as a symptom

Cloud Hypervisor history reinforced the point:

- February 2026 consolidated allocator locking around the already-existing free-first sequence. It improved serialization but did not establish a semantic need for free-first.
- May 2026 added OLD re-allocation when NEW allocation failed, repairing a state inconsistency created by having freed OLD first.

That history is a useful smell:

```text
old ordering
-> later patch adds rollback for damage caused by that ordering
```

Before adding another rollback layer, re-evaluate the original ordering premise.

This does not mean every rollback is accidental. It means a growing compensation path is evidence worth tracing backward.

## A practical review sequence

When a candidate starts accumulating rollback machinery:

1. **Name the destructive publication.** What ownership, mapping, file, pointer, lease, or old state becomes unavailable first?
2. **Name the fallible prerequisite that follows it.** What later step can fail and force restoration?
3. **Ask whether the prerequisite can be prepared first.** Can NEW be allocated, validated, populated, inserted, or owned while OLD still exists?
4. **Find the real exclusion rule.** Alignment, identity, lock ownership, uniqueness, generation numbers, or protocol state may prove OLD and NEW can coexist.
5. **Execute both directions.** Success must eventually retire OLD; failure must leave the old contract usable or conservatively owned.
6. **Check history.** A rollback patch may document the original ordering requirement—or merely repair damage from inherited sequencing.
7. **Stop when the proof changes.** Do not generalize a local ordering proof across a different allocator, format, backend, or compatibility contract.

## The stop boundary matters

The same Cloud Hypervisor function has a nearby PIO branch that looks syntactically similar.

The MMIO proof does **not** carry over:

- PIO allocation defaults to byte alignment;
- equal-size PIO ranges can therefore be distinct and partially overlap;
- reserving NEW while OLD remains allocated could reject a move current free-first behavior can represent.

So the correct lesson is not “always allocate NEW first.”

It is:

> **Challenge the destructive premise, then earn the reorder with the actual domain invariant.**

MMIO earned it. PIO did not yet.

## Relationship to reasoning radius

This is a concrete specialization of [`reasoning-radius-can-justify-local-simplification.md`](reasoning-radius-can-justify-local-simplification.md).

The broader-looking MMIO change is easier to review because it removes intermediate states:

```text
free OLD
temporary OLD-free / NEW-absent
restore OLD on allocation failure
long allocator publication window
```

becomes:

```text
OLD owned
OLD + NEW owned
NEW owned
```

The number of changed lines is less important than the number of failure-bearing states the reviewer must prove safe.

## Durable rule

**Before investing in stronger rollback, walk backward and challenge the first irreversible or externally visible step.**

If a later prerequisite can be completed while the old state remains valid, and the coexistence rule is provable from the domain, reordering may be the smaller transaction.

If coexistence depends on a different contract—as with PIO—keep the rollback/scope question separate until that contract has its own discriminator.

Version boundary: lesson recorded from Cloud Hypervisor Fieldwork #599 through 2026-08-15.
