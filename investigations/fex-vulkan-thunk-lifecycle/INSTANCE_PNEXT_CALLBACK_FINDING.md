# Vulkan instance `pNext` callback finding

Status: hosted ARM64 reproduction and candidate validation complete.

## Exact source under test

- FEX: `c011366706eaf65a00380003989b3a10811212b6`
- This source already contains the proc-availability work from the earlier callback-routing lane.

## New bug

`vkCreateInstance` has a custom host wrapper that historically strips `VK_STRUCTURE_TYPE_DEBUG_REPORT_CREATE_INFO_EXT` from the incoming `VkInstanceCreateInfo::pNext` chain so the host Vulkan stack cannot call a guest debug-report callback during instance creation.

Two problems were demonstrated on current source:

1. `VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT` was not stripped. A native ARM64 validation-layer control proved the debug-utils callback is invoked during `vkCreateInstance`; the equivalent x86/FEX run crashed the host FEX process with SIGILL/exit 132 before `vkCreateInstance` returned.
2. The old strip logic mutates the marshaled input chain with `const_cast` and did not restore the changed predecessor link. A guest integrity probe observed `VkInstanceCreateInfo::pNext` changed after the call.

A consecutive `debug_report -> debug_utils` chain was included because the old loop could also advance past a just-removed node and miss another callback-bearing node immediately after it.

## Candidate policy

Keep FEX's existing callback-suppression policy; do not attempt generic host->guest Vulkan callbacks.

The candidate:

- treats both `VK_STRUCTURE_TYPE_DEBUG_REPORT_CREATE_INFO_EXT` and `VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT` as temporary callback-bearing nodes,
- re-checks the same predecessor after a splice so consecutive callback nodes are all removed,
- records every `(predecessor, original_pNext)` pair,
- calls native `vkCreateInstance`,
- restores the recorded links in reverse order before returning to the guest.

This preserves the existing suppression behavior while avoiding guest-visible mutation.

## Durable candidate files

- `apply_instance_pnext_callback_restoration.py`
- `instance_pnext_callback_integrity_probe.c`

The exact Fieldwork revision used by the final hosted run was:

`8aab7fb4412948b040e1886bb9aa252205ded9c7`

## Packaged internal FEX source branch

The exact validated Fieldwork script was applied to the exact tested base and committed as one `Host.cpp` change in the owned fork:

- branch: `fix/vulkan-instance-pnext-callback-restoration`
- base: `c011366706eaf65a00380003989b3a10811212b6`
- candidate commit: `27bf25d9fd2f918c577e302cda56bb733cdd04dd`
- commit subject: `ThunkLibs/vulkan: preserve instance pNext callback inputs`
- source diff: 22 insertions, 11 deletions, one file (`ThunkLibs/libvulkan/Host.cpp`)
- packaging workflow run: `31797245058`

The packaging workflow asserted both the base FEX SHA and Fieldwork SHA before applying the script, ran `git diff --check`, asserted exactly one modified file, then committed and pushed the resulting source branch.

## Final hosted receipt

Workflow run:

`31793197050`

Workflow commit:

`8e46167f1625879a3684775c7a6662f34db4521c`

Runner:

- `ubuntu-24.04-arm`
- image version `20260810.90.1`
- Lavapipe ICD `/usr/share/vulkan/icd.d/lvp_icd.json`

Exact runtime result:

```text
RESTORE_BEFORE_CREATE ici=0x7fffffffd4f0 report=0x7fffffffd520 utils=(nil)
RESTORE_AFTER_CREATE result=0 instance=0xfff9bd778000 ici_same=1 report_same=1 utils_same=1 callbacks=0/0
RESTORE_AFTER_DESTROY ici_same=1 report_same=1 utils_same=1 callbacks=0/0
RESTORE_RETURN unchanged=1 callbacks=0
```

Summary:

```text
fex_exit=0
guest_chain_unchanged=1
guest_callbacks=0
restoration_candidate=pass
```

Artifact:

- ID `9216433341`
- ZIP SHA-256 `9bd702f880965d2ad44c650aa583d1ad69c54c0fa61adc47584f9683e08d1a24`

## Callback-family audit boundary

The regular Vulkan registry in this source has only three extensible structs with embedded callback/function-pointer members relevant to this audit:

- `VkDebugReportCallbackCreateInfoEXT`
- `VkDebugUtilsMessengerCreateInfoEXT`
- `VkDeviceDeviceMemoryReportCreateInfoEXT`

`VkFaultCallbackInfo` is Vulkan SC-only and is not part of the regular Vulkan lane.

The hosted Lavapipe driver does not advertise `VK_EXT_device_memory_report`, so the device-memory-report callback route remains a source-risk item requiring another driver for runtime proof. It is not a hosted bug claim.

## Next lane

Run a complete proc-availability differential across the exact regular-Vulkan XML command corpus. The frozen corpus contains 773 command spellings: 668 canonical commands plus 105 exposed aliases. Compare native ARM64 and x86/FEX non-null/null results for the relevant proc lookup scopes before making any new routing claim.
