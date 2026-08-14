# Execution-lease audit of destructive guest memory operations

Date: 2026-08-14
Status: source audit after successful MAP_FIXED lease guard
Scope: FEX memory/lifetime design, exact upstream head `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`

## Purpose

The callback execution-lease experiments established a general invariant:

> After an executable owner generation has an active lease, no physical memory operation may destroy, replace, or otherwise make required mappings unusable until that lease releases.

The first implementation only covered the two operations exercised by the synthetic DSO fixture:

```text
munmap       -> retirement may defer physical unmap
mmap FIXED   -> active owner may temporarily reject replacement
```

This audit identifies other memory paths that must eventually participate in the same owner-generation arbitration rather than receiving callback-specific fixes.

## 1. `GuestMunmap` — covered by the current research mechanism

The research lifetime stack calls `RetireGuestRange` before physical host unmap. If the matching owner generation has `active != 0`, guest unload bookkeeping receives success while physical host unmap is deferred to the last execution-lease release.

This behavior is now proven for both concurrent unload and callback self-unload.

Required product improvement: operate on a complete load-generation/dependency set rather than one VMA OwnerID and make the retired-but-pinned state explicit to the memory manager.

## 2. `GuestMmap(... MAP_FIXED ...)` — first guard proven, range semantics incomplete

The unguarded discriminator demonstrated:

```text
active owner 0x15
MAP_FIXED over callback page
old OwnerID 0x15 -> new OwnerID 0x1a
callback resumes -> 139
```

The first guard checks for an active lease before the existing MAP_FIXED prepare/commit transaction. The same replacement receives `EBUSY` while the lease is active and succeeds after final release/reclaim.

That behavior is proven by `CALLBACK_LEASE_MAP_FIXED_REJECT_RETRY_RESULT_2026-08-14.md`.

### Remaining MAP_FIXED issue

The diagnostic guard resolves OwnerID from the replacement range's start address. A multi-page replacement may intersect several owner generations.

Product query must be range-based:

```text
GetDestructiveRangeOwners(base, length)
  -> every owner/load generation intersecting the requested physical change
```

The operation is permitted only if every required owner is reclaimable.

`MAP_FIXED_NOREPLACE` should be treated according to its actual kernel semantics rather than automatically classified as destructive: when an occupied range is present, it fails rather than replacing it.

## 3. `GuestMremap` — high-priority uncovered destructive path

At exact current FEX main, `GuestMremap` acquires the VMA-tracking lock and calls host `::mremap(...)` (or the 32-bit allocator equivalent) **before** `TrackMremap` and code invalidation.

That means the physical mapping transition occurs before any thunk-lifetime or active-owner consultation.

Relevant destructive forms include:

```text
old mapping moved away from its address
old mapping shrunk
MREMAP_FIXED replacement at a requested destination
```

`MREMAP_DONTUNMAP` changes the ownership question because the old mapping may remain, but destination replacement still needs arbitration when combined with a fixed destination.

### Required model

`mremap` needs a prepare/commit/rollback lifetime transaction analogous to the MAP_FIXED research stack:

```text
prepare source-owner transition
prepare destination-owner destructive replacement, if any
check active execution leases on every physical mapping that would be removed/replaced
perform host mremap
commit new ownership on success
rollback ownership plan on failure
```

A callback-specific check at the syscall surface is insufficient because ordinary H->T retained execution and future load-generation uses need the same rule.

## 4. `GuestShmdt` — uncovered physical detach

Current `GuestShmdt` calls host `::shmdt` (or the 32-bit allocator path) before `TrackShmdt` and code invalidation.

For ordinary application data this is unrelated to thunk lifetime, but executable guest code can in principle reside in System V shared memory. If a retained guest callback target or another escaped guest executable target belongs to that region, physical detach can invalidate an active execution lease just like `munmap`.

General owner-generation lifetime therefore needs to wrap this path as well.

