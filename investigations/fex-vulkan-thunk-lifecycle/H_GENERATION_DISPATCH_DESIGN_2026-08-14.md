# FEX synthetic-H generation dispatch direction — 2026-08-14

Internal design note following the same-address `MAP_FIXED` ABA reproduction and the `MREMAP_DONTUNMAP` owner-gap result.

## Why VMA OwnerID is useful but insufficient as the dispatch token

VMA OwnerID remains useful for discovering which registrations depend on a mapping lifetime. It proves same-address destructive reuse and lets retirement target the old mapping generation precisely.

`MREMAP_DONTUNMAP` demonstrates a separate lifetime axis: the old VMA and owner ID survive, while the executable page contents move to a new virtual address. The old synthetic `H -> oldVA` registration becomes obsolete even though `QueryGuestMappingOwner(oldVA)` still returns the same owner ID.

Therefore a compiled synthetic H should validate the lifetime of **its H definition / active claim**, not merely compare the target VMA owner.

## Proposed stable H-generation token

For each synthetic H, retain a process-lifetime generation descriptor. Conceptually:

```cpp
struct ThunkGenerationState {
  std::atomic<uint64_t> Generation;
};
```

The descriptor address stays stable until context/thunk-handler teardown. Every H state transition advances the generation:

- first ACTIVE registration;
- ACTIVE -> REVOKED retirement;
- ACTIVE A -> ACTIVE B promotion;
- rollback reactivation;
- explicit fresh registration after a tombstone.

A compiled H exit-link record carries:

```text
H
stable generation descriptor pointer
expected generation
T
```

The exit linker compares `descriptor->Generation` with the expected generation. A mismatch returns to current H dispatch instead of consuming the stale numeric T.

This naturally covers:

- `MAP_FIXED` same-address ABA;
- `MREMAP_DONTUNMAP` where owner ID stays unchanged;
- multi-owner promotion A -> B;
- rollback, where an old in-flight H can safely bounce through the newly restored H definition;
- explicit re-registration at the same or a different target address.

## Runtime boundary

The check should define a clear compatibility boundary with ordinary native stale-code semantics.

A useful two-check scheme around the existing exit linker is:

1. check H generation after entering the linker and before target lookup/compile;
2. after target selection/compile, re-check under the code-invalidation shared lock immediately before link/return.

If either check fails, set dispatch RIP to current H and return to the dispatcher without linking the stale T result.

Retirement advances H generation while holding the corresponding code-invalidation exclusive transaction before destructive mapping work. This yields a clean ordering:

- retirement wins first -> stale H observes a generation mismatch and bounces;
- H passes the final generation check first -> the target has crossed the selected-code boundary, which follows the native concurrency behavior already measured by the DSO controls.

The second check is needed because `ExitFunctionLink` can release/reacquire the code-invalidation lock around compilation. A generation can change while a target block is being resolved.

## Why a stable descriptor pointer is attractive

A stable descriptor lets the JIT compare one atomic word without querying Linux VMA state or acquiring the VMA lock. That keeps FEXCore independent from Linux mapping internals and avoids turning every H relink into a VMA-tree lookup.

The descriptor can live with thunk registration state and remain allocated after H becomes revoked. Old code buffers can safely hold its address until context teardown.

## Relationship to the current owner-ID token experiment

The current `ci/thunk-owner-exit-token-repair-20260814` experiment remains useful as a narrow causal proof for the witnessed `MAP_FIXED` ABA: owner `0xe` becomes a different owner at the same T, so the token should reject generation-2 T.

Treat that experiment as a stepping stone. The `MREMAP_DONTUNMAP` receipt establishes that the eventual general dispatch token should advance with H/claim state, while VMA OwnerID remains part of dependency indexing and automated retirement.
