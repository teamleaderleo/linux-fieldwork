# Agent B Vulkan callback reduction

Carrier: Linux Fieldwork PR 669; Finding A review: issue 670.

## Artifacts

- `vk_debug_report_repro.c`: minimal `VK_EXT_debug_report` instance, dynamic create lookup, guest callback registration, and explicit `vkDebugReportMessageEXT` injection.
- `vk_debug_utils_repro.c`: analogous `VK_EXT_debug_utils` instance, dynamic messenger creation, guest callback registration, and explicit `vkSubmitDebugUtilsMessageEXT` injection.
- `vk_allocator_instance_probe.c`: `VkAllocationCallbacks` instance-lifetime probe for create/destroy allocator asymmetry.
- `ALLOCATOR_NATIVE_RECEIPT.md`: compact native SwiftShader allocator control results.
- `ALLOCATOR_PROBE_NOTES.md`: source rationale, evidence boundary, and target FEX discriminator for the allocator probe.
- `NATIVE_SWIFTSHADER_RECEIPT.txt`: native x86 software-Vulkan execution receipt.
- `CALLBACK_ENTRY_RECEIPT.txt`: x86 debug-report callback entry-byte discriminator.
- `SOURCE_REVIEW_RECEIPT.md`: FEX-2608 and current-main adjacent source review.

Both debug callback programs keep `libvulkan.so.1` resident through process exit so this callback experiment remains separate from the guest-thunk unload finding.

## Build

```sh
cc -std=c11 -O2 -g -Wall -Wextra -Werror -o vk_debug_report_repro vk_debug_report_repro.c -ldl
cc -std=c11 -O2 -g -Wall -Wextra -Werror -o vk_debug_utils_repro vk_debug_utils_repro.c -ldl
cc -std=c11 -O2 -g -Wall -Wextra -Werror -o vk_allocator_instance_probe vk_allocator_instance_probe.c -ldl
```

The committed sources compile as x86-64 ELF executables on the execution host.

## Debug-report expected outcomes

Pristine affected FEX-2608 dynamic route:

```text
MARK registered
MARK submit-enter
signal before callback/submit-return
```

The debug-report callback begins with an x86-only entry discriminator recorded in `CALLBACK_ENTRY_RECEIPT.txt`, making raw native ARM entry easy to identify.

A local lookup candidate selecting FEX's existing custom `vkCreateDebugReportCallbackEXT` implementation should be run with `--expect=suppressed`. Expected result:

```text
MARK registered
MARK submit-enter
MARK submit-return matched=0 bad_userdata=0
PASS debug_report matched=0
```

Negative controls:

- `--no-submit`: zero callback entries, exit 0.
- `--filter-miss`: zero callback entries, exit 0.
- `--create=export`: optional direct-export control; unavailable export returns 77.

## Debug-utils adjacent result

FEX-2608 already contains a custom `vkCreateDebugUtilsMessengerEXT` implementation that copies the create-info and replaces guest `pfnUserCallback` with `DummyVkDebugUtilsMessengerCallback` before calling native Vulkan.

`LookupCustomVulkanFunction()` omits `vkCreateDebugUtilsMessengerEXT`, matching the existing `vkCreateDebugReportCallbackEXT` omission. The same state is present on FEX `main` at `71afe476751deac24adabd1adb575fd2337b6e0a`, checked again on 2026-08-14.

Therefore debug-utils shares Finding A's source-level defect class: callback-aware custom handling exists, while dynamic custom lookup omits the callback-creating command.

Expected local debug-utils lookup candidate behavior with `--expect=suppressed`:

```text
MARK registered
MARK submit-enter
MARK submit-return matched=0
PASS debug_utils matched=0
```

Negative controls `--no-submit` and `--filter-miss` both require zero callback entries and exit 0.

## Native software-Vulkan control

Chromium SwiftShader at `/usr/lib/chromium/vk_swiftshader_icd.json` produced:

- debug-report matching submit: one callback, exit 0;
- debug-report no-submit: zero callbacks, exit 0;
- debug-report filter-miss: zero callbacks, exit 0;
- debug-report direct export: unavailable, exit 77;
- debug-utils matching submit: one callback, exit 0;
- debug-utils no-submit: zero callbacks, exit 0;
- debug-utils filter-miss: zero callbacks, exit 0.

## FEX software-Vulkan assumption

The retained ARM64 Fedora environment provides llvmpipe/lavapipe through `/usr/share/vulkan/icd.d/lvp_icd.aarch64.json`. Use that ICD while comparing pristine and local callback-routing host thunks.

## Evidence boundary

Executed here: compile plus native software-Vulkan positive and negative controls.

Source-read: FEX-2608 and current `main` debug-report/debug-utils custom implementations and dynamic lookup behavior.

Remaining target execution: run the reduced binaries under the retained ARM64 Fedora/FEX environment against pristine and local candidate host thunks. FEX upstream remained read-only throughout this work.

## 2026-08-14 `vkCreateInstance` pNext follow-up

Peer review found two adjacent behaviors in FEX's custom `vkCreateInstance` at FEX-2608 and reviewed current `main`.

First, debug-report create-info is removed from the application's supplied pNext chain by assigning through `const_cast`. A native SwiftShader integrity control preserves the input chain; the corresponding FEX probe should detect whether `VkInstanceCreateInfo.pNext` is changed after the call.

Second, the same `vkCreateInstance` handling covers debug-report create-info but has no corresponding debug-utils create-info handling. A native control with `VkDebugUtilsMessengerCreateInfoEXT` in `VkInstanceCreateInfo.pNext` plus an intentionally missing instance extension receives 27 debug-utils callbacks while `vkCreateInstance` returns `VK_ERROR_EXTENSION_NOT_PRESENT`. Removing only the pNext node produces the same return value with zero callbacks.

This debug-utils pNext route is independent of `vkGetInstanceProcAddr`; correcting only the dynamic custom-function lookup cannot cover it. The next decisive step is the same positive/negative pair under the existing owned ARM64/Lavapipe FEX lane.

## 2026-08-14 `VkAllocationCallbacks` lifetime follow-up

The allocator probe is a separate callback family that does not depend on proc-address lookup. A valid guest supplies the same non-null allocator object to `vkCreateInstance` and `vkDestroyInstance`; reviewed FEX source drops that allocator on the custom create path while destruction remains generic.

Native SwiftShader with the valid allocator pair observed 43 allocations, 1 reallocation, and 42 frees, then exited 0. The deliberately host-invalid mismatch simulation (`create` with no allocator, `destroy` with the callback object) entered destruction and terminated with status 139. That simulation is retained only as a control model, not as FEX runtime evidence.

The target proof is the normal guest-valid mode under the owned ARM64/FEX fixture. `ALLOCATOR_PROBE_NOTES.md` records the exact interpretation boundary and raw callback-entry discriminator.
