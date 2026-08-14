# Ownership is part of publication

## In simple words

When a pointer makes an object live, the ownership metadata that keeps the allocator from reusing that object is part of what makes the publication valid.

A useful state machine is:

```text
prepare
-> own
-> publish
-> retire predecessor
-> make predecessor reusable only after cleanup is durable
```

This is easier to reason about than carrying ownership or cleanup obligations across unrelated fallible work.

Cloud Hypervisor PR 8721 made this concrete for QCOW L2 metadata:

https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8721

## The state-machine lens

Suppose L1 points to an L2 metadata table. A new L2 is not fully safe to publish merely because storage has been allocated for it. The allocator also needs to know that the cluster is owned.

The dangerous split is:

```text
publish pointer
-> remember ownership update
-> do more fallible work
-> settle ownership later
```

An error can discard the later obligation after reachability has already changed.

The stronger form is:

```text
PREPARE
replacement contents are ready

OWN
replacement cannot be reused by the allocator

PUBLISH
pointer switches to replacement

RETIRE
predecessor loses ownership

REUSE
predecessor becomes allocator-visible only after required cleanup is durable
```

The point is not that every storage update becomes a perfect transaction. The point is that each published state is locally coherent.

## Prefer safer residual states

When complete rollback is unavailable, compare the direction of failure.

Prefer:

```text
dead/unreachable object -> still marked owned
```

over:

```text
live/reachable object -> allocator thinks reusable
```

The first can waste storage. The second can let another writer overwrite live data or metadata.

This gives a useful review question:

> If the operation stops at this exact line, is the leftover state merely conservative, or can a live object be reused as though it were dead?

## Reduce states before adding recovery machinery

A deferred vector, pending callback, cleanup token, or caller-owned out-parameter can look like a transaction without providing transactional guarantees.

Before adding rollback, retries, or more tests around such a structure, ask:

```text
Does this deferred state need to exist at all?
```

If the owner of the transition can finish the handoff locally, deleting the staged state may remove an entire family of error windows.

In PR 8721 the repair evolved from:

```text
new ownership: immediate
old release: deferred to caller
```

to:

```text
allocate replacement
-> own replacement
-> prepare replacement metadata
-> publish replacement
-> release predecessor locally
```

The deferred out-parameter and caller cleanup loop disappeared with the state they represented.

## When the handoff boundary moves, move prerequisites into PREPARE

Concentrating a transition in one helper can introduce a new fallible point inside that helper. Re-check what must already be true before entering it.

For the QCOW compressed-cluster path, once `update_cluster_addr()` owned the complete metadata handoff, replacement data was written before entering that function:

```text
populate replacement data
-> enter metadata handoff
```

That keeps a handoff failure from publishing metadata that points at an unpopulated data cluster.

A general review prompt is:

> What data, ownership, validation, or initialization must be complete before this function is allowed to publish the replacement?

## History can explain why the split existed

The QCOW implementation has direct crosvm ancestry. Cloud Hypervisor's original import says it was extracted from crosvm:

https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/commit/80ac3a84bb6d5672a97a3baa7d12710bc4cddb7c

A 2018 crosvm refactor cached QCOW address and refcount metadata to remove an "absurd number of system calls":

https://redirect.github.com/google/crosvm/commit/32e17bc0b7ddd0cfa2ace015f38bce8375e43af2

That history matters, but the lesson is not simply "performance caused a correctness bug."

The pre-cache path already published a mapping before applying the new cluster's refcount. The cache refactor inherited that ordering and turned the later refcount work into deferred in-memory bookkeeping.

At the same time, the implementation separately preserved two careful COW rules:

```text
replacement L2 contents before durable L1 publication
unreferenced cluster cleanup before allocator reuse
```

The missing reconciliation was that allocator ownership itself also belongs in the publication invariant.

## Tests should preserve behavior, not accidental staging

While a staged state exists, a regression may reasonably exercise what happens when that state is lost.

If review removes the staged state, remove tests that exist only to construct it.

Keep behavioral controls such as:

```text
failure: live replacement stays owned
success: dead predecessor becomes reusable after successful cleanup
```

This avoids turning an implementation-specific test into a reason an unnecessary mechanism must survive forever.

See [`lifecycle-tests-cover-failure-and-success.md`](lifecycle-tests-cover-failure-and-success.md).

## Repair-boundary lesson

A narrow first fix can be correct without being the final repair boundary.

A productive sequence is:

```text
observe broadly
-> prove one invariant
-> repair it narrowly
-> challenge inherited premises
-> widen only when new evidence supports it
```

Review that removes unnecessary state is not evidence that the earlier diagnosis was wrong. It can be evidence that the original diagnosis made the remaining design assumption visible enough to question.

See [`history-can-change-the-repair-boundary.md`](history-can-change-the-repair-boundary.md).

## Compact review checklist

For ownership/publication changes, ask:

1. What exact operation makes the replacement reachable?
2. What must be true before that publication is truthful?
3. Which function owns the complete handoff?
4. What deferred obligations leave that function?
5. Can any of those obligations be eliminated instead of managed?
6. If retirement fails after publication, is the predecessor merely retained or can something live become reusable?
7. When does a retired object become allocator-visible again?
8. Did moving the handoff create new prerequisites that belong in PREPARE?
9. Do tests preserve behavioral state transitions rather than temporary containers?
10. Does history show that an inherited staging rule has a real compatibility or performance requirement?

## Related work

- [`../../investigations/cloud-hypervisor-qcow-r609-review/README.md`](../../investigations/cloud-hypervisor-qcow-r609-review/README.md)
- [`lifecycle-tests-cover-failure-and-success.md`](lifecycle-tests-cover-failure-and-success.md)
- [`history-can-change-the-repair-boundary.md`](history-can-change-the-repair-boundary.md)
- [Cloud Hypervisor PR 8721](https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8721)
- [Cloud Hypervisor PR 8637](https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8637)
- [crosvm metadata-cache refactor](https://redirect.github.com/google/crosvm/commit/32e17bc0b7ddd0cfa2ace015f38bce8375e43af2)
