# Agent B Vulkan callback reduction

Carrier: Linux Fieldwork PR 669; Finding A review: issue 670.

## Artifacts

- `vk_debug_report_repro.c`: minimal `VK_EXT_debug_report` instance, dynamic create lookup, guest callback registration, and explicit `vkDebugReportMessageEXT` injection.
- `vk_debug_utils_repro.c`: analogous `VK_EXT_debug_utils` instance, dynamic messenger creation, guest callback registration, and explicit `vkSubmitDebugUtilsMessageEXT` injection.
- `NATIVE_SWIFTSHADER_RECEIPT.txt`: native x86 software-Vulkan execution receipt.
- `CALLBACK_ENTRY_RECEIPT.txt`: x86 debug-report callback entry-byte discriminator.
- `SOURCE_REVIEW_RECEIPT.md`: FEX-2608 and current-main adjacent source review.

Both programs keep `libvulkan.so.1` resident through process exit so this callback experiment remains separate from the guest-thunk unload finding.

## Build

```sh
cc -std=c11 -O2 -g -Wall -Wextra -Werror -o vk_debug_report_repro vk_debug_report_repro.c -ldl
cc -std=c11 -O2 -g -Wall -Wextra -Werror -o vk_debug_utils_repro vk_debug_utils_repro.c -ldl
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
