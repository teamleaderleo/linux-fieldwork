# Current repair decision — FEX guest-thunk lifetime

Date: 2026-08-14

## Decision

The guest-thunk unload investigation is no longer a root-cause search. The defect class, the unsafe reclamation boundary, and the strongest demonstrated ownership architecture are all established.

### Proven defect

Generated thunk wrappers can advertise a native host function pointer `H` whose address remains stable while the guest executable adapter `T` belongs to an unloadable wrapper generation.

For real generated Vulkan:

```text
stock_hold=0
stock_close=139
stock_reload=139
candidate_hold=0
candidate_close=139
candidate_reload=0
```

Forced moved reload proves that the same native H can survive while wrapper/GIPA/T move. Stock FEX can continue executing stale generation-specific state. Explicit retirement/revocation/rebind repairs future dispatch and generation handoff.

Canonical defect receipt: [`REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md`](./REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md).

The same moved-generation behavior is reproduced against exact FEX-2608 `e869aa644a16e4332cdc15c1ea0b4d13d482385d`: [`FEX2608_REAL_VULKAN_PFN_RUNTIME_2026-08-14.md`](./FEX2608_REAL_VULKAN_PFN_RUNTIME_2026-08-14.md).

## Why retirement/rebind is not the preferred reclamation repair

Owner-aware retirement work established useful mechanics:

- synthetic H definition cleanup;
- shared compiled/direct-link cleanup;
- H invalidation in every live emulation thread cache;
- controlled `ACTIVE` / `REVOKED` synthetic-H policy;
- compatible multi-owner claims and promotion;
- transactional unmap handling;
- independent callback lifetime handling.

Those mechanics repair **future dispatch**.

They do not revoke host code another emulation thread already selected before physical wrapper unmap.

The forced selected-before-unmap experiment establishes:

```text
worker selects wrapper-owned T1 -> HostCode1
worker leaves lookup/invalidation guard
worker pauses
main retires definition/shared/all-thread lookup state
main physically unmaps T1 owner
worker resumes already-selected HostCode1
exit 139
```

Therefore physical reclamation of wrapper-owned executable bridge code requires either an execution-lifetime protocol or executable ownership that outlives the wrapper generation.

See [`TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md`](./TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md).

## Near-term containment — whole-wrapper NODELETE

Keeping complete generated guest thunk wrappers resident remains the smallest demonstrated containment.

Current evidence covers:

- real Vulkan dynamic PFNs;
- real Vulkan/X11 callbacks;
- real GL dynamic PFNs;
- repeated close/reopen stress;
- Vulkan constructor churn;
- current shared guest-thunk build modes.

This avoids reclamation races by avoiding wrapper reclamation entirely.

Its tradeoff is broad process-long residency: library-specific wrapper code, data, static/TLS state, and one initialized physical wrapper generation remain resident.

**Use whole-wrapper NODELETE as the best-supported near-term containment, not the preferred final ownership model.**

## Preferred long-term architecture — generated resident companion

Keep only executable bridge state that can escape wrapper lifetime process-resident; keep ordinary library wrapper code/state physically unloadable.

```text
unloadable guest wrapper
    constructors / OnInit
    library-specific mutable state
    public generated wrappers / pack-repack code
    registration using resident bridge addresses

NODELETE resident companion
    generated signature-specific CallHostFunction adapters
    fixed callback unpackers
    callback targets that are wrapper-owned but retained outside wrapper lifetime
```

This architecture is now proven across Vulkan and GL.

## Vulkan evidence

### Selected-before-unmap race — PASS

The exact barrier that exits `139` when T belongs to the wrapper returns correctly when the already-selected adapter is in the resident companion:

```text
DIAG_INFLIGHT_SELECTED guest=<resident adapter> host=<selected host code>
wrapper physically unmaps
bridge remains executable
DIAG_INFLIGHT_RESUME guest=<same resident adapter> host=<same selected host code>
worker returns correct value
wrapper reload DIFFERENT
bridge reload SAME
exit=0
```

