# Lexical scope can document test lifecycles

## In simple words

When a test depends on an object being closed, dropped, unlocked, flushed, or otherwise retired before the next phase begins, use the test's lexical scopes to make that lifecycle visible.

This came up during review of Cloud Hypervisor QCOW L2 refcount ordering in [PR 8721](https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8721).

The regression deliberately performs two lifetimes of the same image:

```text
first open
-> arrange allocator failure
-> retain one fact needed by the next phase
-> shutdown / Drop

second open
-> inspect persisted state
-> prove the live metadata is not allocator-reusable
```

An intermediate test expressed shutdown with a small scope around only the metadata owner. That was semantically sufficient, but the source did not make the whole first-open phase obvious. Review asked for the entire first version of the image to live in one logical scope, with the reopen beginning after that scope ends.

The resulting pattern is:

```rust
let retained_fact = {
    // Open and manipulate the first lifetime.

    let _owner = OwnerWhoseDropClosesTheResource::new(state);
    retained_fact
};

// The first lifetime has ended here.
// Reopen and inspect the next lifetime.
```

## Why this is useful

The improvement is mostly about reviewability and maintenance, with a real semantic aid underneath it:

- the source mirrors the experiment's phases;
- destruction timing is visible without requiring the reader to remember a hidden `Drop` side effect;
- first-lifetime variables cannot accidentally leak into the reopen phase;
- later edits have an obvious place for handles, guards, owners, or other state that must die before reopen;
- the few facts that intentionally cross the lifecycle boundary are explicit in the scope's return value.

This is especially useful for tests involving:

```text
close -> reopen
crash/recovery simulation
lock release -> reacquire
transaction/session lifetime
RAII cleanup with meaningful Drop behavior
file or metadata flush on destruction
```

It is much less important for ordinary unit tests where destruction timing is incidental.

## Review procedure

When reading or writing a lifecycle-sensitive test:

1. Identify the logical phases of the experiment before reading every fixture detail.
2. Ask which objects must cease to exist before the next phase is valid.
3. If `Drop`, destructor, close, unlock, or cleanup has a meaningful side effect, make its lifetime boundary visible in the source.
4. Put the complete logical phase inside that scope when practical, not only the final object whose destructor happens to trigger the transition.
5. Carry only the minimum facts needed by the next phase across the boundary.
6. Read the finished test as a state transition: a future reviewer should be able to see where one lifetime ends and another begins without reconstructing the author's current mental context.

## Durable rule

> When lifecycle timing is part of what a test proves, let lexical scope describe the lifecycle.

Tests are executable documentation. The author remembers the setup while writing it; the useful standard is whether a future reader can recover the same state machine from the test itself.

## Related work

- [Cloud Hypervisor PR 8721](https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8721)
- [`lifecycle-tests-cover-failure-and-success.md`](lifecycle-tests-cover-failure-and-success.md)
- [`../../FIELD_GUIDE.md`](../../FIELD_GUIDE.md)
