# Clean FEX Vulkan callback-routing candidate

## Purpose

This note is the canonical receipt for the clean owned-fork candidate produced after the hosted ARM64 Finding A investigation. It separates the product fix from disposable CI machinery and from the broader custom-route inventory prevention follow-up.

No upstream FEX state was changed. The source branches and draft PRs below exist only in `teamleaderleo/FEX`.

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
final candidate SHA: c011366706eaf65a00380003989b3a10811212b6
internal draft PR: teamleaderleo/FEX #1
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
c011366706eaf65a00380003989b3a10811212b6
ThunkLibs/vulkan: preserve native proc availability
```

This commit keeps native Vulkan authoritative for proc availability before FEX substitutes a custom implementation:

- host GIPA/GDPA query the native loader first;
- a native null result remains null;
- custom FEX routing is selected only after native availability succeeds;
- the successful native lookup is reused to populate instance-extension loader slots;
- guest `vkGetInstanceProcAddr` performs the packed host lookup first, then returns the guest GIPA/GDPA entrypoints for those two self-referential names only when the host lookup says they are valid;
- guest `vkGetDeviceProcAddr` likewise performs the packed host lookup first, then returns the guest GDPA self-entrypoint when native Vulkan approves `vkGetDeviceProcAddr` for a real device.

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

## Candidate-review correction: GDPA self-query

An earlier version of commit 2 passed the callback/GIPA matrix but had not directly tested `vkGetDeviceProcAddr` as a device-level self-query.

A separate real-device Lavapipe probe exposed a candidate bug:

```text
native: GDPA(device, "vkGetDeviceProcAddr") == direct GDPA
candidate-v1: GDPA(device, "vkGetDeviceProcAddr") == null
```

Other device-vs-instance availability already matched native in that probe:

```text
GDPA(device, "vkDestroyDevice") -> non-null
GDPA(device, "vkAllocateMemory") -> non-null
GDPA(device, "vkCreateShaderModule") -> non-null
GDPA(device, "vkCreateInstance") -> null
GDPA(device, "vkCreateDebugReportCallbackEXT") -> null
```

The first candidate had fixed native availability in the host thunk but still let the generated guest GDPA mapping treat the native host `vkGetDeviceProcAddr` pointer as an unknown dynamic target. Commit 2 was amended so guest GDPA returns its own guest entrypoint after the packed host lookup succeeds.

This correction is why the current candidate head is `c011366706eaf65a00380003989b3a10811212b6`; older `4f8130c...` receipts are superseded development evidence rather than final authority.

## Final exact-head receipt

```text
Actions run: 31776471366
job: 94692835765
CI workflow commit: 2edd7bbc9c8ac9174da5f5f3925cada722e03f6a
exact candidate source: c011366706eaf65a00380003989b3a10811212b6
artifact: 9210141962
artifact SHA-256: 6e8265bd344c221e4c866130dbfc5835e4340dc139f1c2cc52b4b6d450368a38
artifact retention: 30 days
runner: ubuntu-24.04-arm
```

Native ARM64 Lavapipe controls ran first:

- `vulkaninfo --summary` succeeded;
- debug-report callback control succeeded;
- debug-utils callback control succeeded;
- a real-device GDPA semantic control succeeded and reported `self_gdpa == direct_gdpa`.

Final hosted x86/FEX matrix:

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

### Callback routing

Both direct and GIPA routes now complete safely for debug-report and debug-utils while preserving FEX's existing callback-suppression behavior (`callback_count=0`).

### Native-null GIPA availability

```text
GIPA(NULL, "vkCreateDebugReportCallbackEXT") -> (nil)
GIPA(NULL, "vkCreateShaderModule") -> (nil)
```

### GIPA self-query behavior

A real instance was created and the probe observed:

```text
GIPA(instance, "vkGetInstanceProcAddr") == direct guest GIPA
GIPA(instance, "vkGetDeviceProcAddr") == direct guest GDPA
returned GIPA can query vkDestroyInstance successfully
GIPA(NULL, "vkGetInstanceProcAddr") == direct guest GIPA
GIPA(NULL, "vkGetDeviceProcAddr") == null
```

Representative receipt:

```text
SELF_RESULT instance_gipa=0x7ffff7ea22f0
            instance_gdpa=0x7ffff7ea2230
            destroy=<non-null linked proc>
            null_gipa=0x7ffff7ea22f0
            null_gdpa=(nil)
            direct_gipa=0x7ffff7ea22f0
            direct_gdpa=0x7ffff7ea2230
