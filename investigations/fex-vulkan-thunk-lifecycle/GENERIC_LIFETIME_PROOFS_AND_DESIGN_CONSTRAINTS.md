# Generic thunk lifetime proofs and design constraints

## Purpose

This note records the Vulkan-free lifetime experiments that now constrain any unload-preserving FEX thunk design. These experiments are deliberately smaller than the original Vulkan teardown failure: they exercise the bridge primitives directly, on hosted ARM64, through real FEX execution.

The important shift is that the investigation no longer has only a suspected stale pointer. The generic fixtures independently demonstrate three different lifetime requirements:

1. **generation identity** — the same virtual address can belong to a different guest-thunk lifetime;
2. **registry plus translated-code coherence** — changing bridge metadata without invalidating already-generated code leaves the old route executable;
3. **execution quiescence** — even complete retirement and all-thread invalidation cannot retract a transfer that another thread already selected before retirement.

A physical-unload design therefore needs to solve all three. Process residency (`DF_1_NODELETE`) avoids the dangerous physical lifetime transition. A split resident bridge runtime may preserve physical unload for wrapper-specific state while keeping escaped executable bridge identities stable.

## Experiment A — stable native H, changed guest T, stale guest-to-host bridge

### Exact FEX-2608 source

The exact-rebind workflow checks out FEX-2608 commit:

`e869aa644a16e4332cdc15c1ea0b4d13d482385d`

The hosted ARM64 workflow is retained in the owned FEX fork on branch:

`ci/thunk-rebind-diagnostic-v2-20260814`

Workflow:

`.github/workflows/thunk-exact-rebind-fex2608-arm64.yml`

The fixture deliberately mirrors Vulkan dynamic PFN behavior:

- generation G1 obtains native host function address `H`;
- guest registration creates `H -> T1`, where `T1` is guest bridge code owned by generation G1;
- G1 is unloaded;
- the old guest address range is reserved so G2 must load elsewhere;
- G2 obtains the same native host function address `H`;
- G2's guest invoker is a different address `T2`;
- calls are attempted through the retained and freshly registered bridge state.

Observed representative addresses:

```text
T1 = 0x00007ffff7da21b0
T2 = 0x00007ffff7d781b0   DIFFERENT
H  = 0x00007ffff7d80860   SAME across generations
```

The retained old `H -> T1` route faults after G1 is gone. A fresh direct host call succeeds. This reproduces the essential Vulkan lifetime relation without Vulkan, Mesa, Venus, or GPU state:

```text
stable native H
    -> guest bridge target T1 owned by G1
    -> G1 unloads
    -> native H survives
    -> T1 dies
    -> stale bridge execution faults
```

### Exact rebind diagnostic

A diagnostic explicitly removes the old H-keyed CustomIR entry, invalidates the corresponding translated execution state, and then installs `H -> T2`.

The trace shows the duplicate relationship and the retirement/re-registration sequence, including:

```text
DIAG_DUP H=<H> OLD=<T1> NEW=<T2>
DIAG_EXACT_SHARED H=<H> erased=1
DIAG_EXACT_LOCAL ...
DIAG_CUSTOM_REMOVE H=<H>
DIAG_CUSTOM_ADD H=<H> inserted=1 data=<T2>
```

After this full retirement/rebind, the new call succeeds.

**Conclusion:** the dynamic-PFN lifetime defect is generic to the bridge primitive. Vulkan is a real trigger, not the owner of the underlying lifetime rule.

## Experiment B — registry-only replacement is insufficient

A negative control changes only the registry relationship from `H -> T1` to `H -> T2` while deliberately leaving translated execution state intact.

The trace observes the duplicate and updates metadata, for example:

```text
DIAG_REGISTRY_ONLY_DUP H=<H> OLD=<T1> NEW=<T2>
```

Yet the subsequent call still faults through stale translated state.

**Conclusion:** an unload/reload repair cannot be implemented as "overwrite the map entry." The bridge registry and every translated/code-cache representation derived from that registry are one coherence domain.

A minimally credible rebind operation must invalidate the native-H execution key everywhere a compiled redirect can survive.

## Experiment C — host-to-guest callback tombstone

