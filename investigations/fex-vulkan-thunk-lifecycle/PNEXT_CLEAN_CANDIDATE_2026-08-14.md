# Clean Vulkan instance pNext callback candidate — 2026-08-14

Status: **source-only owned-fork candidate packaged from an already-passing runtime experiment**.

Reviewed base:

```text
repository: teamleaderleo/FEX
base: 71afe476751deac24adabd1adb575fd2337b6e0a
branch: fix/vulkan-instance-callback-pnext
candidate: 0a19582b538b521420df07ffadeb13679351a4c3
commit: ThunkLibs/vulkan: mediate instance pNext debug callbacks
```

The candidate is exactly one commit ahead of the reviewed base and changes only:

```text
ThunkLibs/libvulkan/Host.cpp
```

Compare stats:

```text
files: 1
additions: 22
deletions: 11
changes: 33
```

## Bug family

This is separate from the dynamic GIPA/GDPA custom-routing bug.

`vkCreateInstance` can receive callback-bearing structures through its `pNext` chain. The reviewed FEX wrapper removed `VkDebugReportCallbackCreateInfoEXT` but could still expose or skip `VkDebugUtilsMessengerCreateInfoEXT` in specific chain arrangements.

## Candidate behavior

The candidate keeps the debug-utils create-info in the chain but replaces its guest callback pointer with FEX's existing ARM-safe dummy callback.

The pNext walker also re-examines the newly linked node after removing a debug-report record. That matters for an adjacent chain such as:

```text
VkDebugReportCallbackCreateInfoEXT
  -> VkDebugUtilsMessengerCreateInfoEXT
  -> ...
```

Without re-examining the replacement node, removing the first record can advance past the second one.

## Runtime evidence inherited by this package

The source-only branch was produced from the same clean transformation used by the previously retained combined ARM64 experiment.

That experiment passed:

```text
PNEXT_ZERO_CREATE result=0 callback_count=0
PNEXT_ADJACENT_CREATE result=0 report_count=0 utils_count=0
```

The combined run also passed direct/dynamic callback routing and proc-address semantics, so the pNext transformation was exercised in a working FEX Vulkan environment rather than only compiled.

Combined receipt:

```text
workflow: Vulkan combined routing candidate
run: 31776341731
job: 94692442902
carrier: c65299736980783a622d3a918811dae832dea075
artifact: 9210122391
artifact SHA-256: b509e96ccba00a0cc08c06b86beb9d5d9ef4d4a622c155e08c77ed7b5d74cd3b
```

## Packaging receipt

The dedicated packaging workflow checked out the reserved candidate branch at the exact reviewed base, applied the clean transformation, required `git diff --check`, asserted that the only changed path was `ThunkLibs/libvulkan/Host.cpp`, committed, and pushed the source-only branch.

```text
workflow: Package Vulkan instance pNext candidate
run: 31782277563
carrier: 52a12963cc10f2348dc054fc561325cc15c5caee
result: success
candidate: 0a19582b538b521420df07ffadeb13679351a4c3
parent: 71afe476751deac24adabd1adb575fd2337b6e0a
```

## Boundary

Do not merge this candidate conceptually with:

- dynamic custom proc-address registration;
- `VkAllocationCallbacks` mediation;
- guest Vulkan thunk unload/reload lifetime.

They touch nearby Vulkan thunk code but have independent causes and regression evidence.

No upstream FEX state was changed or contacted.
