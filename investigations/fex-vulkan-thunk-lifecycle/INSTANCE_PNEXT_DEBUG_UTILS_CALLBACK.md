# Vulkan creation-time debug-utils callback escape

## Status

**Confirmed current x86-64 FEX product defect** on exact base:

```text
c011366706eaf65a00380003989b3a10811212b6
```

A focused incremental candidate now closes the hosted crash for both the original debug-utils-only route and a consecutive debug-report -> debug-utils pNext chain while preserving FEX's existing callback-suppression policy.

The remaining correctness check for this lane is whether the existing handwritten pNext splice is visible as a mutation of the guest's const input chain after `vkCreateInstance` returns.

## Root cause in current source

FEX already treats guest Vulkan callbacks as unsafe and suppresses them in custom wrappers.

Current `ThunkLibs/libvulkan/Host.cpp` has:

- custom `vkCreateDebugReportCallbackEXT` and `vkCreateDebugUtilsMessengerEXT` wrappers that replace guest callbacks with FEX dummy callbacks;
- a custom `vkCreateInstance` wrapper that walks `VkInstanceCreateInfo::pNext` and removes `VK_STRUCTURE_TYPE_DEBUG_REPORT_CREATE_INFO_EXT` before calling native `vkCreateInstance`.

The base wrapper does **not** remove or sanitize `VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT`.

There is no member-level thunk-generator annotation for `VkDebugUtilsMessengerCreateInfoEXT::pfnUserCallback`, so this route has no generic callback translation underneath it. The raw x86 callback pointer reaches native host loader/layer code.

## Historical context

Upstream PR #1803 introduced the debug-report workaround before FEX had generic guest callback support. Its creation-time protection explicitly covered `VK_EXT_debug_report` by removing `VkDebugReportCallbackCreateInfoEXT` from the instance-create chain.

The current omission is consistent with that history: the older creation-time workaround never received equivalent debug-utils coverage. This is an extension of an existing intentional suppression policy, not a new generic-callback design.

## Exact hosted baseline receipt

```text
repository: teamleaderleo/FEX
exact FEX base: c011366706eaf65a00380003989b3a10811212b6
Actions run: 31790276400
job: 94735392825
artifact: 9215304255
artifact SHA-256: 1559da3f7e5a3339ca50b78c8815019734b622be7f55cec11b0a0f9c0ff99d87
runner: ubuntu-24.04-arm
runner image: 20260810.90.1
host Vulkan: Mesa Lavapipe
validation layers: 1.3.275.0-1
```

The same C probe source is compiled for native ARM64 and x86-64. The x86 binary runs through FEX against the same native Lavapipe ICD.

The probe enables `VK_LAYER_KHRONOS_validation` and `VK_EXT_debug_utils`, chains `VkDebugUtilsMessengerCreateInfoEXT` into `VkInstanceCreateInfo::pNext`, and deliberately sets reserved instance flag `0x80000000` to guarantee validation activity during `vkCreateInstance`.

### Native ARM64 positive control

The native callback fires repeatedly **before `vkCreateInstance` returns**:

```text
PNEXT_BEFORE_CREATE callback_count=0
PNEXT_CALLBACK count=1 ...
...
PNEXT_CALLBACK count=55 ... VUID-VkInstanceCreateInfo-flags-parameter ...
...
PNEXT_AFTER_CREATE result=0 instance=... callback_count=67
...
PNEXT_RETURN callback_count=69 count_after_create=67
native exit=0
```

This proves the callback-bearing pNext route is live on the exact hosted Vulkan stack.

### FEX baseline

The x86 guest reaches the unsafe boundary:

```text
PNEXT_PREFLIGHT validation_layer=1 debug_utils=1 callback=0x...
PNEXT_BEFORE_CREATE callback_count=0 ...
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

The guest callback body never executes. The host FEX process traps when native loader/layer code attempts to call the raw guest function address.

## Additional native mixed-chain control

Before testing the fix, a second native control proved that both temporary callback mechanisms are simultaneously live when chained consecutively:

```text
VkInstanceCreateInfo
  -> VkDebugReportCallbackCreateInfoEXT
  -> VkDebugUtilsMessengerCreateInfoEXT
```

Receipt:

```text
Actions run: 31790933579
job: 94737432050
artifact: 9215451304
artifact SHA-256: 21d762edf4e20206f15dd1176abc4d4d91fe4d64df27ff8d86322314c964ec4c
```

Native results:

```text
CHAIN_AFTER_CREATE mode=utils ... utils=67 report=0
CHAIN_RETURN mode=utils observed_at_create=67 expected=1