```

### Real-device GDPA behavior

The final FEX probe created a real Lavapipe device and observed:

```text
GDPA(device, "vkDestroyDevice") -> non-null
GDPA(device, "vkAllocateMemory") -> non-null
GDPA(device, "vkCreateShaderModule") -> non-null
GDPA(device, "vkCreateInstance") -> null
GDPA(device, "vkCreateDebugReportCallbackEXT") -> null
GDPA(device, "vkGetDeviceProcAddr") == direct guest GDPA
```

Representative final FEX line:

```text
GDPA_RESULT destroy_device=<non-null>
            alloc_memory=<non-null>
            shader=<non-null>
            gipa_shader=<same guest callable shader proc>
            create_instance=(nil)
            debug_report=(nil)
            self_gdpa=0x7ffff7ea2230
            direct_gdpa=0x7ffff7ea2230
```

The native control reported the same command-level availability and self-GDPA relationship.

This final run covers every proc-address behavior changed by the candidate.

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

## Internal review surfaces

### Product candidate

```text
teamleaderleo/FEX pull request 1
base: fork main
head: fix/vulkan-callback-proc-routing
head SHA: c011366706eaf65a00380003989b3a10811212b6
state: draft
```

The fork `main` policy/documentation commits are ahead of the exact product base; the PR remains a review surface rather than a claim that the exact tested branch has been rebased.

### Prevention candidate

A separate stacked draft keeps the inventory test out of the runtime fix:

```text
teamleaderleo/FEX pull request 2
base: fix/vulkan-callback-proc-routing
head: test/vulkan-custom-route-invariant-v2
state: draft
```

## Long-term prevention receipt

The investigation found a two-source-of-truth problem: `custom_host_impl` metadata and the manual `LookupCustomVulkanFunction()` inventory can drift independently.

The prevention branch adds a source-level `.ThunkGen` inventory test for both 64-bit and 32-bit thunk modes.

Rebased prevention validation:

```text
Actions run: 31776688975
artifact: 9210121093
artifact SHA-256: c944d8838858e8d6887c430058340f2eb7abc3f01458530aedc2925dc85f48b2
prevention branch head: 275f6162178ebe65c7f44904bd1b1b784c3f836c
base candidate: c011366706eaf65a00380003989b3a10811212b6
```

Old product source is expected to fail:

```text
x86_64: custom_host_impl=12 lookup=9
  missing: vkCreateDebugReportCallbackEXT, vkCreateDebugUtilsMessengerEXT, vkDestroyDebugReportCallbackEXT
x86_32: custom_host_impl=21 lookup=18
  missing: vkCreateDebugReportCallbackEXT, vkCreateDebugUtilsMessengerEXT, vkDestroyDebugReportCallbackEXT
```

Candidate inventory passes:

```text
x86_64: custom_host_impl=12 lookup=12
  missing: (none)
  lookup-only: (none)
x86_32: custom_host_impl=21 lookup=21
  missing: (none)
  lookup-only: (none)
```

The prevention mechanism remains independently reviewable from the runtime patch.

## Remaining human-only test

Hosted ARM64 now covers the software/emulation lane. The smallest hardware-specific confirmation is Apple M5 + Venus using the exact clean candidate head:

```text
c011366706eaf65a00380003989b3a10811212b6
```

Run the same small x86 callback probe through GIPA for debug-report and debug-utils under the Venus ICD. Capture source SHA, Mesa/Venus identity, command, exit status, and driver/device strings. A `vulkaninfo --summary` pass is useful as an integration check but is secondary to the small deterministic callback probe.