See [`FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md`](./FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md).

### Real generated Vulkan dynamic PFN — PASS

Under stock reviewed FEX core:

```text
hold=0
close=0
reload=0
```

After final close, the five tracked guest Vulkan wrapper mappings disappear while the previously advertised native PFN still returns a real Vulkan result through the resident adapter. Reserving all old wrapper ranges forces generation 2 to move while native H and the resident adapter remain stable.

See [`REAL_VULKAN_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md`](./REAL_VULKAN_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md).

The same architecture passes against exact FEX-2608: [`FEX2608_REAL_VULKAN_SPLIT_RESIDENT_RUNTIME_2026-08-14.md`](./FEX2608_REAL_VULKAN_SPLIT_RESIDENT_RUNTIME_2026-08-14.md).

### Real Vulkan/X11 callback direction — PASS

The generated companion owns Vulkan's fixed X11 callback unpackers. Exact mapping checks prove the Vulkan wrapper is physically gone before a retained Vulkan Xlib PFN drives fresh guest X11 callbacks:

```text
MAPS_BEFORE exact_wrapper=5 bridge=5
MAPS_AFTER  exact_wrapper=0 bridge=5
AFTER_DLCLOSE_BEGIN_CALLBACK_TEST
GUEST_XSYNC display=0x12346000
GUEST_XDISPLAYSTRING display=0x12346000
AFTER_CLOSE_XLIB result=0
```

See [`REAL_VULKAN_SPLIT_X11_CALLBACK_RUNTIME_2026-08-14.md`](./REAL_VULKAN_SPLIT_X11_CALLBACK_RUNTIME_2026-08-14.md).

### Actual distro `vulkaninfo --summary` — PASS

A real amd64 Ubuntu `vulkaninfo --summary` passes under hosted ARM64 FEX with the generated split bridge, using the same FEX core and Finding-A host-thunk routing diagnostic as the unsplit control:

```text
unsplit=0
split=0
```

Both phases enumerate:

```text
Vulkan Instance Version: 1.3.275
deviceName = llvmpipe (LLVM 20.1.2, 128 bits)
driverName = llvmpipe
```

The split phase links real Vulkan dynamic PFNs to resident guest adapters throughout the workload and exits cleanly.

Hosted unsplit also exits `0`, so this is end-to-end compatibility validation of the architecture, not reproduction of the original M5 teardown failure.

See [`HOSTED_VULKANINFO_SPLIT_BRIDGE_AB_2026-08-14.md`](./HOSTED_VULKANINFO_SPLIT_BRIDGE_AB_2026-08-14.md).

## Cross-library genericity — GL PASS in both directions

GL independently proves that the architecture is not Vulkan-specific.

### Stock controls

Stock generated `libGL.so.1` physically unloads on the simple `glGetError` path and on a matched `glXGetFBConfigs` path with guest X11 pinned independently.

This is important because intermediate split candidates that retained the wrapper are therefore genuine design regressions, not normal GL loader behavior.

### Ownership lesson from failed GL candidates

A crude companion that copied the full generated GL guest output resident kept the wrapper mapped.

A narrower v3 companion still kept the wrapper mapped because the unloadable wrapper retained its original `HostPtrInvokers` registry referencing wrapper-local generated adapters.

An ELF audit falsifies GNU-unique symbol lifetime as the explanation:

```text
libGL-stock.so      UNIQUE=0
libGL-v3.so         UNIQUE=0
libGL-v4.so         UNIQUE=0
libfex-GL-bridge.so UNIQUE=0
```

The successful v4 ownership cut makes the resident companion authoritative and removes the wrapper-local adapter registry and obsolete wrapper-local malloc callback target.

### Real GL dynamic PFN — PASS

For generated `glGetError`:

```text
wrapper glXGetProcAddress -> UNMAPPED after close
resident adapter remains mapped
AFTER_CLOSE retained_error=0
old wrapper ranges reserved successfully
reload moved=1
same native H=1
exit=0
```

### Real GL callback target + unpacker — PASS

GL's host thunk retains a GuestMalloc callback whose target and unpacker were both wrapper-owned. The v4 companion moves both resident.

After physical `libGL.so.1` unload, a retained old `glXGetFBConfigs` PFN still performs fresh guest X11 callbacks and executes the process-retained resident malloc callback:

```text
AFTER_CLOSE_BEGIN
GUEST_XSYNC display=0x12346000
GUEST_XDISPLAYSTRING display=0x12346000
GL_BRIDGE_MALLOC size=1920
AFTER_CLOSE_CONFIGS ... count=240
```

All old wrapper ranges are then reserved, generation 2 moves, both native GL PFNs remain stable, and fresh callbacks/malloc execution succeed after reload and again through a retained PFN after generation 2 closes.

See [`GL_SPLIT_RESIDENT_BRIDGE_GENERICITY_2026-08-14.md`](./GL_SPLIT_RESIDENT_BRIDGE_GENERICITY_2026-08-14.md).

## Generic ownership invariant learned from GL

The cross-library rule is stronger than merely moving executable glue resident:

> when resident companion adapters become authoritative, the unloadable wrapper must relinquish parallel adapter registries/references and wrapper-owned callback targets that are retained outside the wrapper generation.

Vulkan's successful split already followed this rule by removing its wrapper-local dynamic adapter map. GL made the failure mode observable when an intermediate candidate did not.

A production implementation should make ownership singular rather than maintaining wrapper-local and resident copies as parallel address authorities.

## Generator-native bridge output — PROVEN

The first successful Vulkan/GL research companions scraped adapters and symbol lists from normal generated guest C++. That post-processing dependency is no longer necessary in principle.

A diagnostic thunkgen `-guest-bridge` output directly emits only:

- unique signature-specific `MAKE_CALLBACK_THUNK` adapters;
- generated symbol enumerators.

Exact equivalence against normal guest generation:

```text
Vulkan: adapters 476/476 exact; internal symbols 714/714 exact
GL:     adapters 736/736 exact; internal symbols 3102/3102 exact
```

The bridge outputs exclude normal API packing/public-wrapper bodies.

See [`THUNKGEN_RESIDENT_BRIDGE_OUTPUT_2026-08-14.md`](./THUNKGEN_RESIDENT_BRIDGE_OUTPUT_2026-08-14.md).

### Direct thunkgen output used in real Vulkan runtime — PASS

The resident Vulkan companion can be built directly from thunkgen's bridge fragment without generated-C++ scraping.

Real PFN matrix:

```text
hold=0
close=0
reload=0
```

Final close removes the five Vulkan wrapper mappings; retained H still returns through the direct-generated resident adapter; old wrapper ranges can be reserved; generation 2 moves; native H and resident adapter remain stable; the real Vulkan call succeeds.

See [`VULKAN_DIRECT_THUNKGEN_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md`](./VULKAN_DIRECT_THUNKGEN_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md).

## Preferred implementation cut

The research result now points to a central generator/build design rather than per-library generated-C++ scraping:

```text
thunkgen interface analysis
    -> normal unloadable guest-wrapper output
    -> resident-bridge adapter/symbol output

GuestLibs/CMake
    -> ordinary wrapper DSO
    -> NODELETE resident companion DSO
```

Start per library/per bitness. Deduplicate companions by generated signature identity later only if measurement justifies the complexity.

The generator can provide generic signature adapters and generated symbol identity. Per-library guest code still has to declare semantic callback-target ownership when the actual GuestTarget, not just the unpacker, is wrapper-owned and retained externally.

Use the existing generated thunk/signature SHA where a compatibility/deduplication identity is needed rather than inventing a parallel ABI token.

