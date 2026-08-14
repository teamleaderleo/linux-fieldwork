# Current repair decision — FEX guest-thunk lifetime

Date: 2026-08-14

## Decision

The lifetime defect is no longer a diagnosis problem. The remaining engineering choice is **where executable bridge ownership should live**.

### Proven defect

FEX's generated Vulkan wrapper can return a native host PFN `H` whose address remains stable while the guest `CallHostFunction` adapter `T` belongs to an unloadable wrapper generation.

A real generated-Vulkan stock/candidate A/B with byte-identical Vulkan thunk binaries proves the failure:

```text
stock_hold=0
stock_close=139
stock_reload=139
candidate_hold=0
candidate_close=139
candidate_reload=0
```

On forced moved reload, the same native `H` is reacquired while the wrapper/GIPA/T generation moves. Stock FEX accepts the new registration but the newly reacquired PFN still crashes. Explicit retirement/revocation/rebind changes that moved-reload call to success.

Canonical receipt: [`REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md`](./REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md).

The same real-Vulkan rebind behavior passes on exact FEX-2608 `e869aa644a16e4332cdc15c1ea0b4d13d482385d`: [`FEX2608_REAL_VULKAN_PFN_RUNTIME_2026-08-14.md`](./FEX2608_REAL_VULKAN_PFN_RUNTIME_2026-08-14.md).

## Retirement/rebind is necessary knowledge, not a complete reclamation repair

Focused runtime work established the mechanics required if generation-owned bridge code is to be retired:

- synthetic H definition cleanup;
- shared H compiled/direct-link cleanup;
- H invalidation in **every live emulation thread** cache;
- controlled `REVOKED` synthetic H state rather than falling through to native ARM bytes as x86;
- retained compatible multi-owner H claims and promotion;
- transactional `munmap` handling so a failed syscall cannot retire a still-live owner;
- independent callback lifetime handling.

Those mechanics successfully repair generation rebinding.

They do **not** make physical unmap safe when another thread already selected wrapper-owned host code.

`TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md` forces:

```text
worker selects wrapper-owned T1 -> HostCode1
worker leaves lookup/invalidation guard
worker pauses
main retires definition/shared/all-thread caches
main physically unmaps T1 owner
worker resumes already-selected HostCode1
exit 139
```

Therefore future lookup invalidation cannot revoke an already-selected transfer.

FEX's existing thread pause API is not an execution drain; it preserves interrupted execution and later restores it.

## Near-term containment: whole-wrapper NODELETE

Keeping the complete generated guest thunk wrapper resident is the smallest demonstrated containment.

Real runtime evidence now covers:

- Vulkan dynamic PFNs after ordinary guest `dlclose()`;
- Vulkan/X11 host→guest callbacks after ordinary guest `dlclose()`;
- GL dynamic PFNs across repeated close/reopen cycles;
- Vulkan constructor churn with one physical guest wrapper generation across 256 logical cycles.

The central linker policy also builds across current shared thunk modes, including representative 32-bit and special VDSO/lld cases.

This is robust because it avoids executable reclamation entirely.

Its cost is broad residency: wrapper-specific code/data/static/TLS state and one initialized generation remain process-long.

Use whole-wrapper NODELETE as the **best-supported near-term containment**, not as the preferred final ownership model.

## Preferred long-term architecture: split process-resident bridge

The stronger design keeps only **escaped executable bridge glue** process-resident while allowing the ordinary library wrapper to physically unload/reset.

```text
unloadable guest wrapper DSO
    constructors / OnInit
    library-specific mutable state
    public generated wrappers / pack-repack code
    registration that references resident bridge addresses

resident guest bridge companion (NODELETE)
    signature-specific CallHostFunction adapters
    fixed CallbackUnpack<signature>::Unpack functions
    generated signature/thunk markers needed by those adapters
```

This architecture is now proven at five levels.

### 1. Standalone loader model

The split model passes on x86-64 and AArch64, including repeated wrapper cycles.

See [`SPLIT_BRIDGE_RUNTIME_EXPERIMENT.md`](./SPLIT_BRIDGE_RUNTIME_EXPERIMENT.md).

