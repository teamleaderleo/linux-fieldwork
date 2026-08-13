# Vulkan proc-address history for Finding A

Exact current source reviewed: `71afe476751deac24adabd1adb575fd2337b6e0a`.

## Key historical commit

`c10402f4f9d589209b70b250cd94a1a98c55a7c7`  
Committed: 2023-12-04  
Title: `Thunks/vulkan: Move custom impl matching to common function`

The parent is `64276dbd0c3be786004f08dc2d40753f72d8e8b1`.

## Before the refactor

At the parent commit:

- `vkCreateDebugReportCallbackEXT` already had a custom host implementation that replaced the guest callback with `DummyVkDebugReportCallback`.
- `vkDestroyDebugReportCallbackEXT` already had a custom host implementation.
- `vkCreateDebugUtilsMessengerEXT` already had a custom host implementation that replaced the guest callback with `DummyVkDebugUtilsMessengerCallback`.
- `vkGetInstanceProcAddr` performed instance setup and then returned native `vkGetInstanceProcAddr` directly. It had no custom-function substitution step.
- `vkGetDeviceProcAddr` contained the handwritten custom-function list inline.
- That old GDPA list included `vkCreateInstance`, so the command-scope problem in GDPA predates the common-helper refactor.

Critically, the old GDPA list did not include the debug-report/debug-utils callback functions. That made sense for a list used only by the device-proc path, even though other entries in the list were already broader than strict device scope.

## What `c10402f` changed

The commit extracted the old GDPA custom list into `LookupCustomVulkanFunction()` and then called that helper from both GDPA and GIPA before native lookup.

No callback-family entries were added during the extraction.

Therefore the Finding A regression mechanism is concrete:

1. callback-safe custom implementations existed;
2. GIPA previously returned native loader addresses;
3. the refactor introduced custom substitution into GIPA by reusing the old device-oriented list;
4. the callback-safe implementations were absent from that reused list;
5. dynamic GIPA lookup of those callback commands therefore continued returning the native host-facing functions instead of FEX's callback-safe wrappers.

## Two distinct correctness questions

### Finding A: incomplete GIPA substitution

This is tied directly to the 2023 common-helper change. The reused list omitted three existing callback-family custom implementations.

### GDPA command-scope behavior

This is older. The pre-refactor GDPA list already returned custom functions such as `vkCreateInstance` before consulting native GDPA.

A native-first policy improves both behaviors, but the historical claims should remain separate:

- callback routing omission: regression exposed by the common-helper reuse;
- GDPA scope leak: pre-existing behavior preserved by that refactor.

## Patch-rationale consequence

The strongest focused production repair is still:

1. ask native GIPA/GDPA for the requested name first;
2. preserve native null;
3. when native returns a PFN, substitute FEX's custom implementation if the name has one;
4. otherwise return the native PFN;
5. add the three missing callback-family names to the substitution registry.

This restores dynamic callback routing while also making the older GDPA custom list obey native availability/scope.

No FEX upstream contact has occurred.
