# Cloud Hypervisor QCOW L2 ownership and publication — review record

## TL;DR

Cloud Hypervisor PR 8721 fixes a QCOW metadata ordering defect where an L2 table could become reachable from L1 before the L2 had `refcount=1` ownership. The final reviewed design goes farther than the first submitted repair: it removes the remaining deferred old-L2 release path, making the relocation ownership handoff local to `update_cluster_addr()`.

Current upstream head at this record: `284a2d42b98c514f57d3e89240861196d94fc6cb`.

The final relocation state machine is:

```text
allocate replacement L2
-> replacement refcount = 1
-> prepare complete replacement L2 contents
-> switch L1 to replacement
-> drop old L2 refcount
-> old L2 waits in unref_clusters until metadata flush
```

The useful property is not transactional perfection. It is failure direction: after publication, an old-L2 release failure can leave dead metadata owned longer than necessary, while the code avoids making still-live metadata allocator-visible as free space.

Public PR: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8721

Fieldwork issue: https://redirect.github.com/teamleaderleo/linux-fieldwork/issues/609

## Explain like I'm five

Think of L1 as a directory telling the program where an L2 table lives. A refcount of 1 says that the cluster belongs to something and must not be handed to another writer.

The unsafe ordering was effectively:

```text
point the directory at a new box
-> remember to mark the box owned later
```

If the operation failed before the later bookkeeping happened, the directory could still point at the box while the allocator thought the box was free.

The repair is:

```text
prepare the new box
-> mark it owned
-> point the directory at it
-> retire the old box
```

For a failure, wasting an unreachable box is much less dangerous than handing a box that is still in use to somebody else.

## Why care

The demonstrated fresh-L2 failure could survive a clean shutdown and reopen. A still-referenced L2 with refcount 0 could enter the ordinary free-cluster pool and later be reused for guest data or metadata, overwriting a table that L1 still referenced.

The review also exposed a second class of state split: after L1 switched to a replacement L2, release of the predecessor was carried back to `map_write()` in a local deferred vector. Errors before the caller's cleanup loop could discard that obligation.

Removing that local pseudo-transaction reduces the number of partially completed ownership states that need to be reasoned about.

## Source and evidence boundaries

### Demonstrated baseline

Original reproduction base:

`1af93ac7035cda77cd87b0c18b1134ebb0928052`

Source fence:

```text
block/src/formats/qcow/metadata.rs
```

The fresh-L2 discriminator reached the historical bad state and then reopened the image:

```text
L1 -> live L2
refcount(live L2) = 0
```

The ordinary allocator could then return that same still-referenced L2 cluster.

### Current submitted head

PR head:

`284a2d42b98c514f57d3e89240861196d94fc6cb`

Current PR base at the latest identity check:

`f2d5f82293088cb6b105dbcdbda075428f0f97bf`

Current upstream diff:

```text
1 commit
1 changed file
201 additions
38 deletions
```

The final commit is signed by the human contributor and the PR branch is `linux-fieldwork/qcow-l2-refcount-ownership-r609`.

## How the repair evolved

### Historical behavior

The write path used a local deferred refcount collection. The important failure shape was:

```text
publish metadata
-> carry refcount obligation forward
-> do more fallible work
-> apply obligation later
```

The vector was bookkeeping, not an atomic transaction. `?` unwinding could discard it after an earlier metadata mutation remained.

### First repair

The first repair moved new-L2 ownership ahead of L1 publication at both fresh allocation and relocation:

```text
allocate new L2
-> refcount = 1
-> publish through L1
```

That fixed the demonstrated ownership/publication invariant while deliberately preserving the inherited old-L2 release mechanism.

At this stage the relocation lifecycle still had two timescales:

```text
new L2 ownership: immediate
old L2 release: deferred to map_write() tail
```

This was a defensible narrow repair boundary: fix the proven defect without redesigning adjacent lifecycle machinery before there was evidence that the machinery itself should change.

### Review-added success control

Weltling's review asked for the successful half of relocation cleanup. The resulting `successful_l2_relocation_releases_old_table` regression preserves:

```text
Old L2: refcount 1 -> refcount 0 -> reusable after flush
New L2: refcount 1 -> stays allocated
```

That was useful because it tested the intended lifecycle rather than only the failure path.

### Bradford's premise challenge

Rob Bradford then asked what benefit the remaining release deferral provided. Once L1 has switched to the replacement, releasing the old table inline is identical on the success path, removes a caller out-parameter and cleanup loop, and avoids another error interval.

That review changed the repair boundary without invalidating the original finding:

```text
notice broadly
-> prove narrowly
-> repair narrowly
-> receive new evidence
-> widen only as far as the new evidence supports
```

The final implementation deletes the deferred old-L2 vector entirely.

## Final relocation state machine

The current `update_cluster_addr()` transition is conceptually:

```text
PREPARE
allocate replacement L2
-> give replacement refcount=1
-> prepare replacement L2 contents

PUBLISH
L1 -> replacement

RETIRE
old L2 refcount -> 0
-> old L2 enters unref_clusters
```

