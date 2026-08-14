# VMA / `MappedResource` ownership design note

Date: 2026-08-14

## Why this exists

The runtime experiments have established that a stable synthetic/native thunk address `H` can outlive several guest load generations, while the guest executable target `T` belongs to one particular generation and must be retired when that generation loses executable ownership.

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

Assign a fresh token when a `MappedResource` is created. For executable anonymous mappings that have no `MappedResource`, assign an equivalent VMA-generation token.

A bridge dependency then records the token that owned its guest executable address at registration time.

## Dynamic host PFN -> guest invoker

At `LinkAddressToGuestFunction(H, T)`:

1. Resolve the VMA containing `T` under VMA tracking.
2. Verify that the mapping is executable (or is valid under the same `READ_IMPLIES_EXEC` policy used elsewhere).
3. Capture its owner token.
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

When that owner loses the executable mapping containing `T`, drop the claim and perform the already-proven exact synthetic-entry retirement transaction.

If another compatible owner for the same stable `H` remains, promote it. If no owner remains, leave `H` revoked/tombstoned rather than allowing it to fall through as ordinary x86 guest code.

On reload, a fresh owner token can reactivate the same stable `H` with the new guest target.

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

The bridge remains callable only while **all required executable dependencies are live**.

Retiring either token must revoke/tombstone the bridge or move it to another fully compatible set of live claims. This prevents an X11-style callback target from remaining reachable merely because the Vulkan unpacker DSO is still mapped, and vice versa.

## Where retirement should happen

The dependency system should sit at the guest executable-mapping lifecycle layer rather than only at `dlclose` or `GuestMunmap`.

Operations that can change dependency validity include at least:

- `munmap`;
- `mmap(MAP_FIXED...)` replacement;
- `mremap` move/shrink/replacement;
- `mprotect` that removes executable permission;
- `shmdt` for executable shared-memory targets;
- any internal mapping replacement path that destroys executable ownership.

A loader-level hook can provide better semantic naming/diagnostics, but it is too narrow to be the correctness boundary.

## Ordering

For destructive operations, bridge retirement should occur while the old owner identity is still queryable and before its executable target can disappear.

A useful transaction shape is:

```text
identify affected owner/dependencies
lock bridge/claim registry
mark claims retiring or revoked
lock code invalidation transaction
exact-evict affected synthetic H entries globally
publish replacement/promoted claims if any
make retirement visible to dispatchers
perform destructive mapping transition
release old owner identity after invalidation bookkeeping is complete
```

The exact lock order needs to remain consistent with FEX's existing VMA, thread-creation, code-invalidation, lookup-map, and thunk locks. The current internal candidate's coherent-lock experiment is evidence for one workable ordering, not yet a final API contract.

## Compatibility advantages

Owner tokens handle several compatibility cases that address-range cleanup alone does not model cleanly:

- same guest virtual address reused by a later DSO generation;
- same file loaded at two bases simultaneously;
- stable host PFN reused across reloads;
- aliases where several host PFNs point to one guest invoker;
- one host PFN with several compatible live guest owners;
- incompatible wrappers claiming one native address;
- callback bridges whose unpacker and target come from different DSOs;
- partial mapping/protection transitions.

## Remaining questions

1. Whether `MappedResource` creation aligns exactly with every loader generation for the thunk DSOs in practice, including unusual loader remaps.
2. How to assign owner tokens to anonymous executable mappings without growing unbounded state.
3. Whether execute permission should be a property of the owner token or a finer VMA dependency under that owner; a resource can contain executable and non-executable segments.
4. How to quiesce a peer dispatcher that already selected an old translated `H` before retirement became visible.
5. How fork/clone should copy or regenerate owner-generation state.
6. Whether cached code-file `PendingResourceDeletions` can be reused as a natural deferred-retirement boundary or needs a distinct bridge lifetime queue.

## Current recommendation

Use `MappedResource`/VMA tracking as the source of **mapping-generation identity**, with an explicit non-reusable owner token. Keep the multi-owner claim model and exact synthetic-key invalidation already validated by the real-FEX 2x2 and Vulkan PFN A/B.

This is a better production direction than scanning every CustomIR entry by address range on each `munmap`, while the range scan remains useful as a small causal diagnostic.

## External-contact state

No third-party/upstream interaction was performed. This note and all referenced experiments are retained in repositories owned by `teamleaderleo`.