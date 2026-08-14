# Generated Vulkan custom-route registry experiment — 2026-08-14

## Purpose

This note records an owned-fork experiment for removing the duplicated handwritten Vulkan dynamic-custom routing inventory.

It is **not** a replacement for the already-clean callback/proc-address product candidate documented in `CLEAN_CALLBACK_ROUTING_CANDIDATE.md`. That candidate remains the clean source-only runtime fix and already has a dedicated prevention branch using an inventory invariant test.

This experiment tests a stronger long-term prevention option: make existing `custom_host_impl` metadata directly generate the host-side dynamic custom registry so declaration and registration cannot drift independently.

No upstream FEX state was changed.

## Design

The thunk generator already knows, for every thunked API function, whether its selected implementation has `custom_host_impl`. Vulkan's `internal` namespace also already opts into generated guest symbol tables and indirect guest calls.

The experiment extends host output generation with a namespace-scoped enumerator:

```text
FOREACH_<namespace>_CUSTOM_HOST_SYMBOL(EXPAND)
```

Generation is limited to namespaces that opt into both:

```text
generate_guest_symtable
indirect_guest_calls
```

Within those namespaces, only API functions whose thunk metadata has `custom_host_impl` are emitted.

`ThunkLibs/libvulkan/Host.cpp` then implements `LookupCustomVulkanFunction()` by expanding:

```text
FOREACH_internal_CUSTOM_HOST_SYMBOL(...)
```

This deliberately excludes the top-level public `vkGetInstanceProcAddr` and `vkGetDeviceProcAddr` implementations, because they are outside Vulkan's internal indirect-call namespace.

## Generated inventory observed

The corrected integration build generated the expected 64-bit internal custom set:

```text
vkCreateInstance
vkCreateDevice
vkAllocateMemory
vkFreeMemory
vkCreateShaderModule
vkCreateDebugReportCallbackEXT
vkDestroyDebugReportCallbackEXT
vkCreateDebugUtilsMessengerEXT
vkAcquireXlibDisplayEXT
vkGetRandROutputDisplayEXT
vkGetPhysicalDeviceXcbPresentationSupportKHR
vkGetPhysicalDeviceXlibPresentationSupportKHR
```

The generated 32-bit registry also included the additional 32-bit custom-host functions already identified by the source audit.

The integration verification explicitly required the three historically missing callback commands and rejected `vkGetInstanceProcAddr` / `vkGetDeviceProcAddr` from the internal custom registry.

## Integration build receipt

Owned fork research branch:

```text
repository: teamleaderleo/FEX
branch: linux-fieldwork/vulkan-procaddr-native-first-experiment
workflow: Vulkan generated custom registry experiment
run: 31776226009
```

The first run exposed only an output-formatting defect: the experiment emitted literal `\n` text into the generated macro. The generated symbol selection itself was already correct. The output was simplified to one physical generated line per macro/symbol.

After that correction:

```text
full FEX build: success
64-bit Vulkan host thunk: success
32-bit Vulkan host thunk: success
generated custom registry verification: success
```

This establishes that generated ownership is compatible with both Vulkan thunk ABIs at compile/integration level.

## Combined ARM64 runtime receipt

The strongest experiment applies together:

1. native-first GIPA/GDPA availability handling;
2. generated internal custom-host registration;
3. debug-utils `vkCreateInstance` pNext callback mediation;
4. the corrected pNext walker that re-examines the replacement node after debug-report removal.

Receipt:

```text
workflow: Vulkan combined routing candidate
run: 31776341731
job: 94692442902
carrier head: c65299736980783a622d3a918811dae832dea075
artifact: 9210122391
artifact SHA-256: b509e96ccba00a0cc08c06b86beb9d5d9ef4d4a622c155e08c77ed7b5d74cd3b
runner: ubuntu-24.04-arm
```

The workflow built and installed FEX with thunks, verified the generated registry, compiled x86-64 probes, built a minimal x86 rootfs, and ran the complete hosted Vulkan matrix against Lavapipe/validation layers.

### Direct and dynamic callback paths

All four callback routes completed safely with the guest callback suppressed as intended:

```text
direct-report=0
direct-utils=0
dynamic-report=0
dynamic-utils=0
callback_count=0
```

### Proc-address availability

The native-first matrix passed:

```text
GIPA(NULL, "vkCreateInstance")               -> non-null
GIPA(NULL, "vkCreateDevice")                 -> null
GIPA(NULL, "vkGetDeviceProcAddr")            -> null
GIPA(instance, "vkGetInstanceProcAddr")       -> non-null
GIPA(instance, "vkCreateDevice")             -> non-null
GIPA(instance, "vkGetDeviceProcAddr")         -> non-null
disabled debug-report create                  -> null
disabled debug-utils create                   -> null
```

Overall proc-address probe:

```text
PROCADDR_FINISH failures=0
```

### Repeated dynamic lookup

Repeated lookup returned stable guest-callable pointers and a dynamically returned `vkCreateInstance` pointer successfully created an instance:

```text
REPEAT_CREATE same=1
REPEAT_DYNAMIC_CREATE result=0
REPEAT_SELF same=1
REPEAT_GDPA same=1
```

### pNext callback mediation

Single debug-utils pNext record:

```text
PNEXT_ZERO_CREATE result=0 callback_count=0
```

Adjacent `debug-report -> debug-utils` records:

```text
PNEXT_ADJACENT_CREATE result=0 report_count=0 utils_count=0
```