Priority is lower than `mremap` for the current DSO reproducer, but the architecture should not encode “ELF only” assumptions if OwnerID is meant to describe executable mapping generations generally.

## 5. `GuestShmat` with replacement semantics — audit required

Linux `shmat` supports `SHM_REMAP`, which can permit an attachment at an address range already containing mappings.

Current FEX `GuestShmat` performs host attach before tracking the resulting VMA.

The exact FEX path and 32-bit allocator behavior should be tested for `SHM_REMAP` replacement before declaring the destructive-operation set complete.

If host mappings can be replaced, the same range-owner lease check must run before physical attachment.

## 6. `GuestMprotect` — protection transition is a separate lifetime boundary

Current `GuestMprotect` calls host `::mprotect` before updating VMA protection tracking and before invalidation/cache handling.

Protection changes do not necessarily destroy mapping identity, and the existing OwnerID research correctly preserves OwnerID across ordinary RX/RW/RX transitions.

However an active executable lease may still depend on the mapping remaining accessible. Examples requiring explicit policy/testing include:

```text
RX -> PROT_NONE while callback is already executing
RX -> non-readable/non-executable combinations
permission changes followed by concurrent code mutation
```

This should not be conflated with mapping-generation replacement. The likely product rule is:

```text
OwnerID identity may remain stable across mprotect,
but destructive permission transitions still need execution-safety arbitration.
```

A dedicated discriminator is preferable before choosing whether to reject/defer a protection change or rely on existing FEX translated-code/SMC semantics.

## 7. Content-destructive operations beyond mapping removal

Operations such as `madvise(MADV_DONTNEED)` can discard anonymous contents without changing the mapping's virtual identity. For file-backed mappings the contents may be faulted back; for anonymous executable/JIT memory this can change the bytes an active generation expects.

This is outside the immediate DSO-unload bug, but it shows why a final execution-lifetime abstraction cannot be defined solely as “prevent munmap.”

Future audit should classify memory operations by effect:

```text
identity replacement
physical removal
permission revocation
content discard/mutation
non-destructive metadata/protection transition
```

The lease contract only needs to interpose on operations that can make an active generation's required state unusable.

## Recommended implementation boundary

Avoid teaching every syscall about callback descriptors.

Expose a memory/lifetime interface around owner generations, conceptually:

```cpp
DestructiveTransitionToken PrepareDestructiveTransition(
    Thread,
    Range,
    TransitionKind);

CommitDestructiveTransition(Token, Result);
RollbackDestructiveTransition(Token);
```

The token can identify all intersecting load generations and report whether transition is currently permitted, must be deferred, or can proceed immediately.

Thunk retirement contributes active execution leases to those owner generations; the memory layer performs the physical arbitration.

That keeps the ownership stack reusable for:

- callback targets;
- retained H->T guest executable targets;
- future generated/reclaimable guest adapters;
- executable mappings unrelated to thunks if FEX later needs the same safety property.

## Priority order from this audit

1. `mremap`, especially `MREMAP_FIXED` and moving old executable mappings;
2. generalize MAP_FIXED guard from start OwnerID to every intersecting owner;
3. test `mprotect(PROT_NONE)` during an active callback lease;
4. inspect/test `shmat(SHM_REMAP)` and `shmdt` on executable shared mappings;
5. audit content-discard operations such as `MADV_DONTNEED` for anonymous executable owners;
6. promote VMA OwnerID to load-generation/dependency ownership before source-ready cleanup.

## Current architecture remains unchanged

The syscall audit reinforces the same three-way separation:

```text
resident generated companion
  -> generated escaping adapter lifetime

generation tombstone
  -> deny future entry after retirement

execution lease + memory arbitration
  -> preserve physical requirements of already-entered unloadable guest execution
```

The memory arbitration is the part that turns the lease from a callback-specific experiment into a coherent FEX executable-lifetime mechanism.
