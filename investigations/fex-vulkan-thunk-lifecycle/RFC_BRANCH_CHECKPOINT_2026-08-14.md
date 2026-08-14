# Lifetime RFC branch checkpoint — 2026-08-14

This branch was created from `investigation/fex-vulkan-thunk-lifecycle` at:

- `29ce7dbd56088dfe58f677fb7e4c36d0426b07fd` — `investigation: identify callback race marker namespace fault`

The three maintainer-facing documents on this branch are:

- `THUNK_EXECUTABLE_LIFETIME_RFC_2026-08-14.md`
- `GENERATED_RESIDENT_BRIDGE_RFC_2026-08-14.md`
- `LIFETIME_DECISION_BRIEF_2026-08-14.md`

The active investigation branch continued moving while these documents were written. Keep these later source findings in view when reviewing the RFCs.

## Callback-race carrier marker namespace fault

Commit `29ce7dbd56088dfe58f677fb7e4c36d0426b07fd` identifies a carrier-only fault in the first in-flight callback barrier: guest code and native FEX code used the same absolute `/tmp/...` marker names on opposite sides of an explicit guest rootfs boundary. They therefore addressed different backing files.

The carrier repair is to use relative marker files from a host/guest shared working directory. This finding explains the earlier `pin=81` / `unmap=81` barrier timeout and does not require a trampoline ABI or lifetime change.

This carrier fault is separate from the later deterministic full-FEX callback race result recorded elsewhere in the investigation, where an already-selected callback target survives future-entry revocation and requires an active-execution drain before reclaimable owner teardown.

## Vulkan allocator const-repack causality

After this branchpoint, active investigation commit:

- `3bc52ef5e08a5a16618eed2965fab586949cf169` — `investigation: record Vulkan allocator const-repack causality`

adds `ALLOCATOR_CONST_REPACK_AUDIT.md`.

Its causal result is a generic thunkgen constness defect reached through Vulkan allocator mediation:

1. the guest supplies a valid `const VkAllocationCallbacks*`;
2. FEX successfully repacks it and invokes guest allocator callbacks through host-callable trampolines;
3. generated host unpack code instantiates the repack wrapper after stripping pointee constness;
4. wrapper cleanup therefore treats the input as writable and copies temporary host-layout data back into the guest allocator;
5. the application-owned allocator is corrupted before a later destroy call;
6. suppressing only that automatic writeback makes both buffer and event allocator create/destroy lifetimes pass.

The preferred generic repair under investigation is to preserve source pointee constness in the generated `make_repack_wrapper<...>` type so the existing wrapper logic skips copyback for pointer-to-const inputs.

This sharpens the lifetime RFC boundary: the observed Vulkan allocator cross-call crash has a generic thunkgen const-repack owner. Keep that fix separate from resident executable lifetime and callback ownership work.

## CUDA bridge status at checkpoint

FEX workflow run `31786582378`, head `2dae03d1bd5038a5d3baa4dbc37145c7383f9782`, successfully completed:

- exact-product provenance;
- synthetic retained CUDA endpoint/native deferred control build;
- generated callback-member application;
- FEX/local-unpacker CUDA wrapper build;
- derived resident CUDA bridge build.

It then failed while preparing the local/resident amd64 rootfs images. The moved-reload runtime matrix was skipped. Treat this as build-path evidence plus a harness/rootfs failure; CUDA runtime lifetime coverage remains pending.

## Review consequence

The main recommendations remain:

- selective whole-wrapper `NODELETE` as immediate executable-lifetime containment;
- per-library direct-thunkgen resident bridge as the current unload-preserving target;
- explicit revocation plus quiescence for reclaimable application callback targets that can race native invocation;
- CustomIR mapped-block retirement/all-thread cache eviction for future dispatch correctness;
- allocator const-repack and native-first Vulkan routing as separate generator/routing findings.

No upstream contact is authorized by this checkpoint.