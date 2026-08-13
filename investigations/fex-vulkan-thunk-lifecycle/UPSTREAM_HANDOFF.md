# FEX Vulkan callback-routing handoff

## Scope

This note is the compact upstream-facing handoff for the hosted ARM64 investigation documented in `HOSTED_ARM64_VULKAN_LOAD_TRACE.md`.

The source under test was:

```text
71afe476751deac24adabd1adb575fd2337b6e0a
```

At the end of the investigation, that SHA was also the current `FEX-Emu/FEX` `main` commit. The reproduction and candidate therefore apply to current upstream main at the time of this note.

## Symptom

With an amd64 guest under FEX on an ARM64 host, `VK_EXT_debug_report` behaves differently depending on how `vkCreateDebugReportCallbackEXT` is obtained.

On current main with the repaired guest runtime:

```text
direct dlsym: exit 20, callback_count=0
vkGetInstanceProcAddr: exit 132 / host SIGILL while firing the debug message
```

The direct route is the expected legacy FEX policy: callback creation succeeds, FEX substitutes a host dummy callback, and the guest callback is suppressed.

The GIPA route bypasses that callback-safe custom implementation. It returns/maps the native host `vkCreateDebugReportCallbackEXT`, allowing an unsafe guest callback pointer to reach native Vulkan. Callback creation succeeds; exercising the callback path terminates the FEX host process.

## Historical intent

Upstream PR #1803, `ThunkLibs/vulkan: Work around lack of generic callback support in VK_EXT_debug_report`, deliberately introduced the custom `vkCreateDebugReportCallbackEXT` implementation that replaces the guest callback with a host dummy callback. The PR explicitly describes ignoring callbacks as the workaround and was tested on ARM/Lavapipe.

The current bug is therefore a proc-address routing hole around an existing workaround.

## Root cause in current code

`fexfn_impl_libvulkan_vkGetInstanceProcAddr()` calls `LookupCustomVulkanFunction()` first and returns a custom implementation when that lookup succeeds.

At the tested/current main SHA, `LookupCustomVulkanFunction()` contains many custom Vulkan routes but omits the debug callback creation family, including `vkCreateDebugReportCallbackEXT` and `vkCreateDebugUtilsMessengerEXT`.

That omission lets GIPA expose the native callback-creating entrypoint through the generic host-function-pointer mapping path.

## Candidate

Fieldwork commit:

```text
1b268a6742768086aa8355e997c10b4423319ba6
```

contains:

```text
apply_native_first_callback_candidate.py
```

The candidate makes two related changes:

1. Route callback-sensitive entrypoints through `LookupCustomVulkanFunction()`:
   - `vkCreateDebugReportCallbackEXT`
   - `vkDestroyDebugReportCallbackEXT`
   - `vkCreateDebugUtilsMessengerEXT`
2. For GIPA/GDPA custom substitutions, ask native Vulkan for the proc first and preserve a native `nullptr` result before returning a FEX custom implementation.

The first change closes the demonstrated crash. The second preserves Vulkan proc-address availability semantics for extension commands.

## Validation

### Baseline reproduction

```text
Actions run: 31736385632
job: 94568925322
CI commit: 8ded2659370d3568ef89427e5a1ced3876ede2d9
artifact: 9195430863
artifact SHA-256: 96446e1a21f0acdcf9f4b25973116de48e7c78de0fa092500ad10ef63097f1ed
```

Result:

```text
direct=20
gipa=132
```

Native ARM64 Lavapipe callback control succeeded.

### Focused candidate confirmation

```text
Actions run: 31739829897
job: 94580235422
CI commit: 51da719d001d09f7fd4dd54e6a23f2a7b3e86103
artifact: 9196735724
artifact SHA-256: dfadddc83314ad0e089922879de29008c32970ffae2695872657396d24b0f1e1
```

Result:

```text
report-direct=0
report-gipa=0
```

Both paths match FEX's existing callback-suppression policy (`callback_count=0`) and complete cleanly.

### Callback-family confirmation

```text
Actions run: 31740540778
job: 94582568559
CI commit: a5604fe3daf8ba1df7dcb75d1ee09cf405174900
source: 71afe476751deac24adabd1adb575fd2337b6e0a
candidate source: 1b268a6742768086aa8355e997c10b4423319ba6
artifact: 9197014064
artifact SHA-256: 3fcd6152df052be28a8ba2f02e663cca140d5e6971b6fb1ee455acf82e3531c3
```

Native ARM64 controls for both debug-report and debug-utils succeeded first.

Candidate matrix:

```text
report-direct=0
report-gipa=0
utils-direct=0
utils-gipa=0
```

Representative debug-report GIPA result:

```text
CREATE_INSTANCE kind=report lookup=gipa result=0
CREATE_CALLBACK result=0
AFTER_FIRE callback_count=0 expected=0
PROBE_FINISH callback_count=0 status=0
```

Representative debug-utils GIPA result:

```text
CREATE_INSTANCE kind=utils lookup=gipa result=0
CREATE_MESSENGER result=0
AFTER_FIRE callback_count=0 expected=0
PROBE_FINISH callback_count=0 status=0
```

The candidate therefore covers both callback-creation families exercised by the probe while preserving the existing FEX suppression behavior.

## Harness note: the earlier Vulkan-load SIGILL

The first hosted runs died during guest `dlopen("libvulkan.so.1")` before reaching the callback test. That was a minimal-rootfs error: the Vulkan guest constructor expects guest `libX11.so.6` symbols `XSync`, `XGetVisualInfo`, and `XDisplayString`. The bare rootfs supplied none, producing null guest targets and an intentional FEX assertion trap on the host.

Adding diagnostic non-null x86 X11 symbols changed the Vulkan guest load from exit `132` to exit `0`. That SIGILL belongs to the test harness and is separate from the callback-routing crash above.

## Test placement

`unittests/ThunkFunctionalTests` is the closest existing runtime suite. It currently drives installed programs such as `vulkaninfo` and contains no custom guest test source of its own. A precise regression for this bug therefore needs either:

- a small guest callback-routing probe added to that functional-test machinery; or
- another maintainers-preferred runtime test seam that can execute the same direct/GIPA callback creation cases under Vulkan thunks.

The end-to-end hosted receipts above already give a deterministic ARM64 reproduction and candidate A/B.

## Remaining patch decision

Before upstream submission, decide how broad to make the native-availability guard. The demonstrated crash fix is the missing callback-family custom routing. The native-first lookup also protects extension availability semantics and passed the focused report/utils tests, while a dedicated negative test for an unavailable extension proc would make that portion of the patch independently demonstrated.

Real guest debug callback delivery is a separate behavior change. This handoff keeps the current FEX policy: debug callbacks are suppressed safely instead of crossing the guest/host callback boundary.
