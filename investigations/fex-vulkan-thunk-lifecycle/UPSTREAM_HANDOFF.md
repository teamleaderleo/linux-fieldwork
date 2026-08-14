# FEX Vulkan callback-routing handoff

## Status

Finding A now has:

- a deterministic hosted ARM64 reproduction on the exact product base;
- a clean two-commit source candidate in the owned FEX fork;
- an exact-head green callback/GIPA/GDPA runtime matrix;
- a separate green inventory test that catches the original custom-route drift.

Canonical detailed receipt:

```text
investigations/fex-vulkan-thunk-lifecycle/CLEAN_CALLBACK_ROUTING_CANDIDATE.md
```

No upstream FEX state was changed.

## Smallest bug statement

FEX already has custom host implementations for Vulkan callback-sensitive functions, but the manual dynamic custom-function routing table omitted:

- `vkCreateDebugReportCallbackEXT`
- `vkDestroyDebugReportCallbackEXT`
- `vkCreateDebugUtilsMessengerEXT`

Direct symbol lookup reaches the callback-safe custom wrapper. `vkGetInstanceProcAddr()` could instead expose/map the native host callback-creating entrypoint. With an x86 guest under FEX on hosted ARM64 Lavapipe, callback creation succeeds and exercising the GIPA debug-report callback path terminates host FEX with SIGILL / exit 132.

Historical intent is clear: `https://redirect.github.com/FEX-Emu/FEX/pull/1803` deliberately introduced the debug-report dummy callback workaround because generic guest-to-host callback delivery was unavailable. Finding A is a routing hole around that existing policy.

## Product base

```text
71afe476751deac24adabd1adb575fd2337b6e0a
```

This was current upstream FEX `main` when the reproduction was established.

## Baseline reproduction

```text
Actions run: 31736385632
job: 94568925322
artifact: 9195430863
artifact SHA-256: 96446e1a21f0acdcf9f4b25973116de48e7c78de0fa092500ad10ef63097f1ed
```

Observed:

```text
direct debug-report lookup: custom FEX dummy policy, guest callback suppressed
GIPA debug-report lookup: callback creation succeeds, fire -> host SIGILL / 132
```

## Clean owned-fork candidate

```text
repository: teamleaderleo/FEX
branch: fix/vulkan-callback-proc-routing
base: 71afe476751deac24adabd1adb575fd2337b6e0a
head: c011366706eaf65a00380003989b3a10811212b6
internal draft PR: teamleaderleo/FEX #1
```

Two source-only commits:

```text
28a3a5bfbd31662bfc4bd316ada39037aebf4165
ThunkLibs/vulkan: route callback custom implementations

c011366706eaf65a00380003989b3a10811212b6
ThunkLibs/vulkan: preserve native proc availability
```

Commit 1 repairs callback-route completeness.

Commit 2 makes native Vulkan authoritative for GIPA/GDPA availability before custom substitution and preserves guest GIPA/GDPA self-entrypoints only after native approval.

## Why commit 2 is separately required

Route-only run:

```text
Actions run: 31775244618
source: 28a3a5bfbd31662bfc4bd316ada39037aebf4165
artifact: 9209694610
artifact SHA-256: b7bbd396b14c00c4ac61f3bbabc14b0d64aa3cd94fd0aa0f216abe0ac8cf9720
```

Callback cases were safe:

```text
report-direct=0
report-gipa=0
utils-direct=0
utils-gipa=0
```

But custom-first lookup still manufactured non-null pointers for invalid NULL-instance queries:

```text
GIPA(NULL, "vkCreateDebugReportCallbackEXT") -> non-null
GIPA(NULL, "vkCreateShaderModule") -> non-null
```

## Candidate review caught and fixed a GDPA hole

A real-device semantic review of the first commit-2 version found:

```text
native: GDPA(device, "vkGetDeviceProcAddr") == direct GDPA
candidate-v1: GDPA(device, "vkGetDeviceProcAddr") == null
```

