# Mapping-owner token implementation sketch

Date: 2026-08-14

This note refines [`MAPPED_RESOURCE_OWNERSHIP.md`](./MAPPED_RESOURCE_OWNERSHIP.md) after the real same-address `MAP_FIXED` ABA in [`VMA_TRANSITION_LOG.md`](./VMA_TRANSITION_LOG.md).

## Required identity

A bridge claim should identify both the mapping generation and the exact guest target:

```text
ThunkClaim {
    host_entrypoint H;
    guest_target T;
    owner_id;
    ABI/signature identity where available;
}
```

`owner_id` prevents virtual-address ABA. Keeping T separately prevents owner identity from becoming too coarse for partial unmap/replacement of one segment inside a larger mapped resource.

## Where the owner ID lives

`MappedResource` alone is insufficient because private anonymous mappings have `VMAEntry::Resource == nullptr`.

A practical representation is an owner-generation ID visible from every `VMAEntry`:

```text
VMAEntry {
    ...
    MappingOwnerID Owner;
}
```

For file-backed mapped instances, every VMA belonging to one `MappedResource` should receive the same non-reusable owner ID. The `MappedResource` can store that canonical ID.

For anonymous/private mappings, `TrackVMARange()` assigns a fresh ID for a new mapping generation.

The ID must be monotonic/non-reused for the process lifetime; a raw `MappedResource*` cannot serve as the durable identity because allocator reuse would recreate an ABA problem.

## Split semantics

FEX VMA splitting already constructs new entries by copying the original VMA metadata in `DeleteVMARange()` / protection-change paths. Owner ID should be copied across splits of the same mapping generation.

Therefore:

```text
mprotect split                  -> preserve owner ID
partial trim/split              -> preserve owner ID on surviving pieces
same mapping restored executable -> same owner ID
```

This matches ordinary function-pointer expectations across permission changes.

## New mapping semantics

A successful new mapping operation receives a fresh owner ID unless it is explicitly preserving/moving an existing mapping generation.

```text
fresh mmap                       -> fresh owner ID
MAP_FIXED replacement            -> replacement gets fresh owner ID
new dlopen generation            -> fresh owner ID
```

For `MAP_FIXED`, the old overlapping entries are still queryable before host `mmap()` executes. That is the prepare point for dependent bridge retirement.

## Partial destructive transitions

Do not retire every claim associated with an owner merely because any VMA of that owner changes.

For each destructive range `[Base, Top)` drop a claim only when both are true:

```text
claim.owner_id identifies an affected old mapping generation
claim.T is inside the destroyed/replaced target range
```

This preserves bridges to unaffected executable segments of the same file mapping while eliminating stale targets inside the replaced portion.

Callback trampolines carry multiple dependencies and should retire when any required `{owner_id, address}` dependency is destroyed.

## `mremap`

`mremap` needs an explicit policy rather than accidental reuse.

If a mapping is moved and a bridge stores a raw guest target T in the old range, that claim must retire because its callable target address disappeared even if the underlying mapping resource survives at a new address.

If FEX later gains a bridge form that can intentionally track a moved target, that would require an explicit target-address update transaction; owner identity by itself does not make the old pointer valid.

Shrinks retire claims whose T falls in the removed tail. `MREMAP_DONTUNMAP` can preserve the old target and may legitimately leave existing claims active.

## Prepare / commit / rollback

The current causal experiment in [`MAP_FIXED_PRE_RETIRE_LOG.md`](./MAP_FIXED_PRE_RETIRE_LOG.md) retires before host `mmap()` and intentionally lacks rollback. Production needs a real transaction.

Minimum behavior:

```text
prepare:
  under VMA tracking, identify old owner/range dependencies
  snapshot affected bridge claims
  make affected H entries unavailable to new dispatch
  exact-evict compiled/cached H entries

execute:
  perform destructive host mapping syscall

commit on success:
  update VMA tracking with fresh/reused owner IDs as appropriate
  remove old claims permanently
  leave H revoked if no compatible owner remains

rollback on syscall failure:
  restore the old claims/active definitions from the snapshot
```

The in-flight dispatcher problem remains: a peer thread may already have selected old translated H before prepare. A production transaction needs quiescence or a generation check that closes that race; exact cache invalidation alone only governs future lookup.

## LinkAddress registration

At `LinkAddressToGuestFunction(H, T)`:

1. resolve the VMA containing T under VMA tracking;
2. capture its `owner_id` and T;
3. add a compatible claim for H;
4. if H is revoked and this is the first live claim, reactivate H through the existing exact global invalidation transaction;
5. maintain reverse lookup from owner ID to its bridge claims.

Same numeric T in a later mapping generation produces a different owner ID, so it cannot inherit the old claim. A fresh explicit LinkAddress registration is required.

## Regression layers

A production patch should carry both:

```text
VMA ownership unit tests
  - ID preserved across protection splits
  - ID preserved across surviving partial splits
  - fresh ID on MAP_FIXED replacement
  - explicit mremap rules

full FEX LinkAddress tests
  - H -> generation 1, pretranslate
  - MAP_FIXED same T, no re-register: H revoked / never generation 2
  - explicit re-register after replacement: H -> generation 2
  - failed MAP_FIXED: rollback restores generation-1 H
  - aliases and multi-owner claims
```

## External-contact state

No third-party/upstream interaction. This implementation sketch is retained only in `teamleaderleo/linux-fieldwork`.
