# Clean FEX Vulkan callback-routing candidate

## Purpose

This note is the canonical receipt for the clean owned-fork candidate produced after the hosted ARM64 Finding A investigation. It separates the product fix from disposable CI machinery and from the broader generator/invariant follow-up.

No upstream FEX state was changed. The source branch and draft PR below exist only in `teamleaderleo/FEX`.

## Product base

The product source used for the baseline and candidate work is:

```text
71afe476751deac24adabd1adb575fd2337b6e0a
```

That was current upstream FEX `main` when the Finding A reproduction was established.

The owned fork's `main` later advanced seven commits above that product revision, but those fork-local commits modify only repository authority/policy documentation (`AGENTS.md`, `CONTRIBUTING.md`, and `CONTRIBUTORS.md`). The candidate branch intentionally remains based on the exact product revision so its validation receipts stay exact.

## Clean source branch

```text
repository: teamleaderleo/FEX
branch: fix/vulkan-callback-proc-routing
base product SHA: 71afe476751deac24adabd1adb575fd2337b6e0a
final candidate SHA: 4f8130c298433a7a9165392d33fc0a3e6be3202b
```

The branch contains two source-only commits.

### Commit 1 — callback route completeness

```text
28a3a5bfbd31662bfc4bd316ada39037aebf4165
ThunkLibs/vulkan: route callback custom implementations
```

This commit adds only the three missing `LookupCustomVulkanFunction()` routes:

- `vkCreateDebugReportCallbackEXT`
- `vkDestroyDebugReportCallbackEXT`
- `vkCreateDebugUtilsMessengerEXT`

These functions were already declared/implemented as custom host endpoints; the manual dynamic custom lookup table had drifted from that metadata.

The commit fixes the demonstrated callback crash without changing FEX's existing callback policy: debug callbacks remain suppressed through the existing native dummy callback path.

### Commit 2 — native proc availability semantics

```text
4f8130c298433a7a9165392d33fc0a3e6be3202b
ThunkLibs/vulkan: preserve native proc availability
```

This commit keeps native Vulkan authoritative for proc availability before FEX substitutes a custom implementation:

- host GIPA/GDPA query the native loader first;
- a native null result remains null;
- custom FEX routing is selected only after native availability succeeds;
- the successful native lookup is reused to populate instance-extension loader slots;
- guest `vkGetInstanceProcAddr` performs the packed host lookup first, then returns the guest GIPA/GDPA entrypoints for those two self-referential names only when the host lookup says they are valid.

Commit 2 is independently motivated. Commit 1 alone fixes callback safety but can manufacture a non-null custom function pointer in a scope where native Vulkan returns null.

## Baseline Finding A reproduction

Hosted ARM64 repaired-rootfs baseline:

```text
Actions run: 31736385632
job: 94568925322
source: 71afe476751deac24adabd1adb575fd2337b6e0a
artifact: 9195430863
artifact SHA-256: 96446e1a21f0acdcf9f4b25973116de48e7c78de0fa092500ad10ef63097f1ed
```

Observed debug-report split:

```text
direct lookup: callback creation succeeds; FEX dummy callback suppresses guest callback
gipa lookup: callback creation succeeds; firing the message terminates host FEX with SIGILL / exit 132
```

This demonstrates that GIPA bypassed the existing callback-safe custom host implementation.

Historical context: `https://redirect.github.com/FEX-Emu/FEX/pull/1803` deliberately introduced the debug-report dummy callback workaround because generic guest-to-host callbacks were unavailable. The current defect is a routing hole around that established behavior.

## Commit 1 route-only receipt

```text
Actions run: 31775244618
job: 94689229815
source: 28a3a5bfbd31662bfc4bd316ada39037aebf4165
artifact: 9209694610
artifact SHA-256: b7bbd396b14c00c4ac61f3bbabc14b0d64aa3cd94fd0aa0f216abe0ac8cf9720
```

Callback matrix:

```text
report-direct=0
report-gipa=0
utils-direct=0
utils-gipa=0
```

Both callback families are safe and match the existing FEX suppression policy.

The same run deliberately tested the remaining custom-first proc semantics and confirmed both were still non-null:

```text
GIPA(NULL, "vkCreateDebugReportCallbackEXT") -> non-null
GIPA(NULL, "vkCreateShaderModule") -> non-null
```

The test expected those non-null values for this route-only receipt, so the workflow exited green while preserving evidence that commit 2 has separate work to do.

## Final exact-head receipt

```text
Actions run: 31775612827
job: 94690326823
CI workflow commit: 2519c13a1188548bb0ebabc0d48ec9d90bd2c580
exact candidate source: 4f8130c298433a7a9165392d33fc0a3e6be3202b
artifact: 9209835985
artifact SHA-256: aca28b0387565742a372101bfd5bad399e03335898a2bceb641042acb05d208d
artifact retention: 30 days
runner: ubuntu-24.04-arm
```

Native ARM64 Lavapipe debug-report and debug-utils callback controls both passed before FEX execution.

Final hosted x86/FEX matrix:

```text
report-direct=0
report-gipa=0
utils-direct=0
utils-gipa=0
null-report=0
null-shader=0
self-gipa=0
```

The two negative proc tests confirm native null availability is preserved:

```text
GIPA(NULL, "vkCreateDebugReportCallbackEXT") -> (nil)
GIPA(NULL, "vkCreateShaderModule") -> (nil)
```

The self-query control created a real Vulkan instance and observed:

```text
GIPA(instance, "vkGetInstanceProcAddr") == direct guest vkGetInstanceProcAddr
GIPA(instance, "vkGetDeviceProcAddr") == direct guest vkGetDeviceProcAddr
returned GIPA can query vkDestroyInstance successfully
GIPA(NULL, "vkGetInstanceProcAddr") == direct guest vkGetInstanceProcAddr
GIPA(NULL, "vkGetDeviceProcAddr") == null
```

Representative receipt:

```text
SELF_RESULT instance_gipa=<direct guest GIPA>
            instance_gdpa=<direct guest GDPA>
            destroy=<non-null linked proc>
            null_gipa=<direct guest GIPA>
            null_gdpa=(nil)
```

This closes the runtime questions introduced by splitting the exploratory patch into two commits.

## Disposable hosted environment

The successful hosted recipe uses:

```text
runner: ubuntu-24.04-arm
host compiler: clang-18 / lld-18
focused host targets: FEXServer vulkan-host-64
focused guest target: vulkan-guest
host Vulkan: Mesa Lavapipe
runtime rootfs: docker pull/export ubuntu:24.04 for linux/amd64
```

The bare amd64 rootfs needs guest X11 helper symbols during the Vulkan guest thunk constructor. The headless probe supplies inert x86-64 `XSync`, `XGetVisualInfo`, and `XDisplayString` symbols. This repaired an earlier pre-probe harness SIGILL caused by FEX deliberately trapping on null guest trampoline targets.

That X11 fixture is test machinery only and is separate from the callback-routing product result.

## Internal review surface

Owned-fork draft PR:

```text
teamleaderleo/FEX pull request 1
base: fork main
head: fix/vulkan-callback-proc-routing
state: draft
```

The fork `main` policy/documentation commits are ahead of the exact product base; the PR remains a review surface rather than a claim that the exact tested branch has been rebased.

## Long-term prevention

The immediate candidate should stay small. The investigation's source audit shows a two-source-of-truth problem: `custom_host_impl` metadata and the manual `LookupCustomVulkanFunction()` inventory can drift independently.

A separate follow-on should make that invariant executable, ideally by deriving or checking the dynamic custom-route inventory from generator metadata. That prevention work should not be folded into the two runtime commits above.

## Remaining human-only test

Hosted ARM64 now covers the software/emulation lane. The smallest hardware-specific confirmation is Apple M5 + Venus using the exact clean candidate head:

```text
4f8130c298433a7a9165392d33fc0a3e6be3202b
```

Run the same small x86 callback probe through GIPA for debug-report and debug-utils under the Venus ICD. Capture source SHA, Mesa/Venus identity, command, exit status, and driver/device strings. A `vulkaninfo --summary` pass is useful as an integration check but is secondary to the small deterministic callback probe.
