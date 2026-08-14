# RFC: Executable Lifetime for Generated Guest Thunks

Status: internal investigation proposal, 2026-08-14

Scope: FEX fork and Fieldwork evidence only. This document does not authorize upstream contact.

## Decision

Use two policies, because the evidence now separates two lifetime classes cleanly.

1. **Immediate containment:** mark affected generated shared guest thunk libraries `DF_1_NODELETE` when executable addresses from that library can escape its loader lifetime.
2. **Long-term unload-preserving design:** emit a **per-thunk-library process-resident generated bridge**. Keep public API packers in the ordinary guest wrapper and place escaping FEX-owned executable adapters in a private resident sidecar.
3. **Application-owned callbacks:** represent callback ownership explicitly. Revocation must stop new entries, and owner teardown must drain in-flight callback execution before reclaiming callback code or state when the native side can race unload.
4. **Stateful/custom semantic helpers:** keep API-specific handling explicit. A signature-derived bridge cannot infer allocator ownership, callback-table semantics, or object lifetime rules.

The per-library resident bridge is the first long-term target. Cross-library signature deduplication can be reconsidered after ABI compatibility, annotation identity, namespace behavior, and footprint are measured across more thunk families.

## Problem

Generated guest thunk code is currently packaged inside ordinary unloadable guest wrappers. Some generated executable addresses escape that wrapper through native-library state, FEX state, proc-address results, callback trampolines, or callback unpackers. Once a consumer retains one of those addresses, `dlclose()` of the wrapper can leave a live reference pointing into an unmapped image.

The same investigation also exposed a related FEX dispatch problem: CustomIR-backed guest targets can remain reachable through compiled holders after ordinary mapped-code retirement paths have removed the owner mapping. Exact mapped-block retirement and all-thread cache eviction repair future dispatch to a replacement mapping, but they cannot rescue a callback or guest target already selected for execution.

These are connected by one rule:

> Any FEX-owned executable address that can escape into a longer-lived consumer needs executable lifetime at least as long as every consumer that may invoke it.

Application callback targets add a second rule:

> A stable FEX adapter can preserve the bridge entrypoint, while the application-owned callback target and state still require explicit ownership, revocation, and quiescence when they can be reclaimed.

## Lifetime classes

### A. Signature-derived FEX adapters

Examples:

- guest callers used for indirect function pointers returned through APIs such as Vulkan or GL proc-address paths;
- host-to-guest callback unpackers generated from ordinary callback signatures;
- callback unpackers discovered through nested callback-bearing aggregate members.

These are determined by ABI/signature plus generator annotations. They carry no application object identity. They are good candidates for process lifetime.

Policy: emit them into the resident bridge.

### B. Library-specific escaping FEX helpers

Some executable helpers or metadata have library-specific meaning even though FEX owns them. Examples include special thunk markers, custom callback-table glue, and generated targets whose identity depends on a library-specific annotation or custom implementation seam.

Policy: keep them in the per-library resident sidecar when they can escape wrapper lifetime. Keep the custom semantic contract visible in the library interface.

### C. Application-owned callback target and state

A native library may retain a callback supplied by the guest and invoke it after the initiating guest-to-host call returns. The resident bridge can keep the FEX unpacker executable. It cannot make the guest callback target or its user data valid after the application tears them down.

Policy:

1. keep a stable callback descriptor/trampoline identity for as long as the native side may use it;
2. revoke before owner teardown so new entries are rejected or diverted;
3. drain active executions before reclaiming the target/state when an invocation can race teardown;
4. roll back revocation if the operation that was supposed to retire the owner mapping fails and the owner remains live.

A deterministic full-FEX race demonstrated the distinction: descriptor/revocation plus cache invalidation still crashed after a callback had already selected the retiring guest target; adding an active-execution drain changed that same race from exit 139 to exit 0.

### D. Stateful/custom semantic helpers

Examples include Vulkan allocation-callback handling and APIs where the helper carries ownership rules beyond a pure ABI adapter.

Policy: solve these as semantic marshalling problems. They may use resident bridge primitives, but bridge residency alone is insufficient.

## Evidence

### Vulkan

The investigation demonstrated all of the following with a resident `libfex-vulkan-bridge.so` and an unloadable public Vulkan guest wrapper:

- a retained dynamic PFN remained callable after the public wrapper unmapped;
- a host-to-guest X11 callback remained callable after wrapper unmap;
- forced moved wrapper reload changed the wrapper address while the retained native function and resident invoker remained usable;
- a bridge-only thunkgen input could be derived from function types;
- later direct thunkgen work emitted the bridge role directly, removing the need to parse/post-process generated C++.

Whole-wrapper `NODELETE` also passed exact mapping accounting: the remaining mapping matched the guest Vulkan wrapper footprint and prevented the stale executable reference from becoming unmapped.

### GL

A split resident GL experiment preserved retained indirect guest-call adapters and GLX host-to-guest callbacks across wrapper close and moved reload. This extended the idea beyond Vulkan-specific proc-address behavior.

### DRM nested callbacks

Generated nested callback conversion found callback-bearing members in `drmEventContext`, reduced them to unique callback signatures, generated aggregate copy/repack code, and placed the callback unpackers in a resident bridge.

