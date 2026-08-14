# NODELETE residency and in-flight retirement race — 2026-08-14

## Summary

Three hosted results now constrain the FEX guest-thunk lifetime problem independently:

1. a clean exact-FEX-2608 Ubuntu `vulkaninfo` normal-vs-`DF_1_NODELETE` application A/B is non-discriminating (`0/0`);
2. a focused FEX guest residency A/B proves ordinary `dlclose` really does remove only the guest Vulkan thunk mappings in the normal arm and `DF_1_NODELETE` keeps them;
3. a deterministic two-thread FEX thunk race proves that removing H→T registration and invalidating every thread cache before unmap is still insufficient once another thread has already selected/copied T.

These results do not conflict. They say the hosted Ubuntu application does not recreate the historical Fedora teardown edge, while the lifetime variable itself is real and the narrow deregistration-only repair is not concurrency-safe.

## Clean exact-FEX-2608 application A/B

Owned-fork branch:

`ci/fex2608-nodelete-vulkaninfo-ab-clean-20260814`

Run:

`31778554202`

The workflow verifies committed product source is byte-for-byte FEX-2608 commit:

`e869aa644a16e4332cdc15c1ea0b4d13d482385d`

excluding only the fork-local research-policy notes and the CI carrier. The historical `vkCreateDebugReportCallbackEXT` lookup diagnostic and the Vulkan-only `-z,nodelete` flag are applied only inside the runner.

Both guest wrappers were built from the same FEX-2608 source. `readelf` verifies the normal wrapper has no `DF_1_NODELETE` and the candidate wrapper does.

The guest application is the real Ubuntu 24.04 x86-64 distro `vulkaninfo` 1.3.275. Both arms enumerate host llvmpipe and exit cleanly:

```text
normal=0
nodelete=0
```

Interpretation limit: this is a clean negative application differential, not a refutation of the historical lifetime failure. The historical crashing guest was Fedora 44 x86-64 `vulkaninfo`, not Ubuntu 24.04. The next useful discriminator is therefore Fedora 44 guest userspace on the same exact FEX-2608 hosted runtime.

## Direct FEX guest Vulkan residency A/B

Owned-fork branch:

`ci/agent-v-nodelete-residency-20260814`

Run:

`31777862101`

The probe loads guest `libvulkan.so.1`, snapshots `/proc/self/maps`, performs the final ordinary application `dlclose`, then snapshots again.

Observed byte totals for the selected Vulkan/X11 dependency set:

```text
normal loaded:          4,296,704
normal after close:     3,985,408
NODELETE loaded:        4,296,704
NODELETE after close:   4,296,704
```

The normal loss is exactly:

```text
311,296 bytes = 0x4c000
```

Map receipts show that this is exactly the five mappings belonging to guest `libvulkan.so.1`. Guest X11, libstdc++, libgcc, and the native host Vulkan loader remain mapped in both arms.

Therefore `DF_1_NODELETE` is not merely correlated with a larger resident set: under FEX it specifically changes the guest Vulkan thunk's final-close lifetime.

## Deterministic in-flight selection race

Owned-fork branch:

`ci/thunk-inflight-selection-race-20260814`

Run:

`31770286056`

Source under test in this mechanism lane is FEX commit `71afe476751deac24adabd1adb575fd2337b6e0a`, not exact FEX-2608.

The diagnostic inserts a deterministic barrier after a worker has selected the guest bridge target T but before that selected transition completes. The other thread then closes the owner DSO.

Before physical unmap the retirement diagnostic successfully:

- finds the H→T owner-range match;
- erases the shared bridge registration;
- invalidates both thread caches;
- records the owner as retired.

In the real-unmap arm, the owner mapping is then gone before the worker is released. When the already-selected transition resumes, the process exits 139.

Matrix:

```text
pin=0
unmap=139
```

The pinned control returns through the selected old target correctly because its code remains mapped.

This directly falsifies the candidate invariant:

> remove the H→T registry row and invalidate all cached code before `munmap`, then unmap is safe.

It is not safe if another thread has already acquired T for an in-progress transition.

## Design consequence

A generic repair needs an execution-lifetime rule in addition to discoverability and cache invalidation. The strongest current direction remains:

- stable externally published bridge state;
- load-generation identity rather than raw-address identity;
- revocation/rebind during generation retirement;
- bridge-key and target-range code invalidation where appropriate;
- an execution lease or equivalent quiescence covering the FEX-owned select→guest-transition/return window;
- physical unmap/reclamation only after those hidden FEX transitions are drained.

This does not promise that an application may legally call an arbitrary stale proc pointer after its owner has been closed. The lifetime mechanism protects FEX-created hidden dependencies and in-flight transitions that must remain coherent while legal teardown proceeds.

## Immediate next discriminator

The historical target-executed environment used Fedora 44 x86-64 `vulkaninfo` inside FEX. The clean hosted A/B used Ubuntu 24.04 x86-64 `vulkaninfo`.

Re-run the exact-FEX-2608 hosted carrier with Fedora 44 guest userspace while keeping the host llvmpipe side constant. Outcomes:

- Fedora guest reproduces exit 139 while Ubuntu guest remains 0: localizes the trigger to guest loader/tool/userspace behavior;
- Fedora guest remains 0: move the split to host Mesa/Vulkan-loader version, VM/runtime timing, or another workstation-specific environment difference.