`unref_clusters` and `avail_clusters` remain intentionally distinct. A newly unreferenced cluster is not allocator-visible for reuse until metadata flush has persisted the relevant state.

That preserves the older durable-reuse rule while deleting the unrelated local deferred-refcount mechanism.

## Failure direction

The current ordering makes the important failure states easier to classify.

### Replacement allocation fails

```text
old L1/L2 remains untouched
```

### Replacement ownership fails

```text
replacement is not published through L1
old L1/L2 remains authoritative
```

### Old-L2 refcount drop fails after L1 switches

The intended local state is:

```text
L1 -> replacement L2
replacement L2 is owned
replacement L2 cache contains the intended entry
old L2 remains refcount 1
old L2 is not advertised for reuse
```

The residual can be leaked space or a propagated metadata error. That is preferable to the dangerous direction:

```text
live/reachable object -> allocator thinks reusable
```

The broader shutdown/DIRTY policy is separate; this PR does not claim full transactional metadata recovery.

## Compressed-cluster ordering

Making `update_cluster_addr()` the local metadata handoff introduced a new reason to reconsider the compressed-cluster path.

The final path writes and verifies the replacement data before entering the metadata handoff:

```text
decompress old contents
-> allocate replacement data cluster
-> populate replacement data cluster
-> update_cluster_addr()
```

The handoff then performs:

```text
own replacement L2
-> prepare its mapping
-> switch L1
-> retire old L2
```

This means a failure during the metadata handoff will not leave the replacement mapping pointing at an unpopulated data cluster. The data dependency belongs in PREPARE, before the publication/retirement transition begins.

This ordering change was not explicitly requested by the reviewer. It followed from examining the new failure position after old-L2 release moved into `update_cluster_addr()`.

## Test matrix after the cleanup

The useful current neighborhood is:

| Role | Test | Contract |
|---|---|---|
| Existing failed relocation | `failed_l2_relocate_keeps_live_table_off_free_lists` | Failed replacement allocation keeps the live old L2 out of free lists |
| Existing compressed failed relocation | `failed_l2_relocate_after_compressed_write_keeps_live_table` | The compressed entry path preserves the same live-old-L2 rule |
| Fresh-L2 regression | `fresh_l2_enospc_reopen_does_not_reuse_live_table` | Clean reopen cannot make an L1-referenced L2 allocator-reusable |
| Successful relocation control | `successful_l2_relocation_releases_old_table` | Old L2 reaches refcount 0 and becomes reusable only after flush; replacement stays owned |
| Alternate caller | `zero_marker_fresh_l2_keeps_refcount_owner` | The fresh-L2 ownership rule also holds through the zero-marker path |

The implementation-specific test `relocated_l2_dropped_deferred_updates_keeps_refcount_owner` was removed because the deferred-update mechanism no longer exists. Keeping it would preserve an implementation structure that review deliberately deleted.

### One useful non-blocking regression idea

An independent review identified one remaining interesting edge for deterministic fault injection:

```text
replacement allocated + owned
-> replacement contents prepared
-> L1 switches
-> old-L2 refcount drop fails
```

A clean regression would verify that the replacement remains owned and complete and that no L1-referenced L2 appears in either free list.

This is worth adding if a local, readable fixture exists. It is not worth distorting this PR around lower-level recursive-refcount failure machinery merely to manufacture the failure point.

## Validation

Exact source used for the final internal cleanup validation matched the source blob carried into the submitted head.

Internal validation workflow:

```text
run: 31821189390
job: 94834531853
```

Results:

```text
rustfmt                                                   PASS
git diff --check                                          PASS
cargo test --locked -p block                              298 passed, 0 failed
cargo test --locked -p block --features io_uring          326 passed, 0 failed
cargo clippy --locked -p block --lib --features io_uring -- -D warnings  PASS
```

Current canonical upstream CI run for `284a2d42...`:

`31823225439`

At the latest check the workflow was still marked `in_progress`, while every returned executable job had completed successfully. Path-inapplicable jobs such as `taplo`, `audit`, `openapi`, and `hadolint` were skipped. Do not describe the complete workflow as finished until its overall conclusion is final.

## Review state

Weltling approved the earlier semantic version after confirming that new L2 tables get refcount 1 before L1 points at them. Review nits also improved the allocator expectation wording and added the successful-relocation lifecycle control.

Bradford subsequently challenged the remaining old-L2 release deferral. The human contributor agreed to fold that cleanup into the PR, pushed `284a2d42...`, and replied with the resulting local state-machine change and compressed-data ordering consequence.

Because the final head contains a semantic cleanup after Weltling's approval, the useful remaining human gate is fresh review of the current head by Bradford or another maintainer.

## Historical provenance

This code has a direct crosvm ancestry.

Cloud Hypervisor's original QCOW import says it was extracted from crosvm:

https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/commit/80ac3a84bb6d5672a97a3baa7d12710bc4cddb7c

A key 2018 crosvm refactor introduced metadata caching to remove an "absurd number of system calls" from repeated QCOW metadata access:

https://redirect.github.com/google/crosvm/commit/32e17bc0b7ddd0cfa2ace015f38bce8375e43af2

