# Regression fixtures should own host-dependent state

## Context

A small range-validation fix can be correct while its regression test still carries unnecessary assumptions or shared test machinery. Review of a VFIO sparse-mapping regression exposed three separate concerns: host page size, temporary-file ownership, and readability of the tested interval geometry.

The production repair did not need to change. The useful follow-up work was in the fixture.

## Durable rules

### Derive host-dependent quantities

If a test feeds values into `mmap`, page alignment, KVM, or another host-sensitive interface, derive the relevant page size or granularity from the same project helper used by production code.

A 4 KiB constant may pass on common x86 hosts while failing on hosts with larger pages even when the behavior under test has nothing to do with 4 KiB pages.

### Let each fixture own its temporary resources

A process-global atomic counter can be a valid way to generate unique names. It is still shared coordination for a resource that may belong entirely to one test invocation.

When an existing helper such as `TempFile` can create a unique file and clean it up with object lifetime, prefer that local ownership. This removes shared mutable state, manual naming, and manual cleanup at once.

The rule is not "globals in tests are bad." The rule is: do not introduce shared coordination when the fixture can own the resource directly.

### Document interval geometry where the assertions are read

For range bugs, a compact comment can save a reviewer from reconstructing the entire fixture mentally. State the logical range, the actually backed subranges, and the request that crosses a boundary.

Example form:

```text
logical range:        [0, 4P)
backed ranges:        [P, 2P), [3P, 4P)
failing request:      [1.5P, 2.5P)
```

The comment belongs close to the assertions because that is where the geometry explains the expected result.

### Candidate rejection is not terminal failure

In a lookup loop, skipping one candidate can still lead to overall success. Logging at the per-candidate `continue` can therefore report an operation that eventually succeeds.

Treat candidate rejection and terminal lookup failure as different events. Add logging only where its meaning matches the actual outcome.

### Preserve an accepted production fix during cleanup review

When review says the production change is generally correct and the remaining remarks concern test hygiene or readability, keep the semantic repair stable unless a new correctness issue is identified.

Do not turn a cleanup round into a redesign. Improve the fixture, rerun the relevant validation, and keep the product diff focused.