Host-to-guest callbacks have an independent lifetime problem: FEX-owned host trampolines can escape while their embedded `GuestUnpacker` and `GuestTarget` addresses belong to an unloadable guest generation.

A diagnostic `RetireGuestRange()` runs before guest unmap. For every FEX host trampoline whose unpacker or target overlaps the retiring guest range, it:

- replaces the trampoline's call target with a stable FEX-owned revoked handler;
- clears the retired guest addresses;
- removes the old cache key so a later same-address generation cannot silently reuse the tombstoned instance.

The escaped host trampoline itself remains executable. Calling an old callback after retirement reaches a controlled FEX-owned path and exits with diagnostic code `113` instead of fetching instructions from retired guest memory.

A fresh callback from the new generation continues to work.

**Conclusion:** escaped bridge identities do not have to become dangling executable pointers. They can be made stable and revocable. This is useful both for a full generation-aware design and for a split resident bridge-runtime design.

## Experiment D — same-address reload proves an ABA problem

A same-address reload variant deliberately allows the new guest generation to occupy the same virtual addresses as the old generation.

This is more dangerous than a changed-base crash because an address-only check sees apparently valid executable memory.

Observed behavior:

- the tombstoned old host callback is still rejected through the controlled revoked path;
- the new generation's callback succeeds;
- a retained guest-to-host `H -> T` path can silently execute through the reused address and observe new-generation behavior.

That is classic ABA:

```text
generation G1: address A means owner G1
unload G1

generation G2: address A means owner G2

A == A, but owner identity changed
```

**Conclusion:** `mapped(address)` and address equality are insufficient lifetime tests. If physical unload/reload is supported, bridge ownership needs an explicit generation/token/epoch identity. Otherwise a visible UAF can turn into silent cross-generation execution.

## Experiment E — post-selection in-flight race proves invalidation is not revocation

A stronger multithreaded fixture tests the point after a worker has already selected old guest target `T1` but before it actually resumes execution there.

This run used FEX source commit:

`71afe476751deac24adabd1adb575fd2337b6e0a`

Owned diagnostic branch:

`ci/thunk-inflight-selection-race-20260814`

Successful Actions run:

`31770286056`

The diagnostic retirement path is intentionally stronger than the registry-only test. It removes the matching H bridge and invalidates relevant translated state across all FEX threads. The worker is stopped at a deterministic barrier after selection.

### Pin control

The bridge owner remains mapped while the selected worker resumes:

```text
DIAG_INFLIGHT_SELECTED guest=T1
inflight pin keeps owner mapped before resume
DIAG_INFLIGHT_RESUME guest=T1
inflight worker returned rv=1023 want-old=1023
```

Exit: `0`.

### Physical-unmap case

The worker first selects `T1`. Another thread then retires H and invalidates all known thread caches:

```text
DIAG_INFLIGHT_SELECTED guest=T1
DIAG_MT_MATCH H=<H> T=<T1> range=<old owner>
DIAG_MT_SHARED H=<H> erased=1
DIAG_MT_THREAD H=<H> thread=<thread 1>
DIAG_MT_THREAD H=<H> thread=<thread 2>
DIAG_MT_REMOVE_ALL H=<H> handler=1
DIAG_MT_RETIRE_ALL H=<H> ...
```

The owner is then physically unmapped:

```text
inflight old invoker after dlclose T1 -> unmapped
inflight owner unmapped before resume
```

The already-selected worker resumes:

```text
DIAG_INFLIGHT_RESUME guest=T1
```

and the process exits `139`.

Final control matrix:

```text
pin=0
unmap=139
```

**Conclusion:** removal and all-thread code invalidation are prospective. They prevent future selection of the retired bridge, but they cannot retract a target already selected by an executing thread. Physical unmap therefore requires a grace period / execution lease / quiescence protocol that covers already-selected or already-entered bridge execution.

## The resulting design constraints

These experiments turn the unload-preserving design into a much more specific protocol.

### Constraint 1 — owner identity must outlive raw address reuse

Every dynamic bridge needs ownership equivalent to:

```text
(owner generation, bridge identity, native H, guest target T)
```

