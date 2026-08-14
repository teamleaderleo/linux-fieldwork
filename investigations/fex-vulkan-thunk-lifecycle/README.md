# FEX Vulkan callback routing and guest-thunk lifetime

## Current status

The investigation has two independent findings and the guest-thunk lifetime finding is now past root-cause discovery.

### Finding A — Vulkan debug-report dynamic lookup

FEX already has a custom `vkCreateDebugReportCallbackEXT` host implementation that suppresses an unsafe guest callback, but dynamic `vkGetInstanceProcAddr()` does not select it on the reviewed revisions.

The diagnostic routing correction removes the original SIGILL and lets x86-64 Vulkan enumeration proceed on the Apple M5 / FEX-2608 setup. The same routing defect was independently reproduced on hosted ARM64.

Canonical hosted receipt: [`HOSTED_ARM64_FINDING_A_CURRENT_MAIN.md`](./HOSTED_ARM64_FINDING_A_CURRENT_MAIN.md).

### Finding B — unloadable guest-thunk executable ownership

A real generated-Vulkan stock/candidate A/B proves the dynamic-PFN lifetime defect:

```text
stock_hold=0
stock_close=139
stock_reload=139
candidate_hold=0
candidate_close=139
candidate_reload=0
```

The native Vulkan PFN `H` remains stable while the guest `CallHostFunction` adapter `T` belongs to an unloadable guest-wrapper generation. Stock FEX can retain/bake the old H→T relationship after the wrapper generation disappears. Explicit retirement/revocation/rebind repairs moved-generation dispatch, but separate runtime work proves that cleanup cannot revoke a host-code pointer another thread already selected before physical unmap.

Canonical receipts:

- [`REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md`](./REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md)
- [`FEX2608_REAL_VULKAN_PFN_RUNTIME_2026-08-14.md`](./FEX2608_REAL_VULKAN_PFN_RUNTIME_2026-08-14.md)
- [`TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md`](./TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md)

## Architecture decision

### Near-term containment

**Whole-wrapper NODELETE / pinning** remains the smallest demonstrated product lever. It avoids reclamation races by keeping the complete guest thunk wrapper resident. Real Vulkan PFNs, Vulkan/X11 callbacks, GL PFNs, constructor churn, and build modes are covered.

Its cost is broad process-long wrapper residency: code/data/static/TLS state and one physical wrapper generation remain alive.

### Preferred long-term architecture

**Split process-resident guest bridge.** Keep only executable glue whose addresses can escape wrapper lifetime resident; allow ordinary library wrapper code/state to unload and reset.

```text
unloadable guest wrapper
    constructors / mutable state / public wrappers
    registration using resident bridge addresses

NODELETE resident companion
    generated signature-specific CallHostFunction adapters
    fixed callback unpackers
    callback targets that themselves are wrapper-owned and process-retained
```

This architecture now has product-sized evidence across Vulkan and GL.

## Vulkan split evidence

### Selected-before-unmap race closes

The same forced post-selection barrier that exits `139` with wrapper-owned adapter code returns correctly when the already-selected adapter lives in the resident bridge:

```text
DIAG_INFLIGHT_SELECTED guest=<resident bridge> host=<selected host code>
wrapper physically unmaps
bridge remains executable
DIAG_INFLIGHT_RESUME guest=<same bridge> host=<same selected host code>
worker returns correct value
wrapper reload DIFFERENT
bridge reload SAME
exit=0
```

See [`FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md`](./FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md).

### Real generated Vulkan PFN unload/reload

Under stock reviewed FEX core, a generated `libfex-vulkan-bridge.so` owns the dynamic signature adapter while `libvulkan.so.1` remains physically unloadable:

```text
hold=0
close=0
reload=0
```

After final close, the five tracked guest Vulkan wrapper mappings disappear. The old native PFN still returns a real Vulkan result through the resident adapter. Forced reservation of the old wrapper ranges moves generation 2 while native H and the resident adapter remain stable.

See [`REAL_VULKAN_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md`](./REAL_VULKAN_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md).