### 2. Stock-FEX synthetic integration

Under stock FEX core, a `NODELETE` guest bridge owns the H adapter and fixed callback unpacker while a wrapper DSO owns generation-specific state.

Across five forced wrapper generations:

- wrapper mappings disappear after `dlclose()`;
- bridge mappings remain;
- retained H works **before wrapper reload**;
- retained host callback works **before wrapper reload**;
- wrapper reloads at a different address with fresh state;
- bridge adapter address stays identical.

See [`FEX_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md`](./FEX_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md).

### 3. Exact selected-before-unmap race

The proven post-selection barrier is rerun with `Tbridge` inside the resident DSO:

```text
DIAG_INFLIGHT_SELECTED guest=<resident Tbridge> host=<selected host code>
wrapper physically unmaps
bridge remains executable
DIAG_INFLIGHT_RESUME guest=<same Tbridge> host=<same selected host code>
worker returns correct value
wrapper reload DIFFERENT
bridge reload SAME
exit=0
```

The equivalent wrapper-owned-T1 experiment exits `139`.

This is the architecture discriminator:

> moving selected executable bridge glue out of the unloadable wrapper removes the proven reclamation race without requiring FEX to revoke an already-selected host-code pointer.

See [`FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md`](./FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md).

### 4. Real generated Vulkan dynamic PFN

A Vulkan-specific generated companion DSO now owns real `GetCallerForHostFunction` signature adapters while `libvulkan.so.1` remains unloadable.

Under stock reviewed FEX core:

```text
hold=0
close=0
reload=0
```

Generation 1 links:

```text
H = 0x7ffff76c80f4
resident invoker = 0x7ffff7e7bcc0
```

After final wrapper close, the five tracked guest-wrapper mappings disappear but the same old native PFN still returns a real Vulkan result through the resident adapter.

Forced wrapper reload moves GIPA/wrapper generation while keeping both native H and resident adapter stable; the real `vkEnumerateInstanceVersion` call succeeds again.

See [`REAL_VULKAN_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md`](./REAL_VULKAN_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md).

The same architecture passes on exact FEX-2608 with stock core:

[`FEX2608_REAL_VULKAN_SPLIT_RESIDENT_RUNTIME_2026-08-14.md`](./FEX2608_REAL_VULKAN_SPLIT_RESIDENT_RUNTIME_2026-08-14.md).

### 5. Real generated Vulkan/X11 callback direction

The generated companion also owns Vulkan's fixed X11 callback unpackers.

The corrected exact-path runtime proves:

```text
MAPS_BEFORE exact_wrapper=5 bridge=5
... real Vulkan Xlib PFN calls guest XSync/XDisplayString ...
MAPS_AFTER exact_wrapper=0 bridge=5
AFTER_DLCLOSE_BEGIN_CALLBACK_TEST
GUEST_XSYNC display=0x12346000
GUEST_XDISPLAYSTRING display=0x12346000
AFTER_CLOSE_XLIB result=0
REAL_SPLIT_VULKAN_X11_CALLBACK_OK
```

The actual guest Vulkan wrapper is physically gone before the retained Vulkan Xlib PFN drives fresh guest callbacks.

See [`REAL_VULKAN_SPLIT_X11_CALLBACK_RUNTIME_2026-08-14.md`](./REAL_VULKAN_SPLIT_X11_CALLBACK_RUNTIME_2026-08-14.md).

## Preferred implementation cut

The successful Vulkan research transformer is a proof, not the final generator interface.

Generalize centrally as an optional **resident bridge companion** emitted by thunk generation/build logic.

First implementation can be per library/per bitness:

```text
libvulkan.so.1                  unloadable wrapper
libfex-vulkan-bridge.so         resident companion

libGL.so wrapper                unloadable wrapper
libfex-GL-bridge.so             resident companion
```

Later, if measurement justifies it, deduplicate companions into one per-bitness bridge keyed by generated signature identity.

Use FEX's existing generated thunk/signature SHA as compatibility/deduplication identity rather than inventing a parallel ABI token.

Detailed integration plan: [`GENERATED_RESIDENT_BRIDGE_INTEGRATION_PLAN.md`](./GENERATED_RESIDENT_BRIDGE_INTEGRATION_PLAN.md).