The adjacent case is important because the older walker could remove the debug-report node and then advance past the newly exposed debug-utils node.

## Generator-level regression

A small `.ThunkGen` regression was added experimentally with this synthetic namespace form:

```text
namespace internal {
  default config -> generate_guest_symtable + indirect_guest_calls
  ordinary()     -> ordinary API function
  custom()       -> custom_host_impl
}
```

The test requires the generated `FOREACH_internal_CUSTOM_HOST_SYMBOL` registry to contain `custom` and exclude `ordinary`.

The first harness attempts failed before exercising that assertion:

1. missing NASM in the hosted test environment;
2. `thunkgen_tests` absent because the workflow had configured `BUILD_THUNKS=False`;
3. the first synthetic source included `common/GeneratorInterface.h`, which the unit harness does not expose as an include path.

All three were test-harness issues, not failures of the generated-membership assertion. The final fixture is self-contained: it defines the minimal annotation marker types it needs in the synthetic prelude, configures `BUILD_THUNKS=True`, and installs NASM.

Final receipt:

```text
workflow: Thunkgen custom registry regression
run: 31777520071
job: 94695981209
carrier head: c07ffb2c3ab7bdd06227d67d9ce463b3059c8c20
runner: ubuntu-24.04-arm
```

The new focused test executed as part of the existing `.ThunkGen` set:

```text
Test #4226: Custom host symbol registry follows namespace metadata.ThunkGen ... Passed 0.12 sec
100% tests passed, 0 tests failed out of 16
Total Test time (real) = 9.94 sec
```

This closes the generator-level invariant: with namespace defaults matching Vulkan's internal indirect-call configuration, an ordinary function stays out of the generated custom registry while the `custom_host_impl` function is included.

## Successor-function validation from allocator work

A later allocator experiment created a new custom-host command that was **not** one of the original three debug callback omissions. This provides a useful independent test of the same ownership problem.

Against exact product source `71afe476751deac24adabd1adb575fd2337b6e0a`, the experiment changed `vkDestroyInstance` from generic to `custom_host_impl` and added a direct wrapper that suppresses the unsupported guest `VkAllocationCallbacks` pointer by passing NULL to native Vulkan.

Direct execution reached the new custom wrapper, returned safely, and then deliberately failed the fidelity probe because the allocator callbacks were ignored:

```text
fex_direct=10
MARK destroy-return alloc=0 realloc=0 free=0 free_delta=0
```

The same `vkDestroyInstance` obtained dynamically through GIPA did **not** reach the new wrapper because the handwritten Vulkan lookup table had not been updated. It re-opened the cross-ISA callback escape and died with SIGILL/132:

```text
native=0
native_dynamic=0
fex_direct=10
fex_dynamic=132
```

Receipt:

```text
workflow: Vulkan instance allocator suppression experiment
run: 31778088761
job: 94697682394
carrier: bbce1e8c1ea9869ef3ddab3e6236dffe060523c1
artifact: 9210726208
artifact SHA-256: 786da5be1a8675109ff3d86b2e1d527006748c1b61a840cc85ca2b2146546366
```

This is stronger than the original historical inventory mismatch because it is a fresh successor command created during the investigation:

> A newly correct direct custom implementation immediately becomes dynamically incorrect if its registration is a separate handwritten maintenance step.

Under generated ownership, marking `vkDestroyInstance` `custom_host_impl` in the internal indirect-call namespace would automatically place it in the generated custom registry. The experiment therefore validates the proposed prevention mechanism against a new function, not only the original three names that motivated the work.

## 32-bit evidence boundary

The generator and host-thunk integration cover both 64-bit and 32-bit metadata/output. A standalone Linux i386 Vulkan guest runtime was attempted on the exact clean callback/procaddr candidate, but current FEX GuestLibs CMake intentionally places Vulkan guest-thunk generation inside the `BITNESS == 64` block. The normal build produces `HostThunks_32/libvulkan-host.so` but no `GuestThunks_32/libvulkan-guest.so`.

Therefore the 32-bit Vulkan lane should currently be described as source/generator/host-thunk covered, not standalone Linux guest-runtime covered. Do not infer a 32-bit runtime failure from the harness attempt.

## Relationship to the existing prevention candidate

`CLEAN_CALLBACK_ROUTING_CANDIDATE.md` documents a separate, already-passing prevention branch that mechanically compares the handwritten lookup inventory against `custom_host_impl` metadata for x86-64 and x86-32.

That is a smaller incremental prevention change and is already reviewable independently.

Generated ownership has a stronger invariant:

> An internal indirectly callable command marked `custom_host_impl` becomes dynamically custom-routable from the same metadata, without a second Vulkan name list.

Tradeoff: it changes generator output/API rather than adding only a focused Vulkan inventory test. The runtime/build evidence and the independent `vkDestroyInstance` successor-function reproduction now show that this ownership model prevents a real class of future regressions; maintainability/review scope decides which prevention mechanism is preferable.

## Acceptance and reopen conditions

Generated ownership is a credible production direction if all of these remain true:

- full 64-bit and 32-bit Vulkan host-thunk builds pass;
- generated membership follows namespace and `custom_host_impl` metadata exactly;
- top-level GIPA/GDPA stay outside the internal custom registry;
- native-first availability remains authoritative before custom substitution;
- the focused generator regression passes;
- no API is found that intentionally wants custom direct calls but native dynamic calls.

Reopen the design if such an intentional exception exists or if another thunk library would receive an unwanted generated registry from the same namespace rule.