The completed run showed:

- native control: exit 0;
- pristine FEX reference: exit 132;
- generated wrapper-local unpacker reference: exit 0;
- generated resident unpacker: exit 0;
- ordinary `libdrm-guest.so` depended on `libfex-drm-bridge.so` and carried no `NODELETE` flag;
- the bridge carried `DF_1_NODELETE`;
- the actual guest callback was delivered with the expected arguments.

This is important because it exercises generator-discovered nested callbacks, not a Vulkan-only handcrafted sidecar.

### CustomIR retirement

The investigation isolated stale compiled-holder behavior for CustomIR guest targets. Regular range invalidation misses those targets because they are excluded from the ordinary guest-code-range index. Exact mapped-block retirement plus exact all-thread cache eviction repairs future holder-to-target rebinding.

This belongs in the lifetime story because unloading an executable owner has two obligations:

- future dispatch must stop selecting retired targets;
- already-selected or concurrently executing targets need a separate quiescence policy when reclamation is allowed.

### In-flight callback race

A deterministic callback race supplied the missing negative control for revocation-only designs. Once an execution has crossed the revocation decision and selected the owner target, invalidating future lookup state cannot revoke that execution. A drain/epoch/refcount-equivalent mechanism is required before target reclamation.

## Required invariants

A long-term implementation should maintain these invariants:

1. Every escaping FEX-owned executable address remains mapped and executable for every consumer lifetime that may invoke it.
2. The public guest wrapper can physically unmap in the resident-bridge design.
3. Resident bridge executable identity remains stable across close/reopen and moved wrapper generations.
4. Signature identity includes ABI-relevant information and generator annotations, not only a textual C function prototype.
5. Application callback target/state lifetime remains explicit and separate from signature-adapter lifetime.
6. Revocation prevents new callback entries before owner reclamation.
7. In-flight callback execution reaches quiescence before reclaiming an application-owned executable target/state when the native side can race teardown.
8. Failed owner retirement preserves or restores a usable callback registration state.
9. Future CustomIR dispatch cannot retain stale executable targets after mapped-block retirement.

## Immediate containment: selective `NODELETE`

For an affected generated shared guest thunk library, whole-wrapper `DF_1_NODELETE` is the smallest demonstrated containment. It preserves every wrapper-local executable address and avoids having to classify each escaping address before the bug is contained.

Use it selectively for thunk families with demonstrated or credible escaping executable state. Keep exact mapping/footprint measurements in the evidence so the memory cost remains reviewable.

This containment is intentionally broader than the long-term ownership model. Its value is small code change, easy review, and strong lifetime guarantee.

## Long-term implementation sequence

1. Land or carry selective whole-wrapper `NODELETE` containment for affected shared guest thunks.
2. Repair mapped-block retirement for CustomIR/synthetic guest targets so future dispatch is evicted across thread caches.
3. Extend direct thunkgen output to emit a per-library resident bridge alongside the ordinary guest wrapper.
4. Move signature-derived indirect callers, callback unpackers, nested callback unpackers, and escaping generated helpers into that bridge.
5. Add explicit callback descriptors plus revocation/drain semantics to APIs whose native side may retain application callbacks across owner teardown.
6. Keep allocator and other stateful/custom semantic marshalling as separately reviewed library logic.
7. Measure bridge footprint, namespace behavior, 32-bit behavior, annotation compatibility, and duplicate signatures across libraries.
8. Revisit process-global cross-library dedup only if the measurements show a worthwhile benefit and a safe identity rule.

## Deliberate exclusions

Keep these findings out of the core lifetime decision so review stays tractable:

- native-first Vulkan proc-address routing;
- Vulkan allocation-callback semantic marshalling/suppression;
- reclamation of process-lifetime signature bridges;
- global cross-library signature deduplication in the first implementation.

They can consume resident bridge primitives later without being prerequisites for the lifetime fix.

## Evidence limits

The historical Apple M5 teardown signature has not been captured directly on the exact historical product stack during this investigation. Exact FEX-2608 Ubuntu/Fedora/X11 `vulkaninfo` probes in the available hosted environment did not reproduce that teardown failure.

The lifetime mechanism is independently reproduced through retained executable references, wrapper unmapping, moved reload, nested callbacks, CustomIR retirement, and a deterministic in-flight callback race. The historical product linkage should continue to be described as an evidence-backed mechanism hypothesis unless an exact historical trace is obtained.

CUDA is still an open extension point. The latest generator/resident build reached the rootfs preparation step, where the harness failed before executing the moved-reload matrix. It supplies build-path evidence only.

## What would reopen this decision

Revisit the per-library resident policy if any of these occur:

- resident bridge footprint becomes material across common process workloads;
- loader namespaces produce incompatible bridge identity or visibility behavior;
- 32-bit guest generation exposes an ABI mismatch;
- two thunk libraries require incompatible adapter semantics for signatures that currently appear identical;
- packaging cannot keep the bridge private while satisfying loader lookup requirements;
- a real workload requires safe reclamation of signature-derived FEX bridge code during process lifetime.

Until one of those conditions appears, the evidence supports selective `NODELETE` now and a generated per-library resident bridge as the unload-preserving destination.