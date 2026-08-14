# FEX Vulkan callback-routing handoff

## Status

Finding A now has a deterministic hosted ARM64 reproduction, a clean two-commit candidate in the owned FEX fork, and an exact-head green runtime matrix.

Canonical detailed receipt:

```text
investigations/fex-vulkan-thunk-lifecycle/CLEAN_CALLBACK_ROUTING_CANDIDATE.md
```

Longer hosted debugging history:

```text
investigations/fex-vulkan-thunk-lifecycle/HOSTED_ARM64_VULKAN_LOAD_TRACE.md
```

No upstream FEX state was changed.

## Smallest bug statement

FEX already has custom host implementations for Vulkan callback-sensitive functions, but the manual dynamic custom-function routing table omitted three of them:

- `vkCreateDebugReportCallbackEXT`
- `vkDestroyDebugReportCallbackEXT`
- `vkCreateDebugUtilsMessengerEXT`

Direct symbol lookup reaches the custom wrapper. `vkGetInstanceProcAddr()` could instead expose/map the native host callback-creating entrypoint. With an x86 guest under FEX on hosted ARM64 Lavapipe, callback creation succeeds and exercising the GIPA debug-report callback path terminates the host FEX process with SIGILL / exit 132.

Historical intent is clear: `https://redirect.github.com/FEX-Emu/FEX/pull/1803` deliberately introduced the debug-report dummy callback workaround because generic guest-to-host callback delivery was unavailable. Finding A is a routing hole around that existing policy.

## Product base

```text
71afe476751deac24adabd1adb575fd2337b6e0a
```

That was current upstream FEX `main` when the reproduction was established.

The owned fork's `main` subsequently advanced seven fork-local authority/documentation commits, touching only `AGENTS.md`, `CONTRIBUTING.md`, and `CONTRIBUTORS.md`. The clean candidate branch remains based on the exact product source above so its execution receipts stay exact.

## Baseline reproduction

```text
Actions run: 31736385632
job: 94568925322
artifact: 9195430863
artifact SHA-256: 96446e1a21f0acdcf9f4b25973116de48e7c78de0fa092500ad10ef63097f1ed
```

Observed:

```text
direct debug-report lookup: callback creation succeeds; guest callback suppressed by FEX dummy policy
GIPA debug-report lookup: callback creation succeeds; firing terminates host FEX with SIGILL / 132
```

Native ARM64 Lavapipe callback control passed first.

## Clean owned-fork candidate

```text
repository: teamleaderleo/FEX
branch: fix/vulkan-callback-proc-routing
base: 71afe476751deac24adabd1adb575fd2337b6e0a
head: 4f8130c298433a7a9165392d33fc0a3e6be3202b
internal draft PR: teamleaderleo/FEX pull request 1
```

Two source-only commits:

```text
28a3a5bfbd31662bfc4bd316ada39037aebf4165
ThunkLibs/vulkan: route callback custom implementations

4f8130c298433a7a9165392d33fc0a3e6be3202b
ThunkLibs/vulkan: preserve native proc availability
```

Commit 1 adds only the three missing callback-family custom routes.

Commit 2 keeps native Vulkan authoritative for proc availability before custom substitution. It also preserves guest GIPA/GDPA self-entrypoint behavior after the host lookup succeeds.

The split is intentional: commit 1 fixes callback safety, while commit 2 fixes a separately demonstrated proc-address semantics defect.

## Why commit 2 is independently required

Route-only run:

```text
Actions run: 31775244618
job: 94689229815
source: 28a3a5bfbd31662bfc4bd316ada39037aebf4165
artifact: 9209694610
artifact SHA-256: b7bbd396b14c00c4ac61f3bbabc14b0d64aa3cd94fd0aa0f216abe0ac8cf9720
```

The four callback cases were safe:

```text
report-direct=0
report-gipa=0
utils-direct=0
utils-gipa=0
```

But custom-first lookup still produced non-null pointers for invalid NULL-instance queries:

```text
GIPA(NULL, "vkCreateDebugReportCallbackEXT") -> non-null
GIPA(NULL, "vkCreateShaderModule") -> non-null
```

So native-first availability gating is not incidental cleanup.

## Final exact-head validation

```text
Actions run: 31775612827
job: 94690326823
exact source: 4f8130c298433a7a9165392d33fc0a3e6be3202b
CI workflow commit: 2519c13a1188548bb0ebabc0d48ec9d90bd2c580
artifact: 9209835985
artifact SHA-256: aca28b0387565742a372101bfd5bad399e03335898a2bceb641042acb05d208d
artifact retention: 30 days
runner: ubuntu-24.04-arm
```

Native ARM64 Lavapipe report/utils controls passed first.

Final x86/FEX matrix:

```text
report-direct=0
report-gipa=0
utils-direct=0
utils-gipa=0
null-report=0
null-shader=0
self-gipa=0
```

Negative proc-address checks:

```text
GIPA(NULL, "vkCreateDebugReportCallbackEXT") -> null
GIPA(NULL, "vkCreateShaderModule") -> null
```

Self-query control created a real instance and confirmed:

```text
GIPA(instance, "vkGetInstanceProcAddr") == direct guest GIPA
GIPA(instance, "vkGetDeviceProcAddr") == direct guest GDPA
returned GIPA can query vkDestroyInstance
GIPA(NULL, "vkGetInstanceProcAddr") == direct guest GIPA
GIPA(NULL, "vkGetDeviceProcAddr") == null
```

This is the current strongest candidate/evidence pair.

## Hosted harness note

The initial hosted Vulkan-load SIGILL was separate from Finding A. A bare amd64 Ubuntu rootfs lacked guest `libX11.so.6`; the Vulkan guest thunk constructor expects `XSync`, `XGetVisualInfo`, and `XDisplayString`, then FEX deliberately trapped while trying to build a host trampoline for a null guest target.

Adding inert x86-64 helper symbols changed guest Vulkan `dlopen()` from exit 132 to exit 0. The final callback result uses that repaired headless fixture.

## Regression-test direction

`unittests/ThunkFunctionalTests` is the closest current runtime suite, but it presently drives installed programs such as `vulkaninfo` rather than custom guest test binaries. A precise regression should exercise direct/GIPA callback creation and native-null proc semantics under Vulkan thunks.

Separately, the source audit found a maintenance problem: `custom_host_impl` metadata and the manual custom routing inventory are two independent sources of truth. A generator-derived or inventory-invariant test should be follow-on prevention work rather than part of this two-commit runtime candidate.

## Remaining human-only test

Hosted ARM64 now covers the software/emulation lane. The smallest hardware-specific confirmation is Apple M5 + Venus using exact candidate head:

```text
4f8130c298433a7a9165392d33fc0a3e6be3202b
```

Run the same small x86 debug-report and debug-utils GIPA probe under the Venus ICD and record candidate SHA, Mesa/Venus identity, command, exit code, and driver/device strings. `vulkaninfo --summary` is a useful secondary integration check.
