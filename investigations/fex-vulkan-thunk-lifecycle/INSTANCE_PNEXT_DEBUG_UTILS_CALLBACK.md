# Vulkan creation-time debug-utils callback escape

## Status

**Confirmed current x86-64 FEX product defect** on exact candidate:

```text
c011366706eaf65a00380003989b3a10811212b6
```

This is the same broad callback-escape class as the earlier dynamic-proc Finding A, but it uses a different legal Vulkan route: `VkDebugUtilsMessengerCreateInfoEXT` chained into `VkInstanceCreateInfo::pNext` so the Vulkan loader/layers can invoke the guest callback **during `vkCreateInstance`**.

## Root cause in current source

FEX already treats guest Vulkan callbacks as unsafe and suppresses them in custom wrappers.

Current `ThunkLibs/libvulkan/Host.cpp` has:

- a custom `vkCreateDebugReportCallbackEXT` wrapper that substitutes `DummyVkDebugReportCallback`;
- a custom `vkCreateDebugUtilsMessengerEXT` wrapper that substitutes `DummyVkDebugUtilsMessengerCallback`;
- a custom `vkCreateInstance` wrapper that walks `VkInstanceCreateInfo::pNext` and removes `VK_STRUCTURE_TYPE_DEBUG_REPORT_CREATE_INFO_EXT` nodes before calling native `vkCreateInstance`.

The `vkCreateInstance` chain walk does **not** remove or sanitize `VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT`.

There is no member-level thunk-generator annotation for `VkDebugUtilsMessengerCreateInfoEXT::pfnUserCallback`, so this route has no generic callback translation underneath it. The raw x86 callback pointer reaches the host Vulkan loader/layer stack.

## Historical context

Upstream PR #1803 introduced the debug-report workaround before FEX had generic guest callback support. Its creation-time protection explicitly handled `VK_EXT_debug_report` by removing `VkDebugReportCallbackCreateInfoEXT` from the instance-create chain.

The current omission is consistent with that history: the original creation-time workaround predates equivalent debug-utils coverage. This is a narrow extension of an existing intentional suppression policy, not a request to design generic guest callbacks.

## Exact hosted baseline receipt

```text
repository: teamleaderleo/FEX
exact FEX: c011366706eaf65a00380003989b3a10811212b6
Actions run: 31790276400
job: 94735392825
artifact: 9215304255
artifact SHA-256: 1559da3f7e5a3339ca50b78c8815019734b622be7f55cec11b0a0f9c0ff99d87
runner: ubuntu-24.04-arm
runner image: 20260810.90.1
host Vulkan: Mesa Lavapipe
validation layers: 1.3.275.0-1
```

The same C probe source is compiled once for native ARM64 and once for x86-64. The x86 binary runs through FEX against the same native Lavapipe ICD.

## Probe

The probe requires:

```text
VK_LAYER_KHRONOS_validation
VK_EXT_debug_utils
```

It creates a `VkDebugUtilsMessengerCreateInfoEXT` with a guest callback and chains it into `VkInstanceCreateInfo::pNext`.

The messenger requests verbose/info/warning/error and general/validation/performance messages. The instance-create flags include reserved bit `0x80000000` to guarantee a validation message during `vkCreateInstance`.

The decisive phase boundary is:

```text
PNEXT_BEFORE_CREATE
  -> native vkCreateInstance
  -> creation-time debug callback(s)
PNEXT_AFTER_CREATE
```

## Native ARM64 positive control

Native preflight passes:

```text
PNEXT_PREFLIGHT validation_layer=1 debug_utils=1 ...
PNEXT_BEFORE_CREATE callback_count=0 ... flags=0x80000000
```

The callback then fires repeatedly **before `vkCreateInstance` returns**. Representative messages include loader diagnostics and the deliberately provoked validation error:

```text
PNEXT_CALLBACK count=1 ... id=Loader Message ...
...
PNEXT_CALLBACK count=55 severity=4096 types=2 id=VUID-VkInstanceCreateInfo-flags-parameter ...
...
PNEXT_AFTER_CREATE result=0 instance=... callback_count=67
```