A raw `H -> T` pair is insufficient when either address can outlive or be reused across owner generations.

### Constraint 2 — bridge metadata and generated code must retire together

Removing or replacing the registry record without invalidating derived translated code leaves stale behavior executable.

Retirement must cover every representation capable of selecting the old target, including per-thread or shared translated caches.

### Constraint 3 — invalidation does not drain execution

Once a thread has selected an old bridge target, deleting maps and invalidating caches does not rewind that thread.

A physical-unload protocol must stop new acquisitions and wait until all old-generation executions have left the retiring code before unmap.

### Constraint 4 — escaped host callback pointers need stable retirement behavior

Host-side callback pointers may have escaped to persistent native libraries. Freeing/reusing the trampoline address is unsafe. A stable FEX-owned trampoline that can be tombstoned or generation-checked is a better lifetime primitive.

### Constraint 5 — unload ordering is a synchronization protocol, not a bookkeeping callback

For a full-reclamation design, the conceptual order is now:

```text
mark generation draining
    -> stop new bridge acquisition
    -> tombstone/revoke escaped host callbacks
    -> remove/rebind native-H bridge metadata
    -> invalidate all translated H routes
    -> wait for old-generation execution leases to drain
    -> physically unmap guest owner
    -> permit later generation registration
```

Running the unmap before the drain recreates the demonstrated post-selection fault.

## Implications for the three contracts

### Contract A — process-resident generated guest thunks (`DF_1_NODELETE`)

This avoids the dangerous bridge-owner lifetime transition. H-key redirects, callback unpackers, and already-selected executions continue to point at executable process-lifetime code.

The cost is semantic residency: wrapper static state and executable mappings persist until process exit. The investigation therefore keeps compatibility, namespace, and memory-footprint tests separate from the crash-safety result.

### Contract B — true physical unload/reload

This is now demonstrably more than an unregister hook. A correct implementation needs generation identity, cache coherence, callback revocation, and execution quiescence. Any proposal missing one of these should be expected to fail one of the generic fixtures above.

### Contract C — stable resident bridge runtime + unloadable wrapper state

This remains attractive because it can remove the most dangerous executable addresses from the unloadable lifetime while preserving fresh physical lifetime for library-specific state.

The loader-level split-runtime prototype has already survived repeated physical wrapper reloads with a stable resident adapter. The next meaningful test is to implement the same split using FEX's actual generated `CallHostFunction`/callback machinery and measure both semantics and hot-call overhead.

## Next discriminators

1. **Already-entered execution race.** Block a worker *inside* old guest bridge code, retire the generation from another thread, and attempt physical unload. This tests whether a lease must cover the entire guest bridge execution interval rather than only target selection.
2. **Repeat the in-flight race on exact FEX-2608.** The current post-selection race receipt used `71afe476...`; reproducing it on `e869aa...` closes the version gap to the original target.
3. **FEX-native split bridge prototype.** Move a generated signature adapter into process-resident code while physically reloading its wrapper owner; test changed-base and same-address generations.
4. **Namespace collision test.** Load equivalent guest thunk owners in multiple loader namespaces and determine whether process-global H-key bridge state conflates logically separate owners.
5. **Native-H collision test.** Create two live guest owners that want the same H with different T/generation identity and observe the current single-key CustomIR semantics.
6. **Performance test.** Compare current direct CustomIR redirect against generation-checked/stable-indirection and split-resident adapter designs in a hot-call loop.
7. **Original core caller proof.** The original Vulkan core can still identify the immediate final caller through guest `r11`, `rsp`, and return PC. The generic defect is now proved independently, but the original chronology deserves that exact final edge.

## Current interpretation

The generic experiments now support a stronger statement than "Vulkan unloads too early":

> FEX currently has bridge objects whose useful lifetime can exceed the physical lifetime of guest code embedded in those objects, while bridge lookup, translated execution, and in-flight execution do not share one owner-generation retirement protocol.

That is why process residency is such a powerful near-term policy: it aligns physical executable lifetime with the process-long bridge state FEX already keeps.

If true physical reclamation is required, the experiments above define the minimum problem that an alternative design has to solve.