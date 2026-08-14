# VMA / `MappedResource` ownership design note

Date: 2026-08-14

## Why this exists

The runtime experiments have established that a stable synthetic/native thunk address `H` can outlive several guest load generations, while the guest executable target `T` belongs to one particular mapping generation and must be retired when that generation is destroyed.

Raw address ranges are sufficient for a causal probe, but they are a weak production identity because:

- guest virtual addresses are reusable;
- the same file can be loaded more than once at different bases;
- a file mapping is composed from several VMAs;
- partial unmap/protection changes can split VMAs;
- one stable native PFN can have multiple compatible guest owners;
- host-to-guest bridges can depend on two guest executable addresses from different DSOs.

FEX's existing VMA tracker already has an object that is close to the needed load-generation owner.

## Existing FEX semantics

Source snapshot: `71afe476751deac24adabd1adb575fd2337b6e0a`.

Relevant source:

- [`SyscallsVMATracking.h`](https://redirect.github.com/teamleaderleo/FEX/blob/71afe476751deac24adabd1adb575fd2337b6e0a/Source/Tools/LinuxEmulation/LinuxSyscalls/SyscallsVMATracking.h)
- [`SyscallsVMATracking.cpp`](https://redirect.github.com/teamleaderleo/FEX/blob/71afe476751deac24adabd1adb575fd2337b6e0a/Source/Tools/LinuxEmulation/LinuxSyscalls/SyscallsVMATracking.cpp)
- [`SyscallsSMCTracking.cpp`](https://redirect.github.com/teamleaderleo/FEX/blob/71afe476751deac24adabd1adb575fd2337b6e0a/Source/Tools/LinuxEmulation/LinuxSyscalls/SyscallsSMCTracking.cpp)

`MappedResource` is documented as normally representing one ELF/PE file mapping. If the same file is mapped at different base addresses, FEX creates separate `MappedResource` objects even though their `MRID` is the same.

Each VMA belonging to that mapped instance points back to the same resource through `VMAEntry::Resource`, and the resource owns an intrusive list beginning at `FirstVMA`.

`TrackVMARange()` first removes/replaces overlapping VMAs and then attaches the new range to the resource. `DeleteVMARange()` removes/splits VMAs and erases the resource once its last VMA is gone, except for the explicit preserved-resource case used while reshaping one mapping. Resources whose mapped code cache data must survive code invalidation are moved temporarily to `PendingResourceDeletions` and destroyed after invalidation.

This gives FEX an existing notion of:

```text
same backing file + same mapped instance/base + currently live VMA set
```

which is substantially closer to a guest load generation than either a pathname, `MRID`, or guest virtual address.

## Proposed owner token

Do not expose a raw `MappedResource*` as the long-term identity. Pointer reuse after deletion would create another ABA problem.

Add a monotonically increasing generation/token field associated with each mapping owner, for example:

```text
struct MappingOwnerToken {
    uint64_t generation;
};
```

or a wider typed ID if desired.

Assign a fresh token when a `MappedResource` is created. For anonymous mappings that have no `MappedResource`, assign an equivalent VMA-generation token.

A bridge dependency then records the token that owns its guest address at registration time.

## Mapping generation is distinct from protection state

A key compatibility correction is that **losing `PROT_EXEC` is not automatically the same as losing the mapping generation**.

Programs and runtimes legitimately do this:

```text
RX mapping
  -> mprotect RW
  -> patch/rewrite code
  -> mprotect RX
```

Ordinary function pointers to the same virtual address remain meaningful across that protection flip. If the same mapping generation still owns address `T`, a thunk bridge whose semantic target is `T` should not be permanently destroyed merely because the page is temporarily non-executable.

So the production model should distinguish:

```text
owner generation lifetime    // mapping identity
current executable state     // whether a call may execute right now
```

While the mapping is non-executable, a call through H should fail according to ordinary guest execute-permission semantics. When the *same* mapping generation becomes executable again, H may legitimately reach the code currently at T without requiring a new LinkAddress claim.

This also avoids breaking loaders/JITs that intentionally change page protections while preserving pointer identity.

By contrast, these operations can destroy or replace the mapping generation itself:

- `munmap` of the target;
- `mmap(MAP_FIXED...)` replacing the target range with a new mapping;
- destructive `mremap` move/shrink when the old target address is no longer owned by the same mapping;
- `shmdt` of the target mapping;
- internal VMA replacement paths that create a new owner for the same virtual address.

Those are owner-retirement events.

## Dynamic host PFN -> guest invoker

At `LinkAddressToGuestFunction(H, T)`:

1. Resolve the VMA containing `T` under VMA tracking.
2. Capture its mapping-owner token.
3. Record the target address and whatever ABI/signature identity is needed for compatible multi-owner promotion.
4. Register a claim conceptually equivalent to:

```text
H claim {
    guest_target: T,
    owner: token,
    ABI/signature identity: ...
}
```

5. Maintain a reverse dependency index:

```text
owner token -> set of H claims
```

When the mapping generation owning `T` is destroyed or no longer contains `T`, drop the claim and perform the already-proven exact synthetic-entry retirement transaction.

If another compatible owner for the same stable `H` remains, promote it. If no owner remains, leave `H` revoked/tombstoned rather than allowing it to fall through as ordinary x86 guest code.

On a legitimate reload, a fresh owner token can reactivate the same stable `H` with the new guest target.

This matches the successful real Vulkan PFN experiment in [`VULKAN_PFN_LIFETIME_AB.md`](./VULKAN_PFN_LIFETIME_AB.md).

## Host -> guest callback trampoline

`GuestcallToHostTrampoline` has a stronger dependency shape. A bridge can contain both:

```text
GuestUnpacker
GuestTarget
```

Those addresses may belong to different guest mappings/DSOs.

Treat the trampoline as depending on a set of owner tokens:

```text
callback bridge {
    unpacker: {address, owner_token},
    target:   {address, owner_token},
}
```

The bridge remains owned by those mapping generations. Execution still has to respect current guest protection state for each target.

Destroying either required owner generation must revoke/tombstone the bridge or move it to another fully compatible set of live claims. This prevents an X11-style callback target from remaining reachable merely because the Vulkan unpacker DSO is still mapped, and vice versa.

## Where retirement should happen

The dependency system should sit at the guest mapping-generation lifecycle layer rather than only at `dlclose` or `GuestMunmap`.

Owner-retirement operations include at least:

- `munmap`;
- `mmap(MAP_FIXED...)` replacement;
- `mremap` move/shrink/replacement when the original target address loses its owner;
- `shmdt` for target mappings;
- any internal mapping replacement path that destroys the owner generation.

`mprotect` should update protection state without assigning a fresh owner generation merely because permissions changed.

A loader-level hook can provide better semantic naming/diagnostics, but it is too narrow to be the correctness boundary.

## Ordering

For destructive owner transitions, bridge retirement should occur while the old owner identity is still queryable and before its target mapping can disappear.

The current FEX syscall ordering makes this especially important for `MAP_FIXED`: host `mmap()` executes before `TrackVMARange()` discovers/replaces the overlapped old VMA. A production dependency hook therefore needs a prepare/commit shape rather than a post-hoc scan.

A useful transaction shape is:

```text
identify old owner(s) affected by requested mapping operation
identify dependent bridge claims whose target would lose that owner
prepare retirement/revocation under consistent locks
perform host mapping syscall
if syscall succeeds:
    commit VMA tracker transition
    exact-evict/revoke affected synthetic entries
    publish replacement/promoted claims if any
if syscall fails:
    preserve original ownership and claims
```

The exact point at which dispatchers see the retirement must also prevent a peer thread from selecting old generated code during the destructive transition. That remains a concurrency-design item.

The lock order needs to remain consistent with FEX's existing VMA, thread-creation, code-invalidation, lookup-map, and thunk locks. The current internal candidate's coherent-lock experiment is evidence for one workable ordering, not yet a final API contract.

## Compatibility advantages

Owner tokens handle several compatibility cases that address-range cleanup alone does not model cleanly:

- same guest virtual address reused by a later DSO/mapping generation;
- same file loaded at two bases simultaneously;
- stable host PFN reused across reloads;
- aliases where several host PFNs point to one guest invoker;
- one host PFN with several compatible live guest owners;
- incompatible wrappers claiming one native address;
- callback bridges whose unpacker and target come from different DSOs;
- partial unmap and mapping replacement;
- temporary RW/RX protection flips without spuriously changing owner identity.

## Remaining questions

1. Whether `MappedResource` creation aligns exactly with every loader generation for the thunk DSOs in practice, including unusual loader remaps.
2. How to assign owner tokens to anonymous mappings without growing unbounded state.
3. Whether an anonymous VMA token should follow VMA splits/merges as one lineage or use a separate small owner object analogous to `MappedResource`.
4. How to quiesce a peer dispatcher that already selected an old translated `H` before retirement became visible.
5. How fork/clone should copy or regenerate owner-generation state.
6. Whether cached code-file `PendingResourceDeletions` can be reused as a natural deferred-retirement boundary or needs a distinct bridge lifetime queue.
7. How to handle partial `mremap`/split cases where the resource remains live but the specific target T leaves the surviving range.

## Current recommendation

Use `MappedResource`/VMA tracking as the source of **mapping-generation identity**, with an explicit non-reusable owner token. Keep protection state orthogonal to owner identity. Keep the multi-owner claim model, revoked-H state, and exact synthetic-key invalidation already validated by the real-FEX 2x2 and Vulkan PFN A/B.

This is a better production direction than scanning every CustomIR entry by address range on each `munmap`, while the range scan remains useful as a small causal diagnostic.

## External-contact state

No third-party/upstream interaction was performed. This note and all referenced experiments are retained in repositories owned by `teamleaderleo`.