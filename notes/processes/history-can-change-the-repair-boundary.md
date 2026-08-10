# History can change the repair boundary

## In simple words

A bug can be diagnosed correctly from the current code while the best fix still lives one step earlier in the history.

A runc CPU-mask report found a real off-by-one: `configs.MaxCPU` was documented as the highest accepted CPU ID, while `unix.NewCPUSet` takes an exclusive upper bound. The first candidate therefore changed `NewCPUSet(MaxCPU)` to `NewCPUSet(MaxCPU + 1)`.

That local fix followed the current contract. The stronger fix came from reading the change that introduced the mismatch. Two values that both happened to equal `64 * 1024` had originally represented different things: a mask capacity and a highest accepted identifier. They were later unified into one exported constant. The maintainer repaired that semantic collision by making `MaxCPU` exclusive everywhere.

The lesson is useful beyond runc: when a defect appears around a recent refactor, type migration, or constant reuse, inspect the introducing history before choosing the repair boundary.

## What happened in runc

The sequence was:

1. [runc issue 5388](https://redirect.github.com/opencontainers/runc/issues/5388) reported that the reset mask omitted the CPU ID documented as `configs.MaxCPU`.
2. [runc PR 5389](https://redirect.github.com/opencontainers/runc/pull/5389) proposed the direct repair: allocate the reset mask with `configs.MaxCPU + 1` and add a boundary regression test.
3. The maintainer preferred [runc PR 5392](https://redirect.github.com/opencontainers/runc/pull/5392), which changed the meaning of `MaxCPU` itself to an exclusive bound and also repaired empty-slice handling introduced by the same CPU-mask migration.
4. Reading [runc PR 5343](https://redirect.github.com/opencontainers/runc/pull/5343) explains why. The earlier code had a local `maxCPUs = 64 * 1024` used as a capacity for the reset mask, while the parser gained a separate limit described as the highest accepted CPU/NUMA node ID. A review suggestion later combined the two into `configs.MaxCPU`.

The integer stayed the same. The unit of meaning changed.

## What was correct about the original report

The report identified a genuine contract mismatch in the current source:

```go
// Current documented interpretation at the time:
// MaxCPU = highest accepted CPU ID

unix.NewCPUSet(configs.MaxCPU) // max is exclusive
```

Given those premises, this follows cleanly:

```go
unix.NewCPUSet(configs.MaxCPU + 1)
```

So the report and local diagnosis were useful. A superseded patch does not erase a valid finding.

The better question after finding the mismatch is: **which side of the mismatch carries the accidental contract?**

## The historical clue

Before the constants were unified, the reset path effectively used:

```go
const maxCPUs = 64 * 1024
```

Here `maxCPUs` means a count or capacity. A capacity of 65536 represents IDs `0..65535`.

The parser-side limit was described as the highest accepted ID. Under that interpretation, a value of 65536 means IDs `0..65536` are valid, requiring capacity for 65537 IDs.

Those values look identical in code:

```text
mask capacity      = 65536
highest valid ID   = 65536
```

They carry different contracts. Combining them created an off-by-one waiting to surface.

PR 5392 restores one convention:

```text
MaxCPU = exclusive limit / representable count
valid IDs = [0, MaxCPU)
```

That lets both parser validation and `unix.NewCPUSet(MaxCPU)` use the same boundary without call-site arithmetic.

## A second clue from the type migration

The same earlier runc work changed CPU masks from pointer-like fixed sets to `unix.CPUSetDynamic`, which is a slice.

That changes the zero-value surface:

```go
nil
[] // non-nil, length zero
```

Old checks such as:

```go
aff.Initial == nil
```

were complete when the field was a pointer. After the migration, an empty non-nil slice can represent the same effective absence, including after JSON decoding. PR 5392 therefore changes relevant checks to `len(...) == 0`.

This is the broader review move: when a type changes, audit every assumption attached to the old type, especially zero values, serialization, equality, allocation, pointer/size behavior, and syscall boundaries.

## The regression-test lesson

The first candidate also tried to assert that the bit immediately above the accepted maximum was absent from a `CPUSetDynamic` created with `NewCPUSet(MaxCPU + 1)` and then filled.

That is the wrong layer to test. `NewCPUSet` allocates whole machine-word chunks, so its physical bit capacity can extend beyond the requested exclusive bound. `Fill()` fills those allocated bits too.

A more durable boundary test asks about the public contract:

```text
MaxCPU - 1 -> accepted
MaxCPU     -> rejected
```

Tests should pin the semantic invariant while allowing an allocator to round its backing storage.

## Takeaways

### 1. Current comments are evidence, and history can reveal that the comment describes an accidental contract

Treat the current source as the starting point. When two adjacent APIs disagree about inclusive/exclusive bounds, units, ownership, lifetime, or zero values, inspect the commit that connected them.

### 2. When constants are unified, compare meanings before values

Ask what each value measures:

- count or identifier;
- bytes or elements;
- inclusive maximum or exclusive limit;
- timeout duration or deadline;
- capacity or last valid index.

Numerical equality can hide a semantic mismatch.

### 3. Repair the invariant at the owner that can state it once

A local `+1` can repair one consumer. An exclusive `MaxCPU` lets the parser and allocator share one convention. Prefer the boundary that removes repeated translation when compatibility permits it.

### 4. Type migrations deserve a semantic audit

For pointer-to-slice, fixed-to-dynamic, scalar-to-optional, or similar migrations, inspect:

- nil and empty values;
- serialization and deserialization;
- equality and counting;
- allocation rounding;
- syscall pointer and size pairs;
- callers that used the old zero-value test.

### 5. Test the contract, not a convenient implementation detail

A parser limit should be tested through accepted and rejected inputs. An allocator may legally reserve extra backing bits, bytes, pages, or buckets.

### 6. A good bug report and a superseded fix can coexist

The report can correctly expose the broken equation while a maintainer finds a better place to repair it. Preserve the report, understand why the replacement is better, and carry the lesson into the next review.

### 7. After a plausible local fix appears, ask one historical question

A compact habit:

> What earlier decision made these two pieces share a value, type, or helper, and did they originally mean the same thing?

That question would have exposed the runc distinction quickly.

## Suggested review receipt for similar cases

```text
current mismatch:
local fix that follows current code:
introducing/refactor commit:
pre-refactor meanings:
units and bound conventions:
type-semantic changes:
preferred invariant owner:
public boundary test:
compatibility consequence:
why the local candidate was superseded:
```

## Limits

This is a source-reading and review lesson based on the runc issue and pull-request history available on 2026-08-11. It records why the maintainer's repair has a cleaner invariant and why the first regression test targeted the wrong layer. It is not an executed runc reproduction or a claim about every supported architecture and kernel configuration.

## Related work

- [`START_HERE.md`](../../START_HERE.md) — requires a bounded history-and-intent pass before promoting a defect claim.
- [`FIELD_GUIDE.md`](../../FIELD_GUIDE.md) — review guidance on full contracts, compatibility surfaces, and durable tests.
- [`BUG_LENSES.md`](../../BUG_LENSES.md) — invariant-first defect lenses, including cross-layer contract drift.
- [`cross-context-review-prevents-myopia.md`](cross-context-review-prevents-myopia.md) — includes history and intent as an adjacent context that can overturn a local explanation.
- [runc issue 5388](https://redirect.github.com/opencontainers/runc/issues/5388)
- [runc PR 5389](https://redirect.github.com/opencontainers/runc/pull/5389)
- [runc PR 5392](https://redirect.github.com/opencontainers/runc/pull/5392)
- [runc PR 5343](https://redirect.github.com/opencontainers/runc/pull/5343)
