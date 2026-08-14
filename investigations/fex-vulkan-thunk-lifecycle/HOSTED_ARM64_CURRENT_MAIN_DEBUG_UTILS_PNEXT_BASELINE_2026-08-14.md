# Hosted ARM64 current-main pristine debug-utils pNext escape — 2026-08-14

Status: demonstrated runtime finding on exact upstream-current product source observed during this investigation.

FEX product revision: `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`.
Owned-FEX carrier commit: `dcbc859ef433db44c1732711434fa32d7c36f463`.
Workflow run: `31770688438`.
Job: `94675816361`.
Artifact: `9208090394`, `agent-b-debug-utils-pnext-baseline-31770688438`.
Runner: GitHub hosted `ubuntu-24.04-arm`.
Driver: Lavapipe with the Vulkan validation layer.

The workflow verified that the carrier had no product-source delta under `ThunkLibs`, `FEXCore`, or `Source` relative to `f3ab82...` before building FEX.

## Probe contract

The probe places one `VkDebugUtilsMessengerCreateInfoEXT` in `VkInstanceCreateInfo::pNext` and supplies a guest callback with the retained x86/ARM64 instruction discriminator.

It enables `VK_EXT_debug_utils`, enables `VK_LAYER_KHRONOS_validation`, and also requests an intentionally missing instance extension. The loader therefore emits a synchronous debug-utils message while `vkCreateInstance` is in progress and then returns `VK_ERROR_EXTENSION_NOT_PRESENT`.

This is deliberately the embedded-instance pNext path, not the later explicit `vkCreateDebugUtilsMessengerEXT` command.

## Native ARM64 control

Observed:

```text
CALLBACK_PTR=<native-arm callback>
MARK create-enter
CALLBACK count=1 id=Loader Message
MARK create-return result=-7 callbacks=1 instance=(nil)
```

Exit:

```text
native=0
```

This proves that the pNext callback is active and synchronous for the exact input.

## Exact FEX current-main result

Observed:

```text
CALLBACK_PTR=<guest-x86 callback>
MARK create-enter
```

There is no guest callback-body marker and no `MARK create-return`.

The process terminates:

```text
fex=132
Illegal instruction
```

## Source match

At `f3ab82...`, `ThunkLibs/libvulkan/Host.cpp` handles legacy `VK_STRUCTURE_TYPE_DEBUG_REPORT_CALLBACK_CREATE_INFO_EXT` inside the custom `vkCreateInstance` implementation, but has no corresponding mediation for `VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT` in that pNext path.

The ordinary explicit `vkCreateDebugUtilsMessengerEXT` custom wrapper is not relevant here because the loader invokes the callback from the `vkCreateInstance` input chain before any explicit messenger-creation command is called.

The raw guest function pointer therefore reaches the native ARM64 Vulkan loader. The native loader attempts to invoke the x86 callback address as ARM64 code, matching the SIGILL boundary: `create-enter` is printed, but the guest callback body and `create-return` are never reached.

## Relationship to the earlier sanitizer experiment

An earlier diagnostic candidate added debug-utils nodes to FEX's destructive pNext-removal loop and showed that a one-node chain could be suppressed. A separate legal two-node test then proved that this destructive loop skips the newly exposed second debug-utils node and still SIGILLs.

This pristine current-main run closes the remaining evidence gap: the unmodified current source itself fails on the one-node debug-utils pNext path.

The combined evidence is now:

```text
pristine current main, one debug-utils pNext node   -> SIGILL 132
single-node destructive sanitizer                   -> can suppress one node
legal adjacent two-node debug-utils chain           -> destructive sanitizer still SIGILL 132
read-only caller root                               -> current destructive debug-report path SIGSEGV 139
```

That strongly favors a copied host-side pNext sanitization design over extending the existing caller-mutating loop.

## Independence from Finding A

This is not the dynamic proc-address routing defect:

- no dynamic callback-create PFN needs to be returned to the guest;
- the failure occurs inside `vkCreateInstance` while consuming input pNext data;
- adding `vkCreateDebugUtilsMessengerEXT` to `LookupCustomVulkanFunction()` does not repair this path.

It is also independent of `VkAllocationCallbacks`; the probe passes a NULL Vulkan allocator.

## Evidence boundary

Demonstrated here:

- exact `f3ab82...` product source;
- native synchronous debug-utils callback and normal `-7` return;
- pristine FEX SIGILL after `create-enter` and before callback body/create return.

Not demonstrated here:

- a production-ready copied-chain repair;
- every callback-bearing Vulkan pNext structure;
- callback delivery semantics if FEX eventually chooses to mediate rather than suppress these callbacks.

No upstream write or interaction was performed. All mutations and workflow execution remained in owned repositories/forks.