Detailed plan: [`GENERATED_RESIDENT_BRIDGE_INTEGRATION_PLAN.md`](./GENERATED_RESIDENT_BRIDGE_INTEGRATION_PLAN.md).

## Logical stale-H policy is separate from executable safety

The split research prototype permits a previously advertised H to remain callable after logical wrapper close when the native host function and resident adapter remain process-live.

A production policy may instead require stale-H rejection:

```text
H -> resident adapter -> ACTIVE / REVOKED logical state
```

This policy decision is now independent of wrapper executable reclamation. Even an already-selected adapter remains process-resident while logical state can be checked/revoked separately.

## Callback policy

If a fixed callback unpacker is wrapper-owned but the actual GuestTarget belongs to another owner, move the unpacker resident and keep the target's real owner semantics separate.

If the actual callback target is also wrapper-owned and process-retained—as GL's GuestMalloc target was—move both target and unpacker into the companion.

If the actual GuestTarget belongs to another unloadable guest owner, retain explicit owner/revocation semantics. The immutable host trampoline + atomic process-lived callback descriptor remains the preferred revocable representation.

See [`REAL_VULKAN_CALLBACK_DESCRIPTOR_RUNTIME_2026-08-14.md`](./REAL_VULKAN_CALLBACK_DESCRIPTOR_RUNTIME_2026-08-14.md).

## Current ranking

### Near-term containment

1. **Whole-wrapper NODELETE / pinning** — smallest demonstrated product lever, broad current runtime/build coverage.
2. **Generated resident companion** — stronger wrapper unload/reset semantics and now proven across Vulkan and GL, but current code is still research-only diagnostic integration.
3. **Owner-generation + execution lease/hazard** — only necessary if even resident bridge executable glue must eventually be reclaimable; largest synchronization change.

### Long-term architecture

1. **Generated process-resident companion** — strongest demonstrated balance: wrapper physical unload/reset preserved, Vulkan and GL both bridge directions pass, selected-before-unmap race passes, exact FEX-2608 passes, actual distro `vulkaninfo` passes, and generator-native bridge output is runtime-proven.
2. **Owner-generation + execution lease/hazard** — full reclamation option if process-long bridge glue is unacceptable.
3. **Whole-wrapper NODELETE** — robust containment with broader permanent wrapper state residency.

Retirement/revoked-H, callback descriptors, and target-cell experiments remain useful policy/lifetime primitives, but they are no longer the preferred physical-reclamation mechanism where a resident companion can own the escaped executable glue.

## Remaining engineering work

The high-value remaining work is productization and measurement, not diagnosis:

1. fold the proven bridge output into clean central thunkgen/GuestLibs interfaces instead of diagnostic patch helpers;
2. define per-library callback-target ownership declarations so wrapper-owned escaped targets can move resident without guessing from type alone;
3. measure resident companion RSS/PSS, relocation cost, and signature duplication across thunk libraries;
4. decide logical stale-H behavior independently of executable safety;
5. optionally repeat the final architecture on the original Apple M5 environment as a target confirmation while preserving the historical evidence separately.

## Relationship to the original Apple M5 failure

The original M5 run proves:

- enumeration succeeds after the independent debug-report routing diagnostic;
- teardown exits `139`;
- saved guest instruction fetch lies in the old `libvulkan-guest.so` range after unmap;
- guest `dlclose` suppression changes the run to `0`;
- bogus preload does not;
- pinning only `libvulkan-guest.so` changes llvmpipe and Venus runs to `0`.

Hosted work now independently proves the generated H→T lifetime defect, the selected-execution reclamation race, and a race-safe split ownership repair on real generated Vulkan and GL.

The historical M5 trace did not capture the immediate terminal H/R11 or first post-unload synthetic-entry hit. Preserve that evidence boundary.

## Submission boundary

All source changes described here are diagnostic/research code in owned repositories and forks. FEX prohibits AI-generated contribution code. Any upstream implementation must be independently derived and written by a human.

No upstream FEX interaction was made.