Cleanup also invokes the temporary messenger callback before the instance is destroyed:

```text
PNEXT_BEFORE_DESTROY callback_count=67
PNEXT_CALLBACK count=68 ...
PNEXT_CALLBACK count=69 ...
PNEXT_AFTER_DESTROY callback_count=69
PNEXT_RETURN callback_count=69 count_after_create=67
native exit=0
```

This is a strong same-driver oracle proving the pNext callback route is live and is exercised during instance creation.

## FEX baseline result

The x86-64 guest reaches the exact unsafe boundary:

```text
PNEXT_PREFLIGHT validation_layer=1 debug_utils=1 callback=0x5564fb5b97d0
PNEXT_BEFORE_CREATE callback_count=0 pnext=0x7fffffffd560 callback=0x5564fb5b97d0 flags=0x80000000
```

It does **not** return from `vkCreateInstance`:

```text
Illegal instruction
timeout: the monitored command dumped core
```

Normalized result:

```text
native_exit=0
fex_exit=132
after_create=0
guest_callback_observed=0
sigill_like=1
sigsegv_like=0
```

The guest callback body never runs. The host FEX process traps when the host Vulkan stack attempts to call the raw guest function address.

## Root-cause statement

`VkDebugUtilsMessengerCreateInfoEXT` is a legal `VkInstanceCreateInfo` pNext node and can install a temporary debug messenger covering `vkCreateInstance`/`vkDestroyInstance` activity.

FEX suppresses the equivalent explicit debug-utils callback creator, but its custom `vkCreateInstance` safety filter only strips the older debug-report node. Therefore the debug-utils pNext route bypasses FEX's callback-suppression policy and exposes a guest callback pointer to native host code.

## Candidate fix

The policy-consistent minimal fix is to extend the existing `vkCreateInstance` callback-node filter to treat both callback-bearing instance-create nodes as unsafe:

```text
VK_STRUCTURE_TYPE_DEBUG_REPORT_CREATE_INFO_EXT
VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT
```

A robust implementation should also avoid the current iterator behavior that can skip one node when two removable callback nodes are consecutive. After removing a node, re-check the same predecessor instead of immediately advancing.

Expected candidate behavior under current FEX policy:

```text
native ARM64: callback_count > 0, exit 0
x86/FEX:      guest callback suppressed, vkCreateInstance returns, no host crash
```

The guest callback count being zero on FEX is expected and consistent with the existing explicit callback wrappers.

## Bounded embedded-function-pointer audit

A Vulkan-XML audit of extensible structures on the same header set found only four PFN-bearing structure members:

```text
VkDebugReportCallbackCreateInfoEXT::pfnCallback
  extends VkInstanceCreateInfo
  provider VK_EXT_debug_report

VkDebugUtilsMessengerCreateInfoEXT::pfnUserCallback
  extends VkInstanceCreateInfo
  provider VK_EXT_debug_utils

VkDeviceDeviceMemoryReportCreateInfoEXT::pfnUserCallback
  extends VkDeviceCreateInfo
  provider VK_EXT_device_memory_report

VkFaultCallbackInfo::pfnFaultCallback
  extends VkDeviceCreateInfo
```

Audit receipt:

```text
Actions run: 31790425419
job: 94735855349
artifact: 9215243875
artifact SHA-256: 11ce3c4672ce51c77bf738f3f6df1bcd8cfe165cf8180468fb5f7a603faef93a
```

None of these function-pointer members has member-level generator callback handling in the current interface file.

Do not infer that the two device-create structures are confirmed bugs. They are the remaining bounded callback-risk inventory and need extension/support/context checks before runtime claims.

## Next steps

1. Apply only the instance-create debug-utils suppression candidate to `c0113667...`.
2. Rerun this exact native/FEX probe, treating FEX callback count 0 as expected success if `vkCreateInstance` returns safely.
3. Add a mixed consecutive chain regression (`debug_report` + `debug_utils`) so the filter cannot skip one callback node.
4. Only after this closes, inspect the two PFN-bearing device-create structures for current driver support and reachability.