CHAIN_AFTER_CREATE mode=mixed ... utils=67 report=65
CHAIN_RETURN mode=mixed observed_at_create=132 expected=1
```

The first candidate workflow stopped before compilation because its source replacement was whitespace-sensitive. That is a harness-only failure; the native controls above remain valid.

## Candidate

The focused candidate changes only the handwritten `vkCreateInstance` pNext filter:

1. Treat both callback-bearing temporary instance-create nodes as unsafe:
   - `VK_STRUCTURE_TYPE_DEBUG_REPORT_CREATE_INFO_EXT`
   - `VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT`
2. After removing a callback-bearing node, re-check the same predecessor rather than advancing immediately. This prevents consecutive removable callback nodes from being skipped.

Conceptually:

```cpp
for (...; vk_struct->pNext;) {
  const auto next_type = vk_struct->pNext->sType;
  if (next_type == VK_STRUCTURE_TYPE_DEBUG_REPORT_CREATE_INFO_EXT ||
      next_type == VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT) {
    const_cast<VkBaseInStructure*>(vk_struct)->pNext = vk_struct->pNext->pNext;
    continue;
  }
  vk_struct = vk_struct->pNext;
}
```

No generic callback behavior is introduced. Guest callbacks remain suppressed, consistent with the existing explicit debug callback wrappers.

## Passing candidate receipt

Candidate v2 is fully green:

```text
workflow: .github/workflows/agent-c-instance-pnext-callback-candidate-v2.yml
workflow commit: 3df8e46c1de81dc3fbddeed0c4aa7a4fc973a139
base FEX: c011366706eaf65a00380003989b3a10811212b6
Actions run: 31791153300
job: 94738126272
artifact: 9215745861
artifact SHA-256: 62bf88eda859a8612bce0b86894809b681485224fd977baa37cb50836e78bc33
```

Debug-utils-only FEX result:

```text
CANDIDATE_PREFLIGHT mode=utils layer=1 utils=1 report=1
CANDIDATE_BEFORE_CREATE mode=utils utils=0 report=0
CANDIDATE_AFTER_CREATE mode=utils result=0 instance=... utils=0 report=0
CANDIDATE_AFTER_DESTROY mode=utils utils=0 report=0
CANDIDATE_RETURN mode=utils callbacks=0
```

Consecutive debug-report -> debug-utils FEX result:

```text
CANDIDATE_PREFLIGHT mode=mixed layer=1 utils=1 report=1
CANDIDATE_BEFORE_CREATE mode=mixed utils=0 report=0
CANDIDATE_AFTER_CREATE mode=mixed result=0 instance=... utils=0 report=0
CANDIDATE_AFTER_DESTROY mode=mixed utils=0 report=0
CANDIDATE_RETURN mode=mixed callbacks=0
```

Normalized candidate summary:

```text
utils=0
mixed=0
guest_callbacks=0
candidate_status=pass
```

Both processes exit 0. Neither guest callback body executes. This closes the hosted callback-safety crash and also demonstrates that the updated traversal removes consecutive callback-bearing nodes correctly.

## Bounded embedded-function-pointer audit

A corrected Vulkan-XML audit distinguishes regular Vulkan from Vulkan SC.

Receipt:

```text
workflow: .github/workflows/agent-c-vulkan-pfn-struct-audit-v2.yml
workflow commit: 28e188a250108ba30d5f4e422563da62d948e8c4
Actions run: 31791050730
job: 94737804414
artifact: 9215475414
artifact SHA-256: 21d94071c36d172855dfbca4752e066a96d9d89d9e1da489bc8bc702cff2b474
```

Regular Vulkan has exactly three extensible callback-bearing structure members in this registry:

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
```

`VkFaultCallbackInfo::pfnFaultCallback` is Vulkan SC-only and is not part of the regular-Vulkan callback audit.

None of the regular-Vulkan function-pointer members has member-level generator callback handling in the current interface file.

### Device-memory-report reachability

Hosted Lavapipe/Mesa 25.2.8 does not advertise `VK_EXT_device_memory_report`:

```text
Actions run: 31791298465
device_memory_report=0
deviceName = llvmpipe (LLVM 20.1.2, 128 bits)
driverName = llvmpipe
driverInfo = Mesa 25.2.8-0ubuntu0.24.04.2 (LLVM 20.1.2)
```

Therefore that remaining callback family is a bounded source-risk item, not a confirmed hosted runtime defect. Runtime proof requires a real driver that supports the extension; this investigation will not force a synthetic unsupported path.

## Current conclusion

The supported x86-64 creation-time debug-utils callback escape is reproduced and the focused suppression candidate closes it on hosted ARM64/Lavapipe.

The callback family audit is also bounded:

- debug-report instance pNext route: existing FEX workaround;
- debug-utils instance pNext route: newly reproduced and fixed by the candidate above;
- device-memory-report device pNext route: source risk, not reachable on hosted Lavapipe;
- Vulkan SC fault callback: outside the regular-Vulkan lane.

## Remaining correctness check

The existing and candidate `vkCreateInstance` filters splice a `const` input chain with `const_cast` before calling native Vulkan. Before packaging the candidate as a clean source patch, verify whether those writes are visible back in guest memory.

The next probe should preserve the original guest pointers and check after `vkCreateInstance` returns:

```text
VkInstanceCreateInfo::pNext unchanged
VkDebugReportCallbackCreateInfoEXT::pNext unchanged in mixed mode
```

If guest-visible chain pointers remain unchanged, document that the host wrapper is operating on a marshaled copy and no further change is required.

If the guest-visible input is mutated, create a follow-up candidate that restores every temporarily spliced pointer on all return paths while preserving the now-proven callback-safety behavior.
