# Competing guest-thunk lifetime designs

This records what each local implementation changed, what it fixed, and where it failed under the common suite in [`results.tsv`](./results.tsv).

## 1. Unload-owned deregistration

Implementation: associate each native-PFN -> guest-invoker registration with the load instance that created it. On unload, erase every owned PFN entry before unmapping the guest DSO.

Score: **10/15**.

Fixes:

- ordinary unload/reload;
- same native PFN reused after reload;
- different guest load bases;
- independent PFNs from multiple thunk DSOs;
- guest->host dynamic function pointers that return through the registry;
- stale registry and metadata cleanup.

Vulnerable:

- compatible aliases sharing one native PFN lose the previous owner when the newest owner unloads;
- host->guest callback trampolines retain raw guest PCs;
- compiled/raw targets captured before deregistration remain executable-looking;
- unload can unmap after another thread has selected the target and before that thread jumps.

Characteristic failures:

- `host_to_guest_callback`: `before=EXEC, after_close=UAF`
- `code_cache_stale_target`: `compiled_after_close=UAF`
- `concurrent_unload_dispatch`: `call=UAF, close_completed_while_paused=1`

Conclusion: deregistration owns discoverability, not execution lifetime.

## 2. DSO ownership with bulk removal

Implementation: make each guest load instance an owner; maintain a per-native-PFN stack of compatible owners and a reverse owner -> PFN index. Unload removes every binding owned by the DSO in one operation, revealing an older compatible owner when present.

Score: **11/15**.

Fixes beyond plain deregistration:

- compatible aliases resolving to one native PFN;
- multiple thunk DSOs with independent bulk teardown;
- fallback to an older live owner after the newest alias owner unloads.

Vulnerable:

- callback trampolines and compiled targets that copied a guest PC outside the owned registry;
- select/check -> unmap concurrency race.

Conclusion: guest-DSO ownership is a useful indexing/reclamation mechanism, but ownership of the map entry alone does not protect copied execution targets.

## 3. Stable revocable indirection slots

Implementation: each native PFN gets a stable host-owned slot containing the current owner-qualified guest target. Compiled calls retain the slot rather than a raw guest PC. Host->guest callbacks use similarly revocable callback slots. Compatible alias owners form a stack inside the slot.

Score: **13/15**.

Fixes:

- reload and same-PFN reuse;
- new guest load bases without replacing the host-visible slot;
- compatible aliases and multiple DSOs;
- host->guest callback invalidation;
- stale compiled targets;
- cached call paths can either reject or follow a rebound slot.

Vulnerable:

- dispatch can read a valid slot, unload can invalidate and unmap, then dispatch can use the already-read old target;
- slots accumulate for unique native PFNs unless empty-slot reclamation is added.

Characteristic race:

```text
caller: read slot -> old guest target
unload: invalidate slot -> unmap guest DSO
caller: jump old target -> UAF
```

Conclusion: stable indirection solves retained identity and rebinding, yet revocation alone ends too early for in-flight execution.

## 4. Load-generation IDs

Implementation: each guest load receives a monotonically distinct generation. PFN bindings, callback handles, and cached calls carry the generation and reject execution when their generation is no longer current/live.

Score: **14/15**.

Fixes:

- same native PFN reused by a new load instance;
- different load bases;
- aliases and multiple DSOs;
- callbacks;
- stale cached targets;
- stale metadata cleanup.

Vulnerable:

- the final generation/live check races the unmap exactly like stable-slot target selection.

Characteristic failure:

`concurrent_unload_dispatch`: `call=UAF, close_completed_while_paused=1, unmapped=1`.

Conclusion: generation is excellent identity. It does not, by itself, extend lifetime through the jump.

## 5. Dispatch-time stale-target rejection

Implementation: leave stale registry rows present and scan newest-to-oldest for a currently live owner each time the registry is entered. Callback handles reject when their owner mapping is dead.

Score: **9/15**.

Fixes:

- ordinary reload and PFN reuse when execution returns through the registry;
- aliases and multiple DSOs;
- callbacks that perform the live check at dispatch.

Vulnerable:

- compiled/raw call paths bypass the registry scan;
- the final live check still races unmap;
- stale rows remain permanently unless a separate reclamation policy exists;
- teardown has no explicit invalidation-before-unmap event.

Conclusion: stale rejection is a useful secondary guard, not a primary lifetime owner.

## 6. Pin/refcount residency

Implementation: retain the guest mapping while bridge references exist; a close request leaves the old load resident. This models the successful pinned-thunk control as an explicit policy.

Score: **1/15** under tests that require real unload/reload semantics.

What it demonstrates:

- stale execution remains safe because the old image remains mapped;
- it explains why pinning `libvulkan-guest.so` is such a strong discriminator for the real crash.

Vulnerable / semantic cost:

- reload returns the same load instance and generation;
- requested new guest bases never take effect;
- close-requested mappings remain resident;
- old PFN rows and callback state remain live;
- multiple thunk DSOs can become permanently resident.

Representative results:

- `unload_reload`: `after_close=EXEC`, reload base stays `0x100000`;
- `code_cache_reload_same_pfn`: `old_unmapped=0`;
- `guest_mapping_residency_40_cycles`: `live_guest_mappings=1, close_requested_live=1`.

Conclusion: indefinite pinning is a diagnostic/workaround policy. A refcount that first blocks new users, then drains existing users, and finally unmaps becomes an execution-lease design.

## 7. Stable slot + generation + execution lease

Implementation:

- stable host-owned PFN slot;
- stable revocable callback slot;
- load-instance generation and owner metadata;
- a `draining` state that blocks new execution leases;
- each dispatch acquires a lease before committing to its guest PC and holds it through the guest transition;
- unload revokes slots, records code-cache invalidation, waits for active leases, then unmaps;
- empty slot/owner metadata is reclaimed.

Score: **15/15**.

Winning invalidation order:

`generation_draining > slot_invalidate > code_cache_invalidate > drain_complete > unmap`

Forced race result:

`call=EXEC, close_completed_while_paused=0, unmapped=1`.

The unload thread cannot complete while a caller is paused after acquiring the final execution lifetime. Once that call leaves the protected transition, the lease drains and unmap proceeds.

## Alias rule exposed by the experiment

A native PFN alone is too lossy to define alias ownership. The model uses this policy:

- compatible aliases resolving to one native PFN may share the host slot and form an owner stack;
- when the newest owner unloads, the previous compatible live owner becomes current;
- aliases requiring incompatible bridge ABIs are rejected because the PFN has already discarded the identity needed to choose between incompatible guest wrappers.

A production implementation could replace rejection with a richer dispatch key if FEX has another call identity available at that boundary.

## Invariant revealed by the competing designs

Every executable bridge or compiled path that can outlive a guest-thunk load instance must carry a revocable identity for that load instance **and hold its execution lifetime through the actual guest jump**.

Unload therefore has five lifecycle obligations:

1. prevent new lifetime acquisitions for the retiring load instance;
2. revoke or rebind all externally reachable PFN and callback bridges;
3. retire code-cache/JIT paths capable of bypassing that revocation;
4. drain executions that already acquired the retiring generation;
5. unmap and reclaim only after the drain completes.

The difference between the 14/15 generation design and the 15/15 lease design is obligation 4.