The same architecture passes on exact FEX-2608 `e869aa644a16e4332cdc15c1ea0b4d13d482385d`: [`FEX2608_REAL_VULKAN_SPLIT_RESIDENT_RUNTIME_2026-08-14.md`](./FEX2608_REAL_VULKAN_SPLIT_RESIDENT_RUNTIME_2026-08-14.md).

### Real Vulkan/X11 retained callback path

The generated companion owns Vulkan's fixed X11 callback unpackers. Exact-path mapping checks prove the guest Vulkan wrapper is physically gone before a retained Vulkan Xlib PFN causes fresh guest `XSync` / `XDisplayString` calls.

```text
MAPS_BEFORE exact_wrapper=5 bridge=5
MAPS_AFTER  exact_wrapper=0 bridge=5
AFTER_DLCLOSE_BEGIN_CALLBACK_TEST
GUEST_XSYNC display=0x12346000
GUEST_XDISPLAYSTRING display=0x12346000
AFTER_CLOSE_XLIB result=0
```

See [`REAL_VULKAN_SPLIT_X11_CALLBACK_RUNTIME_2026-08-14.md`](./REAL_VULKAN_SPLIT_X11_CALLBACK_RUNTIME_2026-08-14.md).

### Actual distro `vulkaninfo --summary`

A real amd64 Ubuntu `vulkaninfo --summary` now passes with the generated split bridge under hosted ARM64 FEX, using the same FEX core and the same Finding-A host-thunk routing diagnostic as the unsplit control:

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

The split phase logs real Vulkan dynamic PFNs linking to resident guest adapters throughout the workload and exits cleanly.

Hosted unsplit also exits `0`, so this is an end-to-end compatibility confirmation, not a reproduction of the original M5 teardown `139`.

See [`HOSTED_VULKANINFO_SPLIT_BRIDGE_AB_2026-08-14.md`](./HOSTED_VULKANINFO_SPLIT_BRIDGE_AB_2026-08-14.md).

## Cross-library genericity — GL

GL independently confirms the architecture in both lifetime directions.

Stock generated `libGL.so.1` physically unloads, including after a real generated `glXGetFBConfigs` path. Intermediate split candidates exposed an important rule: leaving the wrapper's original `HostPtrInvokers` registry in place caused the split wrapper to remain mapped even though adapters had moved resident.

The successful v4 cut removes the wrapper-local adapter registry and wrapper-local malloc callback target, making the companion authoritative.

### Dynamic PFN

For real generated `glGetError`:

```text
wrapper glXGetProcAddress -> UNMAPPED after close
resident adapter remains mapped
AFTER_CLOSE retained_error=0
old wrapper ranges reserved successfully
reload moved=1
same native H=1
exit=0
```

### Process-retained callback target + unpacker

GL's host thunk retains a GuestMalloc callback whose target and unpacker were both wrapper-owned. The v4 companion moves both resident.

After physical `libGL.so.1` unload, the retained old `glXGetFBConfigs` PFN still performs fresh X11 callbacks and invokes resident GuestMalloc:

```text
AFTER_CLOSE_BEGIN
GUEST_XSYNC display=0x12346000
GUEST_XDISPLAYSTRING display=0x12346000
GL_BRIDGE_MALLOC size=1920
AFTER_CLOSE_CONFIGS ... count=240
```

Forced moved reload preserves both native GL PFNs and the final retained call still works after generation 2 closes.

See [`GL_SPLIT_RESIDENT_BRIDGE_GENERICITY_2026-08-14.md`](./GL_SPLIT_RESIDENT_BRIDGE_GENERICITY_2026-08-14.md).

## Generator-native bridge output is proven

The first Vulkan/GL research companions scraped adapter and symbol fragments from normal generated guest C++. That tooling dependency is no longer necessary in principle.

A diagnostic thunkgen `-guest-bridge` output directly emits only:

- unique signature-specific `MAKE_CALLBACK_THUNK` adapters;
- generated symbol enumerators.

Exact comparison against normal guest generation:

```text
Vulkan: adapters 476/476 exact; internal symbols 714/714 exact
GL:     adapters 736/736 exact; internal symbols 3102/3102 exact
```

The bridge fragments exclude normal API packing/public-wrapper bodies.

See [`THUNKGEN_RESIDENT_BRIDGE_OUTPUT_2026-08-14.md`](./THUNKGEN_RESIDENT_BRIDGE_OUTPUT_2026-08-14.md).

The direct thunkgen output also builds the real Vulkan resident companion and passes the real PFN matrix:

```text
hold=0
close=0
reload=0
```

See [`VULKAN_DIRECT_THUNKGEN_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md`](./VULKAN_DIRECT_THUNKGEN_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md).

## Generic ownership rule learned from GL

Moving executable glue resident is not sufficient if the unloadable wrapper still owns a parallel registry/reference graph for wrapper-local copies.

The successful cross-library rule is:

> resident companion adapters become the authoritative dynamic adapters; unloadable wrappers should relinquish wrapper-local adapter registries and wrapper-owned callback targets that are retained outside the wrapper generation.

This is a generator/build ownership rule, not a Vulkan-specific exception.

## Retirement-policy mechanics that remain useful

The split architecture separates executable reclamation safety from logical stale-handle policy. Proven policy mechanisms remain useful when needed:

- synthetic H `ACTIVE` / `REVOKED` state;
- all-thread future-dispatch invalidation when baked targets change;
- compatible multi-owner H claims and promotion;
- generated thunk/signature SHA as compatibility identity;
- transactional `munmap` handling;
- immutable host trampoline + atomic callback descriptor when the actual GuestTarget belongs to another unloadable owner.

A target cell alone is insufficient for reclaiming wrapper-owned executable code because another thread can load old T immediately before retirement and branch after unmap.

Detailed decision: [`CURRENT_REPAIR_DECISION_2026-08-14.md`](./CURRENT_REPAIR_DECISION_2026-08-14.md).

## Original Apple M5 evidence boundary

Original target:

```text
Host: Apple M5 MacBook Air, arm64, Darwin 25.6.0
Guest: Fedora 44 aarch64
FEX: FEX-2608 / e869aa644a16e4332cdc15c1ea0b4d13d482385d
```

After the independent Finding-A routing diagnostic, x86-64 `vulkaninfo --summary` enumerates and then exits `139` during teardown. Saved guest RIP lies in the former `libvulkan-guest.so` executable image after it is unmapped.

Controls:

```text
normal teardown                   -> 139
bogus preload                     -> 139
guest dlclose no-op               -> 0
only libvulkan-guest.so pinned    -> 0
pinned Venus run                  -> 0
```

The historical trace did not capture the immediate terminal H/R11 or first post-unload synthetic-entry hit. Preserve that evidence boundary. Hosted generated-Vulkan work independently proves the H→T lifetime defect and the race-safe ownership repair.

Original receipts: [`EVIDENCE.md`](./EVIDENCE.md), [`TEARDOWN_CHRONOLOGY.md`](./TEARDOWN_CHRONOLOGY.md).

## Current engineering work

Root-cause discovery is complete. Remaining work is productization/measurement:

1. fold bridge output into clean central thunkgen/GuestLibs interfaces rather than diagnostic patch helpers;
2. generalize library callback-target ownership declarations without guessing from type alone;
3. measure resident companion RSS/PSS and signature duplication across thunk libraries;
4. decide logical stale-H policy independently of executable safety;
5. optionally repeat the final architecture on the original M5 environment as a target confirmation, while preserving historical evidence separately.

## Contribution and contact boundary

All FEX source changes in this investigation are diagnostic/research code on local trees or owned forks. FEX prohibits AI-generated contribution code; any upstream implementation must be independently derived and written by a human in compliance with that policy.

No upstream FEX issue, PR, comment, review, reaction, push, discussion, or other mutation has been made by this investigation.

When an external FEX GitHub reference is necessary, use the redirect form, for example:

```text
https://redirect.github.com/FEX-Emu/FEX/commit/e869aa644a16e4332cdc15c1ea0b4d13d482385d
```
