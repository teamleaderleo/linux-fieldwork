# Native-gated Vulkan proc-address implementation notes

Target: FEX `ThunkLibs/libvulkan/Host.cpp` at `71afe476751deac24adabd1adb575fd2337b6e0a`.

These are review notes only.

## Registry

Add all three missing callback-family custom implementations to the existing custom substitution registry:

- `vkCreateDebugReportCallbackEXT`
- `vkDestroyDebugReportCallbackEXT`
- `vkCreateDebugUtilsMessengerEXT`

The report-only variant remains useful only as a causal experiment. The production candidate should contain the full three-entry family.

## Device proc-address path

Change the order so native `vkGetDeviceProcAddr` is queried first.

If native returns null, return null immediately.

If native returns a function pointer, consult the FEX custom substitution registry. Return the FEX custom function when present; otherwise return the native pointer.

This makes native Vulkan authoritative for device-command scope and availability. It also closes older behavior where the pre-native FEX list can return broader-scope names such as `vkCreateInstance` through GDPA.

## Instance proc-address path

Keep the existing instance setup step first.

Then query native `vkGetInstanceProcAddr` for the requested name. Return null immediately when native returns null.

When native returns a function pointer, consult the custom substitution registry. Return the FEX custom implementation when present; otherwise preserve the native pointer.

## X11/Xcb instance-extension initialization

The current custom GIPA branch has four special cases that issue a second native GIPA query to populate the corresponding FEX loader slot:

- `vkGetRandROutputDisplayEXT`
- `vkAcquireXlibDisplayEXT`
- `vkGetPhysicalDeviceXcbPresentationSupportKHR`
- `vkGetPhysicalDeviceXlibPresentationSupportKHR`

With native-first ordering, that second query is redundant. Reuse the native pointer already obtained for the requested name when the relevant loader slot is empty.

This preserves the existing minimal-instance then real-instance behavior while reducing duplicate loader calls.

The debug-report/debug-utils callback wrappers need no analogous preload step here; their custom implementations already obtain the relevant native instance function when called.

## Pure policy unit-test seam

A tiny Vulkan-local helper can express one rule: a custom pointer may substitute only when native lookup returned a non-null pointer.

APITests is the cleanest existing host-side Catch2 neighborhood. Keep the helper header-only so the test avoids linking the generated Vulkan host thunk and its loader dependencies.

Minimum synthetic function-pointer cases:

1. Native null, known custom name: result null.
2. Native null, ordinary name: result null.
3. Native non-null, known custom name: result custom pointer.
4. Native non-null, ordinary name: result native pointer.

Add representative names to make review intent obvious:

- GDPA policy with native null and `vkCreateInstance` must remain null.
- GIPA policy with native non-null and `vkCreateDebugReportCallbackEXT` must select the custom pointer.
- GIPA policy with native non-null and `vkCreateDebugUtilsMessengerEXT` must select the custom pointer.

## Companion tests

The pure policy test covers ordering, not registry completeness or callback ABI behavior. Keep three independent gates:

- source invariant: every public Vulkan `custom_host_impl` intended for dynamic lookup is registered;
- policy unit test: native availability gates substitution;
- end-to-end software-Vulkan callback probe: baseline and candidates separate at the actual guest/host callback boundary.

## Historical precision

Commit `c10402f4f9d589209b70b250cd94a1a98c55a7c7` moved the old inline GDPA custom list to a common helper and began applying it to GIPA. The callback-safe wrappers already existed in the parent but were absent from that device-oriented list.

The older GDPA list already included `vkCreateInstance`, so GDPA scope behavior predates the common-helper refactor. The GIPA callback omission is the regression associated with reusing the old list from GIPA.

No FEX upstream contact has occurred.
