# Vulkan callback-routing convergence review

## Purpose

This record compares the source/design audit in `DYNAMIC_CUSTOM_ROUTING_AUDIT.md` with the hosted ARM64 probe lane on `probe/fex-vulkan-callback-ci`, and records the assumptions that still need executable checks.

Internal references:

- [investigation PR #669](https://github.com/teamleaderleo/linux-fieldwork/pull/669)
- [Finding A issue #670](https://github.com/teamleaderleo/linux-fieldwork/issues/670)
- [source/design audit](./DYNAMIC_CUSTOM_ROUTING_AUDIT.md)

FEX source under comparison remains `71afe476751deac24adabd1adb575fd2337b6e0a`. FEX upstream remains untouched. The owned FEX fork has a `linux-fieldwork/fex-vulkan-callback-ci` branch at that exact source revision for later experimental candidates.

## Where the lanes agree

Both lanes independently identify the same three internal Vulkan functions declared `custom_host_impl` but omitted from `LookupCustomVulkanFunction()`:

- `vkCreateDebugReportCallbackEXT`
- `vkDestroyDebugReportCallbackEXT`
- `vkCreateDebugUtilsMessengerEXT`

Both lanes also converge on the same production-design constraint: adding those names to a common manual lookup is useful for causality, but a durable fix also needs to preserve Vulkan proc-address availability and scope rules.

Preferred direction:

1. ask native Vulkan for the exact GIPA/GDPA query;
2. preserve native `NULL`;
3. when native lookup succeeds and FEX metadata marks the command `custom_host_impl`, substitute the FEX implementation;
4. otherwise return the native function pointer.

The long-term custom-routing registry should preferably be generated from the existing `custom_host_impl` metadata, or mechanically checked against it.

## Cross-review findings in the hosted probe

### Wrong-ABI selection was possible

The workflow previously selected the first installed `libvulkan-host.so` using `find ... | head -1`. A retained hosted run selected `HostThunks_32/libvulkan-host.so` for the x86-64 probe.

That makes an all-variants-fail result non-discriminating. The workflow now selects explicit 64-bit `GuestThunks` / `HostThunks` paths, rejects `_32` paths, and selects candidate host thunks from a temporary install rather than from the first build-tree match.

### Direct-call control existed but was unused

The C probe already supported both `gipa` and `direct` resolution. CI only ran `gipa` before this review.

The workflow now runs direct and dynamic report/utils cases separately. This tests the specific Finding A prediction: the existing direct thunk path should use the custom wrapper, while the broken dynamic path can bypass it.

If healthy direct and dynamic baseline cases fail identically, the current source explanation must be reopened.

### Hosted Clang state can vary

One ARM64 runner stopped during FEX CMake configure because a Clang 17 CMake package referenced a missing archive even though Clang 18 packages were installed. A fresh runner with the same workflow later passed FEX configure.

That failure is classified as runner/package-state variability. It is not Vulkan evidence. If it recurs consistently, the workflow should pin LLVM/Clang CMake package directories explicitly.

## Blind spots now added to the matrix

A new test-only `procaddr_semantics_probe.c` checks cases that a naive three-name fix can get wrong:

- `GIPA(NULL, "vkCreateInstance")` should produce a function pointer;
- `GIPA(NULL, "vkCreateDevice")` should return `NULL`;
- `GIPA(NULL, "vkGetDeviceProcAddr")` should return `NULL`;
- `GIPA(instance, "vkGetInstanceProcAddr")` should produce a function pointer;
- when neither debug extension is enabled, GIPA for each debug create function should return `NULL`.

The callback workflow now runs this probe against native Vulkan, baseline FEX, the report-only candidate, and the report+utils candidate.

The report-only candidate also keeps debug-utils as an untouched sibling control, so a generic harness change cannot masquerade as report-route causality.

## Alternatives still worth testing

### Deterministic fake Vulkan provider

Real llvmpipe is valuable integration evidence but cannot force every availability/scope combination. A tiny fake native provider can return sentinel function pointers for an exact object/name matrix and record which callback or allocator pointer reaches native code.

This remains the cleanest test for native-first substitution.

### Non-null allocation callbacks

The create probes use null allocators. A separate fixture should use guest allocation callbacks when testing `vkDestroyDebugReportCallbackEXT`; otherwise its routing omission remains only conditionally demonstrated.

### 32-bit runtime

The source inventory covers both ABIs, but hosted runtime coverage is currently x86-64. A 32-bit probe should be added after the 64-bit matrix is stable.

### Adjacent debug-utils destroy path

`vkDestroyDebugUtilsMessengerEXT` is not part of the exact declaration-versus-lookup mismatch, but it accepts allocation callbacks while the create side is custom. If non-null allocation callbacks enter scope, this deserves its own review.

### Repeated proc-address queries

A generated/native-first implementation should be exercised across repeated queries and multiple Vulkan objects so the returned guest-visible function pointer and FEX linking remain usable and consistent.

## Current execution state

At the time of this record, hosted run `31731074124` had checked out exact FEX `71afe476751deac24adabd1adb575fd2337b6e0a`, passed the source inventory gate, passed dependency setup, passed FEX CMake configuration, and entered the full FEX build.

No result from that still-running job is treated as product evidence. The retained Apple-M5/FEX-2608 A/B remains the runtime demonstration for `vkCreateDebugReportCallbackEXT` until the hosted matrix actually reaches the callback cases.

## Current conclusion

Cross-review strengthens the core Finding A diagnosis:

> FEX has a dynamic Vulkan custom-routing completeness defect. Three callback-related internal commands are declared `custom_host_impl` but omitted from the handwritten dynamic custom lookup. The retained Apple-M5 experiment demonstrates one consequence for `vkCreateDebugReportCallbackEXT`.

It also raises the acceptance bar. A candidate should demonstrate all of the following before it is treated as a strong production direction:

- direct and dynamic calls receive the same required FEX mediation;
- Vulkan `NULL` and command-scope decisions are preserved;
- report and utils siblings change independently as predicted;
- the test uses deterministic ABI selection;
- destroy/allocator claims have dedicated non-null-allocator evidence.

The preferred design remains native-first resolution plus generated or mechanically enforced custom-host substitution. The three-name manual table remains a useful experiment, not the strongest long-term owner.

## Reopen conditions

Reopen if a healthy direct baseline bypasses the custom implementation, if native-first substitution fails the proc-address matrix, if another callback-translation mechanism explains the debug-utils path, if an intentional dynamic-routing exception is found for an internal `custom_host_impl`, if 32-bit runtime points to a different owner, or if the relevant FEX source changes and the inventory no longer matches this record.
