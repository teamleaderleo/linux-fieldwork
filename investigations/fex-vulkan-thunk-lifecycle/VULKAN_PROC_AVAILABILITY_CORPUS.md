# Vulkan proc availability corpus differential

Status: complete for the non-beta Vulkan thunk surface on hosted ARM64/Lavapipe.

## Purpose

Finding A was caused by proc-address routing: direct lookup reached an existing FEX callback-suppression wrapper while `vkGetInstanceProcAddr` exposed the native host callback creator. The candidate source then added the missing callback-family custom routes and changed GIPA/GDPA to preserve native availability before substituting a custom implementation.

This corpus test checks that broader availability behavior across the entire Vulkan XML command-name inventory rather than a few hand-picked functions.

## Exact source under test

FEX:

`c011366706eaf65a00380003989b3a10811212b6`

This is two internal source commits on top of upstream/current baseline `71afe476751deac24adabd1adb575fd2337b6e0a`:

1. `28a3a5bf34c40e02810d57b39f439d6d400a5671` — `ThunkLibs/vulkan: route callback custom implementations`
2. `c011366706eaf65a00380003989b3a10811212b6` — `ThunkLibs/vulkan: preserve native proc availability`

The combined source delta is only `ThunkLibs/libvulkan/Host.cpp`.

Fieldwork probe/comparator revision:

`a206f8a904af29576f70ab9a5b873acea961bdfd`

Durable files:

- `vulkan_proc_availability_probe.c`
- `compare_vulkan_proc_availability.py`

## Probe behavior

The probe:

- loads `libvulkan.so.1`,
- creates a minimal instance at the maximum API version reported by the loader,
- enumerates the first physical device,
- creates a minimal device using the first queue family with a nonzero queue count,
- for every command name records only whether each lookup is null/non-null:
  - `dlsym(libvulkan, name)`
  - `vkGetInstanceProcAddr(VK_NULL_HANDLE, name)`
  - `vkGetInstanceProcAddr(instance, name)`
  - `vkGetDeviceProcAddr(device, name)`
- never calls the corpus commands themselves.

Native ARM64 and x86-64/FEX use the same hosted Lavapipe ICD.

## First XML corpus

The first mechanical XML inventory included every spelling exposed by regular Vulkan features/extensions, including provisional/beta extensions:

- command spellings: 773
- canonical commands: 668
- alias spellings: 105

Hosted differential run:

`31796981664`

Job:

`94756109413`

Workflow commit:

`7fa5592cb01a1fd0c4718f96361e8da758b9c795`

Artifact:

- ID `9217865350`
- ZIP SHA-256 `cf8bb94c0b5cb16a6dd48147a25f8101abf5e0d0306f50b9ae6232fd2df8261c`

Native and FEX metadata both showed successful minimal instance/device creation. The probe used Vulkan API version 1.3.275 (`4206867`) and one Lavapipe physical device / queue family 0.

Raw comparison:

```text
command_count=773
direct:        matches=307 fex_extra_nonnull=466 fex_missing_nonnull=0
gipa_null:     matches=773 fex_extra_nonnull=0   fex_missing_nonnull=0
gipa_instance: matches=760 fex_extra_nonnull=0   fex_missing_nonnull=13
gdpa_device:   matches=773 fex_extra_nonnull=0   fex_missing_nonnull=0
```

The 13 GIPA(instance) names were:

```text
vkCmdCudaLaunchKernelNV
vkCmdDispatchGraphAMDX
vkCmdDispatchGraphIndirectAMDX
vkCmdDispatchGraphIndirectCountAMDX
vkCmdInitializeGraphScratchMemoryAMDX
vkCreateCudaFunctionNV
vkCreateCudaModuleNV
vkCreateExecutionGraphPipelinesAMDX
vkDestroyCudaFunctionNV
vkDestroyCudaModuleNV
vkGetCudaModuleCacheNV
vkGetExecutionGraphPipelineNodeIndexAMDX
vkGetExecutionGraphPipelineScratchSizeAMDX
```

For each of those names the native row was:

```text
direct=0 gipa_null=0 gipa_instance=1 gdpa_device=0
```

and the FEX row was:

```text
direct=0 gipa_null=0 gipa_instance=0 gdpa_device=0
```

FEX stderr emitted exactly 13 messages of the form:

```text
vkGetInstanceProcAddr: Unknown Vulkan function at address ...: <name>
```

## Why the 13 names are not part of FEX's normal Vulkan thunk surface

All 13 commands belong to exactly two provisional/beta extension families:

- `VK_NV_cuda_kernel_launch`
- `VK_AMDX_shader_enqueue`

In the exact Vulkan-Headers revision used by FEX (`450bd2232225d6c7728a4108055ac2e37cef6475`), both families are declared in `vulkan_beta.h`.

`vulkan.h` includes `vulkan_beta.h` only under `VK_ENABLE_BETA_EXTENSIONS`.

FEX's `ThunkLibs/libvulkan/libvulkan_interface.cpp` includes `vulkan/vulkan.h` without defining `VK_ENABLE_BETA_EXTENSIONS`, so thunkgen intentionally has no signatures/invokers for those commands.

`Guest.cpp` implements this policy explicitly: proc lookup receives the native host pointer first, then `MakeGuestCallable()` searches the generated `HostPtrInvokers` signature map. If the name is unknown and `stub_unknown_functions` is false (the default), it returns `nullptr` instead of exposing an uncallable host pointer.

That is exactly what the 13 runtime messages show.

## Corrected non-beta inventory

A second mechanical XML pass excluded extension commands whose only provider is marked `provisional="true"`.

Inventory run:

`31797687995`

Workflow commit:

`fbcd9667e81623ef1b103ac4c2f99f24409df588`

Artifact:

- ID `9218008524`
- ZIP SHA-256 `48ffa81f21efde40d453264440b7a5488f9048b5f141c6fd328876a6e82a6b10`

Exact inventory:

```text
all_regular_spellings=773
nonbeta_spellings=760
beta_only_spellings=13
nonbeta_alias_spellings=105
nonbeta_canonical_commands=655
```

The mechanically identified 13 beta-only names are exactly the same 13 names in the GIPA(instance) mismatch set. There are no other beta-only names in this registry revision.

## Supported/non-beta result

Reinterpreting the already-collected native/FEX runtime rows over the corrected 760-name non-beta corpus gives:

```text
gipa_null:     760 / 760 exact
gipa_instance: 760 / 760 exact
gdpa_device:   760 / 760 exact
```

There are:

- zero FEX-extra non-null GIPA/GDPA results,
- zero FEX-missing non-null GIPA/GDPA results,
- zero remaining proc-availability mismatches in the non-beta corpus.

This is strong same-driver evidence that the native-first availability guard in `c0113667...` preserves host Vulkan proc availability across the complete FEX-supported/non-beta registry surface exercised here, while still allowing the callback-family custom substitution that fixed Finding A.

## Direct `dlsym` result is intentionally separate

The raw `dlsym` column has 466 names that are exported/non-null by the FEX guest thunk library while the native system loader DSO does not directly export them.

This does not indicate the GIPA/GDPA availability bug class: direct ELF export surface and Vulkan proc-address availability are different interfaces. The load-bearing result for this lane is the GIPA/GDPA null/non-null parity above.

No FEX direct-export name was missing relative to the native DSO in the 773-name table (`fex_missing_nonnull=0`).

## Conclusion

For this hosted Lavapipe environment, the broad native-first proc-availability part of the callback-routing candidate is now validated across the complete 760-name non-beta Vulkan command corpus available to FEX's current thunk header configuration.

The remaining Vulkan callback work is separate from proc availability:

- the validated `vkCreateInstance` pNext callback restoration is packaged on `fix/vulkan-instance-pnext-callback-restoration` at `27bf25d9fd2f918c577e302cda56bb733cdd04dd`;
- `VK_EXT_device_memory_report` still needs a driver that advertises it before its embedded callback route can be tested at runtime;
- current FEX callback policy remains suppression/dummy host callbacks rather than generic guest callback delivery.

A permanent regression should focus on small runtime probes for the callback routes and a narrow proc-availability null guard, not carry this full hosted corpus workflow into normal CI unless maintainers want registry-wide differential coverage.