The other device/instance command decisions already matched native. Commit 2 was amended so guest GDPA returns its guest self-entrypoint after the packed host lookup approves the name.

Older `4f8130c...` candidate receipts are therefore superseded development evidence. Current head is `c011366...`.

## Final exact-head validation

```text
Actions run: 31776471366
job: 94692835765
exact source: c011366706eaf65a00380003989b3a10811212b6
CI workflow commit: 2edd7bbc9c8ac9174da5f5f3925cada722e03f6a
artifact: 9210141962
artifact SHA-256: 6e8265bd344c221e4c866130dbfc5835e4340dc139f1c2cc52b4b6d450368a38
retention: 30 days
runner: ubuntu-24.04-arm
```

Native ARM64 Lavapipe report/utils controls and a real-device GDPA control passed first.

Final x86/FEX matrix:

```text
report-direct=0
report-gipa=0
utils-direct=0
utils-gipa=0
null-report=0
null-shader=0
self-gipa=0
gdpa=0
```

GIPA semantics:

```text
GIPA(NULL, "vkCreateDebugReportCallbackEXT") -> null
GIPA(NULL, "vkCreateShaderModule") -> null
GIPA(instance, "vkGetInstanceProcAddr") == direct guest GIPA
GIPA(instance, "vkGetDeviceProcAddr") == direct guest GDPA
GIPA(NULL, "vkGetInstanceProcAddr") == direct guest GIPA
GIPA(NULL, "vkGetDeviceProcAddr") == null
```

Real-device GDPA semantics:

```text
GDPA(device, "vkDestroyDevice") -> non-null
GDPA(device, "vkAllocateMemory") -> non-null
GDPA(device, "vkCreateShaderModule") -> non-null
GDPA(device, "vkCreateInstance") -> null
GDPA(device, "vkCreateDebugReportCallbackEXT") -> null
GDPA(device, "vkGetDeviceProcAddr") == direct guest GDPA
```

This covers every proc-address behavior changed by the candidate.

## Hosted harness note

The initial hosted Vulkan-load SIGILL was separate from Finding A. A bare amd64 Ubuntu rootfs lacked guest X11 helper symbols expected by the Vulkan guest thunk constructor. FEX deliberately trapped while trying to create a trampoline for a null guest target.

Supplying inert x86-64 `XSync`, `XGetVisualInfo`, and `XDisplayString` symbols changed guest Vulkan `dlopen()` from exit 132 to exit 0. The final callback result uses that repaired headless fixture.

## Prevention follow-on

Separate stacked draft PR `teamleaderleo/FEX #2` adds a `.ThunkGen` inventory check so `custom_host_impl` metadata and `LookupCustomVulkanFunction()` cannot silently diverge.

Rebased validation:

```text
Actions run: 31776688975
artifact: 9210121093
artifact SHA-256: c944d8838858e8d6887c430058340f2eb7abc3f01458530aedc2925dc85f48b2
```

Old base is correctly rejected:

```text
x86_64: custom_host_impl=12 lookup=9
x86_32: custom_host_impl=21 lookup=18
missing in both: vkCreateDebugReportCallbackEXT, vkCreateDebugUtilsMessengerEXT, vkDestroyDebugReportCallbackEXT
```

Fixed inventory passes:

```text
x86_64: custom_host_impl=12 lookup=12
x86_32: custom_host_impl=21 lookup=21
missing: none
lookup-only: none
```

## Remaining human-only test

Hosted ARM64 now covers the software/emulation lane. The smallest hardware-specific confirmation is Apple M5 + Venus using exact candidate head:

```text
c011366706eaf65a00380003989b3a10811212b6
```

Run the same small x86 debug-report and debug-utils GIPA probe under the Venus ICD and record candidate SHA, Mesa/Venus identity, command, exit code, and driver/device strings. `vulkaninfo --summary` is a useful secondary integration check.