That refactor introduced the in-memory L1/L2/refcount cache architecture and the `set_refcounts` batching pattern. The performance motivation was real: avoid repeated disk/system-call traffic and write cached metadata on flush or eviction.

The important historical nuance is that publication-before-ownership did not originate with the cache vector. The pre-cache implementation already wrote a new mapping, synced it, then set the new cluster's refcount and synced again. The cache refactor inherited that ordering and represented the later refcount work as deferred in-memory bookkeeping.

At the same time, the cached implementation explicitly preserved two other safety ideas:

1. modified L2 tables move to new clusters so L1 can be committed after the replacement table and does not point at an invalid table;
2. freshly unreferenced clusters remain in `unref_clusters` and only become `avail_clusters` after the removal of references has been synced.

The historical seam was therefore not "performance versus correctness" in one simple decision. It was that content/pointer COW ordering and durable-reuse ordering were treated carefully, while refcount ownership remained outside the publication invariant.

PR 8721 reconciles those models:

```text
new object complete enough to use
-> new object owned
-> pointer published
-> predecessor unowned
-> predecessor withheld from reuse until safe
```

That is the provenance-worthy lesson.

## Relation to earlier Cloud Hypervisor work

Earlier PR 8637 fixed a different relocation ordering failure: the old live L2 must not enter the release pipeline before replacement allocation succeeds.

https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8637

That repair established:

```text
allocate replacement first
-> only then release predecessor
```

It did not establish that predecessor release needed to remain deferred to the tail of `map_write()`.

PR 8721 first fixed new ownership publication and review then removed that leftover deferral.

## Adjacent successors that remain separate

This PR owns the L2 publication/ownership boundary. It does not absorb every adjacent QCOW metadata failure policy.

### Fieldwork 611 — shutdown DIRTY handling

`QcowMetadata::shutdown()` can ignore a metadata sync failure and continue toward clearing DIRTY. That can falsely certify state as clean after a real metadata write failure.

The current L2 handoff should not rely on DIRTY recovery as its local safety mechanism. Issue 611 remains a separate durability-policy owner.

### Fieldwork 634 — recursive refcount-block ownership

`set_cluster_refcount_track_freed()` enters lower-level refcount metadata machinery that has its own recursive ownership/publication questions when refcount blocks relocate or need new storage.

PR 8721 fixes the L2-level ordering; it does not make the entire recursive refcount operation transactional.

### Fieldwork 645 — failed cache eviction

A failing dirty-cache eviction can lose retryable metadata at a different owner. That remains a separate cache failure-policy question.

These successors sharpen this PR's boundary rather than invalidate it.

## Reusable lessons

### 1. Ownership is part of publication

If a pointer makes an object live, ownership metadata that prevents allocator reuse is part of what makes that publication truthful.

```text
prepare -> own -> publish -> retire
```

is easier to reason about than:

```text
publish -> carry obligation -> do more work -> settle obligation later
```

### 2. Reduce state before adding machinery to manage it

The first repair narrowed a generic deferred vector to old-L2 releases. Review then showed that even that residual state was unnecessary.

Deleting a state can remove an entire family of failure paths more effectively than adding rollback or tests for every way the state can be lost.

### 3. Scope discipline does not require preserving every premise

The narrow repair was correct under the evidence available at the time. Review supplied new evidence that the inherited release staging had no useful property.

A good progression is:

```text
prove the local invariant
-> repair it narrowly
-> challenge inherited premises
-> widen only when the new evidence supports it
```

### 4. Before pinning a staged lifecycle in tests, ask whether the staging is required

The removed deferred-update regression was useful while that mechanism existed. Once review removed the mechanism, the durable test is the behavioral success/failure contract, not the old vector shape.

### 5. When a handoff boundary changes, move its prerequisites to PREPARE

Concentrating metadata transition work inside `update_cluster_addr()` made the compressed-data dependency obvious. Populate replacement data before entering the handoff that can publish metadata pointing to it.

### 6. Prefer the safer failure direction

When perfect rollback is unavailable, prefer:

```text
dead object remains owned
```

over:

```text
live object becomes allocator-reusable
```

The former can waste space; the latter can corrupt live metadata or data.

## External-contact state

Upstream PR 8721 was opened, updated, and replied to by the human contributor. This record does not grant any additional upstream interaction authority.

## Related records

- [`../../notes/processes/lifecycle-tests-cover-failure-and-success.md`](../../notes/processes/lifecycle-tests-cover-failure-and-success.md)
- [`../../notes/processes/history-can-change-the-repair-boundary.md`](../../notes/processes/history-can-change-the-repair-boundary.md)
- [`../../FIELD_GUIDE.md`](../../FIELD_GUIDE.md)
- [`../../BUG_LENSES.md`](../../BUG_LENSES.md)
- Cloud Hypervisor PR 8721: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8721
- Cloud Hypervisor PR 8637: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8637
- crosvm metadata-cache refactor: https://redirect.github.com/google/crosvm/commit/32e17bc0b7ddd0cfa2ace015f38bce8375e43af2
- Cloud Hypervisor QCOW import: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/commit/80ac3a84bb6d5672a97a3baa7d12710bc4cddb7c
