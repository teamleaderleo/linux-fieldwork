# Instance-create pNext chain integrity

## Status

The callback-suppression candidate from hosted run `31791153300` fixes the creation-time debug callback crash, but the handwritten pNext splice is **guest-visible** and therefore needs one more correction before the source candidate is considered complete.

This also exposes a pre-existing correctness issue in the older debug-report workaround, because the base `vkCreateInstance` implementation uses the same `const_cast` splice technique.

## Exact integrity receipt

```text
FEX base: c011366706eaf65a00380003989b3a10811212b6
Fieldwork candidate script: 1f58c1bc21c5dcf2cbc3697d6c3c1dd42e712a31
workflow: .github/workflows/agent-c-instance-pnext-chain-integrity.yml
workflow commit: 3613edfc67499ebdfef796cb1057aa7fd6823256
Actions run: 31791737796
job: 94739946051
artifact: 9215848077
artifact SHA-256: ff8d83aaac39b4431d170c474cd9d380b39848ea30093cdaf1383fe3e2ff7eab
runner: ubuntu-24.04-arm
runner image: 20260810.90.1
```

The workflow checked out the exact FEX base and exact Fieldwork apply script, applied the callback-suppression candidate successfully, built it, and ran a mixed guest chain:

```text
VkInstanceCreateInfo
  -> VkDebugReportCallbackCreateInfoEXT
  -> VkDebugUtilsMessengerCreateInfoEXT
```

The guest saved the original values of:

```text
VkInstanceCreateInfo::pNext
VkDebugReportCallbackCreateInfoEXT::pNext
VkDebugUtilsMessengerCreateInfoEXT::pNext
```

before calling `vkCreateInstance`.

## Result

Before create:

```text
INTEGRITY_BEFORE_CREATE ici=0x7fffffffd500 report=0x7fffffffd530 utils=(nil) callbacks=0/0
```

After create:

```text
INTEGRITY_AFTER_CREATE result=0 instance=0xfffd38778000 ici_same=0 report_same=1 utils_same=1 ici=(nil) report=0x7fffffffd530 utils=(nil) callbacks=0/0
```

After destroy:

```text
INTEGRITY_AFTER_DESTROY ici_same=0 report_same=1 utils_same=1 callbacks=0/0
```

Normalized receipt:

```text
fex_exit=40
guest_chain_unchanged=0
guest_callback_observed=0
```

`40` is the probe's deliberate integrity-failure exit code, not a FEX crash. The callback-safety portion is still successful: neither guest callback body executes, instance creation returns, and the host does not trap. The failure is specifically that `VkInstanceCreateInfo::pNext` has been changed from the guest's original pointer to `nullptr`.

## Interpretation

The custom 64-bit `vkCreateInstance` wrapper receives guest-visible structure memory for this argument path. Its `const_cast<VkBaseInStructure*>(vk_struct)->pNext = ...` writes are therefore observable by the guest after return.

That means the callback-suppression candidate from run `31791153300` is a valid crash fix but is **not yet the final source candidate**.

The older base implementation already removes `VK_STRUCTURE_TYPE_DEBUG_REPORT_CREATE_INFO_EXT` with the same technique, so the mutation issue predates the new debug-utils coverage. The new investigation merely made it explicit with a regression probe.

## Next candidate

Keep the proven safety behavior, but make every temporary splice reversible:

1. While filtering callback-bearing nodes, record each modified predecessor and its original `pNext` value.
2. Continue re-checking the same predecessor so consecutive debug-report/debug-utils nodes are all removed.
3. Call native `vkCreateInstance` with the filtered chain.
4. Restore all recorded predecessor pointers in reverse order immediately after the native call and before returning to the guest.

Reverse-order restoration is important when multiple consecutive nodes are removed from the same predecessor:

```text
root -> report -> utils -> next
```

The filter may modify `root->pNext` twice. Restoring in reverse reconstructs the original head correctly.

The next hosted test must require all of the following simultaneously:

```text
vkCreateInstance returns successfully
no guest debug-report callback executes
no guest debug-utils callback executes
VkInstanceCreateInfo::pNext unchanged after return
VkDebugReportCallbackCreateInfoEXT::pNext unchanged after return
VkDebugUtilsMessengerCreateInfoEXT::pNext unchanged after return
process exit 0
```

Do not package the existing apply script as final until this restoration candidate passes.