`libGL` is already confirmed as a direct second pattern match: wrapper-local dynamic `HostPtrInvokers = GetCallerForHostFunction(...)` plus fixed `CallbackUnpack` addresses for malloc/X11 callbacks. See [`RESIDENT_BRIDGE_LIBRARY_AUDIT.md`](./RESIDENT_BRIDGE_LIBRARY_AUDIT.md).

## Logical stale-H policy becomes independent of executable reclamation

The split prototype deliberately permits a previously advertised native H to remain callable after logical wrapper close because:

- the generic adapter remains resident;
- current FEX host thunk libraries/native functions remain process-live.

A production policy may instead require stale H rejection:

```text
H -> resident adapter -> ACTIVE / REVOKED owner state
```

That policy is now separate from wrapper executable safety. Even an already-selected adapter remains process-resident while logical state can be checked/revoked independently.

This separation is the main architectural win.

## Callback policy

Where both the fixed unpacker and actual GuestTarget can outlive the wrapper, resident bridge ownership is sufficient.

Where the actual GuestTarget belongs to another unloadable guest owner, retain explicit owner/revocation semantics. The successful immutable trampoline + atomic callback descriptor remains the preferred revocable representation:

```text
escaped immutable host trampoline
    -> process-lived descriptor
         atomic LIVE / REVOKED
         GuestUnpacker
         GuestTarget
```

See [`REAL_VULKAN_CALLBACK_DESCRIPTOR_RUNTIME_2026-08-14.md`](./REAL_VULKAN_CALLBACK_DESCRIPTOR_RUNTIME_2026-08-14.md).

## Current ranking

### Near-term containment

1. **Whole-wrapper NODELETE / pinning** — smallest product lever with broad current runtime/build evidence.
2. **Generated split resident bridge** — stronger semantics and now proven on real generated Vulkan, but still research-only generator/CMake code that needs clean generalization.
3. **Owner-generation + execution lease/hazard** — required only if even resident bridge executable glue must eventually be reclaimable; largest synchronization change.

### Long-term architecture

1. **Generated split process-resident bridge** — strongest demonstrated balance: wrapper unload/reset preserved, real Vulkan both bridge directions pass, exact in-flight race passes, exact FEX-2608 passes.
2. **Owner-generation + execution lease/hazard** — full reclamation option if process-long bridge glue is unacceptable.
3. **Whole-wrapper NODELETE** — robust containment with broader permanent wrapper state residency.

Retirement/revoked-H and target-cell experiments remain valuable evidence and possible policy primitives, but they are no longer the preferred physical-reclamation mechanism when a resident adapter split is available.

## Remaining confirmation / engineering work

The high-value remaining work is now:

1. hosted actual amd64 `vulkaninfo --summary` confirmation combining the already-proven Finding A callback-routing diagnostic with the split lifetime wrapper;
2. replace Vulkan research post-processing with generator-native companion outputs;
3. generalize the companion build helper centrally;
4. run the same generated split on GL as the first non-Vulkan product family;
5. quantify resident companion footprint and signature duplication.

These are implementation/generalization gates, not open root-cause questions.

## Relationship to original Apple M5 evidence

The original M5 run proves:

- enumeration succeeds after the independent debug-report callback-routing correction;
- final teardown exits 139;
- saved guest instruction fetch lies in the old `libvulkan-guest.so` range after it is unmapped;
- disabling guest `dlclose()` changes the run to exit 0;
- bogus preload does not;
- pinning only `libvulkan-guest.so` changes the run to exit 0 for llvmpipe and Venus.

Hosted work now independently proves the generated-Vulkan H→T lifetime defect, exact FEX-2608 behavior, and a race-safe split ownership repair on real generated Vulkan.

The historical M5 trace still did not capture the immediate terminal H/R11 or first post-unload synthetic-entry hit. Preserve that evidence boundary.

## Submission boundary

All source changes described here are diagnostic/research code in owned repositories and forks. FEX's policy prohibits AI-generated contribution code. Any upstream implementation must be independently derived and written by a human.

No upstream FEX interaction was made.