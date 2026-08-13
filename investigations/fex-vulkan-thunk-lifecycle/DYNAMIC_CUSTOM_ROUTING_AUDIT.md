# Agent A audit — Vulkan custom host implementations and dynamic proc-address routing

## TL;DR

The existing Finding A is correct and narrower than the source defect.

FEX's Vulkan interface metadata already declares which entrypoints require a `custom_host_impl`, and the thunk generator preserves that fact. Dynamic Vulkan calls use a separate hand-maintained `LookupCustomVulkanFunction()` table in `ThunkLibs/libvulkan/Host.cpp`. At both reviewed FEX revisions, those two registrations disagree.

For both 64-bit and 32-bit Vulkan thunk builds, the exact missing internal custom-host entries are:

- `vkCreateDebugReportCallbackEXT`
- `vkDestroyDebugReportCallbackEXT`
- `vkCreateDebugUtilsMessengerEXT`

`vkCreateDebugReportCallbackEXT` is a demonstrated correctness bug in the retained runtime experiment. `vkCreateDebugUtilsMessengerEXT` is the same source-level callback hazard and should be treated as a correctness bug pending an independent runtime reproduction. `vkDestroyDebugReportCallbackEXT` is correctness-sensitive when the guest supplies non-null `VkAllocationCallbacks`; with the usual null allocator it can behave equivalently to the native path.

The stronger invariant is:

> When native Vulkan proc-address lookup says a command is available, an internal Vulkan command declared `custom_host_impl` must dynamically route through that custom host implementation, with the generated parameter/ABI annotations that belong to it.

That invariant belongs with the generator metadata, or at minimum should be mechanically checked against any manual routing table. A three-branch patch fixes the demonstrated symptom but leaves future drift possible.

There is a second adjacent design concern: the current host proc-address implementations consult the custom table before the native loader. A complete fix should preserve Vulkan's native availability/null decision for the supplied instance/device/name and substitute the custom implementation only for a command that native lookup actually exposes.

## Scope and authority

Internal carriers:

- [linux-fieldwork PR #669](https://github.com/teamleaderleo/linux-fieldwork/pull/669)
- [linux-fieldwork issue #670](https://github.com/teamleaderleo/linux-fieldwork/issues/670)

Reviewed FEX revisions:

- `FEX-2608` / `e869aa644a16e4332cdc15c1ea0b4d13d482385d`
- reviewed `main` / `71afe476751deac24adabd1adb575fd2337b6e0a`

Relevant source files are byte-identical across those two revisions for this lane:

- `ThunkLibs/libvulkan/Host.cpp` blob `535d6954f77871a74c47532637453189f99e0e39`
- `ThunkLibs/libvulkan/libvulkan_interface.cpp` blob `e85b5c1ba279d6404f178c0fa56227136f3aa935`

Additional source read:

- `ThunkLibs/libvulkan/Guest.cpp`
- `ThunkLibs/include/common/Guest.h`
- `ThunkLibs/include/common/Host.h`
- `ThunkLibs/Generator/analysis.cpp`
- `ThunkLibs/Generator/gen.cpp`
- `unittests/ThunkLibs/generator.cpp`

Historical intent:

- `https://redirect.github.com/FEX-Emu/FEX/pull/1803` added the debug-report custom wrappers to avoid passing guest callbacks directly to native Vulkan.
- `https://redirect.github.com/FEX-Emu/FEX/commit/4b76eb0b3f3e138b321e6511c2338300c655fb13` later added more aggressive instance-extension pointer reload behavior for existing custom functions.
- `https://redirect.github.com/FEX-Emu/FEX/commit/feaee702e9c949415e239563cdd6cb19707aebbb` later refined device-specific pointer reload behavior for custom host implementations.

No FEX upstream mutation, comment, review, reaction, email, issue, pull request, or backlink was created by this audit. Linux Fieldwork is the owned research surface.

## Exact mismatch inventory

### 64-bit thunk build

Internal functions declared `custom_host_impl`: **12**.

Covered by `LookupCustomVulkanFunction()`: **9**.

Covered common entries:

- `vkCreateShaderModule`
- `vkCreateInstance`
- `vkCreateDevice`
- `vkAllocateMemory`
- `vkFreeMemory`
- `vkAcquireXlibDisplayEXT`
- `vkGetRandROutputDisplayEXT`
- `vkGetPhysicalDeviceXcbPresentationSupportKHR`
- `vkGetPhysicalDeviceXlibPresentationSupportKHR`

Missing:

- `vkCreateDebugReportCallbackEXT`
- `vkDestroyDebugReportCallbackEXT`
- `vkCreateDebugUtilsMessengerEXT`

### 32-bit thunk build

Internal functions declared `custom_host_impl`: **21**.

Covered by `LookupCustomVulkanFunction()`: **18**.

The same three common entries are missing.

All nine 32-bit-only custom host functions are present in the lookup table:

- `vkAllocateCommandBuffers`
- `vkEnumeratePhysicalDevices`
- `vkFreeCommandBuffers`
- `vkGetDeviceQueue`
- `vkGetPipelineCacheData`
- `vkMapMemory`
- `vkQueueSubmit`
- `vkCmdSetVertexInputEXT`
- `vkUpdateDescriptorSets`

### Custom-host functions outside the internal Vulkan command set

Two public proc-address functions are declared at top level as `custom_host_impl`, `custom_guest_entrypoint`, and `returns_guest_pointer`:

- `vkGetInstanceProcAddr`
- `vkGetDeviceProcAddr`

They are intentionally outside `namespace internal`, whose default config enables the generated guest symbol table and indirect guest calls. They therefore should not be mixed blindly into the internal command-table invariant. Their own dynamic/self-query semantics deserve explicit tests, described below.

Three private setup helpers are also top-level custom implementations:

- `Vulkan_SetGuestXSync`
- `Vulkan_SetGuestXGetVisualInfo`
- `Vulkan_SetGuestXDisplayString`

These are internal initialization helpers called by the Vulkan guest thunk. They are not Vulkan proc-address names and their absence from `LookupCustomVulkanFunction()` is benign.

## Classification by function

### `vkCreateDebugReportCallbackEXT` — demonstrated correctness bug

The custom host implementation copies/reinterprets the guest create-info, replaces `pfnCallback` with `DummyVkDebugReportCallback`, resolves the native Vulkan function, and calls it with a null allocation-callback pointer.

The retained runtime evidence in this investigation demonstrates the dynamic path failure:

1. pristine FEX reaches the extension through `vkGetInstanceProcAddr()`;
2. dynamic lookup omits the custom host implementation;
3. the original run dies with SIGILL on the callback path;
4. routing that dynamic name to the existing custom implementation makes the wrapper execute and removes the original SIGILL;
5. Vulkan enumeration then proceeds.

This establishes causality for the original callback-routing failure.

### `vkCreateDebugUtilsMessengerEXT` — source-level correctness bug; runtime reproduction pending

The custom implementation performs the same essential callback substitution for `VK_EXT_debug_utils`: it converts the guest create-info and replaces `pfnUserCallback` with `DummyVkDebugUtilsMessengerCallback` before entering native Vulkan.

Dynamic routing currently bypasses that implementation. A guest callback pointer can therefore escape the mediation policy already encoded by the custom implementation. On a 32-bit guest, the declared `ptr_passthrough` parameter also makes this a generated ABI/repacking concern: the indirect-call wrapper depends on the annotations associated with the function signature.

An isolated debug-utils runtime fixture would promote this from source-established hazard to demonstrated runtime defect.

### `vkDestroyDebugReportCallbackEXT` — conditional correctness bug

Its custom implementation resolves the native destroy function and forces `VkAllocationCallbacks*` to null.

When the guest passes null allocation callbacks, the direct native path can be behaviorally equivalent for this aspect. When the guest supplies allocation callbacks, dynamic bypass violates the policy implemented by the custom wrapper and may expose guest function pointers/data through the allocator interface.

The retained experiment where an added destroy lookup entry executes the custom wrapper and the process still exits 139 establishes only that this mismatch does not explain the separate unload/lifecycle crash. It does not make the routing omission harmless.

## Dynamic dispatch path

The dynamic path spans the generated and handwritten halves of the Vulkan thunk.

### 1. Guest requests a Vulkan command

Guest `vkGetInstanceProcAddr()` / `vkGetDeviceProcAddr()` calls the generated packing function for the corresponding custom host proc-address implementation.

### 2. Host proc-address implementation chooses an address

`FEXFN_IMPL(vkGetInstanceProcAddr)` and `FEXFN_IMPL(vkGetDeviceProcAddr)` first call `LookupCustomVulkanFunction(name)`.

If that lookup returns a pointer, the host side returns the FEX custom host implementation address.

If the name is absent, the host side asks native Vulkan and returns the native host function pointer.

### 3. Guest turns that host address into an indirect guest-call target

`ThunkLibs/libvulkan/Guest.cpp` builds `HostPtrInvokers` from `FOREACH_internal_SYMBOL`. Each Vulkan command name maps to `GetCallerForHostFunction(name)`, a signature-aware `CallHostFunction` instantiation.

`MakeGuestCallable(origin, host_pointer, name)`:

1. finds the command name in `HostPtrInvokers`;
2. calls `LinkAddressToFunction(host_pointer, guest_invoker)`;
3. returns the host pointer as the guest-visible PFN.

### 4. A later indirect call reaches the selected host address

`CallHostFunction` receives the linked host address through FEX's custom guest ABI, packs the Vulkan arguments plus that host target, and invokes the thunk callback entry.

On the host side, the generated `GuestWrapperForHostFunction` retrieves the appended host target and invokes it while applying the function's generated parameter annotations.

Therefore the name selected in step 2 controls whether the later indirect call reaches:

- `fexfn_impl_libvulkan_<name>` with custom policy, or
- the raw native Vulkan implementation.

The three missing entries return native addresses and bypass the custom policy even though the generator metadata says the corresponding commands require custom host implementations.

## Challenge to the original Finding A explanation

The original bounded claim — "dynamic GIPA bypasses the existing debug-report custom host implementation" — is supported.

The stronger explanation is a **registration completeness defect** between two sources of truth:

1. `libvulkan_interface.cpp` says which internal commands require custom host implementations;
2. `LookupCustomVulkanFunction()` separately enumerates which of those custom implementations dynamic Vulkan resolution should select.

The thunk generator already parses and stores `custom_host_impl` for every emitted function. It also generates symbol enumerators for configured namespaces. Nothing in the metadata model requires the dynamic custom-routing list to be handwritten.

The mismatch family is therefore broader than `VK_EXT_debug_report`.

### Availability/null semantics are part of the same review

A three-entry manual fix creates the expected custom pointer as soon as the name matches `LookupCustomVulkanFunction()`. The current host proc-address implementation performs that custom lookup before asking native Vulkan whether the supplied instance/device actually exposes the command.

Vulkan proc-address APIs use null results to communicate unavailable commands and scope/extension conditions. The safer invariant is consequently two-stage:

1. native lookup establishes availability for the supplied instance/device/name;
2. a successful result is substituted with the FEX custom implementation when generator metadata says the command is `custom_host_impl`.

Any candidate that expands `LookupCustomVulkanFunction()` should include negative controls for disabled extensions and invalid/wrong-scope queries so that FEX does not manufacture availability merely because a custom implementation exists.

## Proposed regression and invariant tests

### Test A — generated custom-host routing inventory

Best owner: thunk generator / generated Vulkan metadata.

Generate a custom-host symbol enumerator, or another machine-readable set, from the existing `ThunkedFunction::custom_host_impl` field for namespaces that support `indirect_guest_calls`.

Then require the Vulkan dynamic custom-routing set to equal that generated set for each ABI.

The existing `unittests/ThunkLibs/generator.cpp` fixture already runs interface snippets through the generator and compiles/AST-checks generated guest and host output. A small synthetic interface can assert that:

- ordinary indirect functions appear in the ordinary symbol set;
- custom-host indirect functions appear in the generated custom-host set;
- ABI-conditional custom functions appear only for the selected guest ABI.

This catches future omissions at generation/test time.

### Test B — Vulkan fake-loader proc-address matrix

Build a tiny native fake Vulkan loader/driver fixture that returns sentinel PFNs only for explicitly selected instance/device/name combinations.

Run a guest probe through the thunk and verify:

- dynamic `vkCreateDebugReportCallbackEXT` reaches the custom wrapper and native code sees the dummy callback;
- dynamic `vkCreateDebugUtilsMessengerEXT` reaches the custom wrapper and native code sees the dummy callback;
- dynamic `vkDestroyDebugReportCallbackEXT` gives native code a null allocator when the guest supplied a non-null allocator;
- unavailable extension functions still resolve to null;
- wrong-scope device/instance queries retain the native null result.

The negative cases distinguish "complete custom registration" from "return every custom symbol for every query".

### Test C — direct versus dynamic equivalence

For every internal `custom_host_impl` command that Vulkan permits through proc-address lookup, compare:

- direct guest symbol call;
- dynamically obtained PFN call.

Assert the same custom wrapper is reached and the same guest-to-host policy is applied. This is the user-visible invariant that the current handwritten list violates.

### Test D — adjacent proc-address self-query cases

Add explicit tests for:

- `vkGetInstanceProcAddr(instance, "vkGetInstanceProcAddr")`;
- the Vulkan-version-appropriate null-instance self-query case;
- `vkGetInstanceProcAddr(VK_NULL_HANDLE, "vkGetDeviceProcAddr")`;
- ordinary global-command null-instance queries.

Guest `vkGetInstanceProcAddr` currently special-cases `vkGetDeviceProcAddr` before performing the packed host query, while `vkGetInstanceProcAddr` itself has no equivalent guest-side self special-case and lies outside `HostPtrInvokers`. These deserve direct execution rather than inference from the callback fix.

## Competing implementation approaches

### Approach 1 — add the three missing branches only

Change `LookupCustomVulkanFunction()` to add:

- `vkCreateDebugReportCallbackEXT`
- `vkDestroyDebugReportCallbackEXT`
- `vkCreateDebugUtilsMessengerEXT`

Advantages:

- smallest source edit;
- directly repairs the demonstrated debug-report create path;
- easy to A/B against the current investigation.

Costs:

- preserves duplicated registration state;
- future custom-host additions can drift again;
- without native availability gating, it can return custom PFNs in queries where native Vulkan would return null.

Use as a diagnostic candidate, not as the preferred long-term owner.

### Approach 2 — manual table plus generated invariant test

Keep the handwritten runtime table but generate the authoritative expected set from thunk metadata and fail a unit/build test when the sets differ.

Advantages:

- modest runtime change;
- catches future drift;
- lets Vulkan-specific runtime exceptions stay explicit.

Costs:

- two registrations still exist;
- every deliberate exception needs a named policy or allowlist.

This is a reasonable incremental candidate if generator-produced runtime dispatch is considered too invasive.

### Approach 3 — generate the dynamic custom-routing table

Use the already parsed `custom_host_impl` metadata to emit a macro/table mapping internal command names to `fexfn_impl_libvulkan_<name>`.

Advantages:

- one authoritative declaration owns both direct and dynamic custom routing;
- 64/32 ABI conditionals naturally follow the same interface generation;
- future custom functions cannot silently omit dynamic registration.

Costs:

- generator output needs a new host-side enumerator/table format;
- Vulkan-specific exceptions, if any exist, need explicit metadata.

This is the strongest long-term ownership candidate found in this audit.

### Approach 4 — native-first lookup plus generated substitution

Combine generated custom registration with native Vulkan availability gating:

1. call native GIPA/GDPA for the supplied object and command name;
2. return null when native lookup returns null;
3. when native lookup succeeds, return the generated FEX custom implementation for custom-host commands;
4. return the native pointer for ordinary commands.

Advantages:

- preserves Vulkan availability semantics;
- eliminates registration drift;
- naturally distinguishes "custom implementation exists" from "command is valid in this query context."

Costs:

- custom wrappers that lazily resolve native pointers must be reviewed for recursive lookup and pointer initialization;
- existing extension-pointer refresh code may need consolidation.

This is the preferred design direction from source review, subject to fake-loader and real-driver regression execution.

### Approach 5 — guest-side substitution

Teach `MakeGuestCallable()` or guest proc-address wrappers to substitute fixed guest thunk entrypoints for custom-host command names.

Advantages:

- dynamic dispatch policy sits near the guest PFN mechanism.

Costs:

- creates another Vulkan-specific name registry unless generated;
- changes pointer-identity behavior;
- duplicates logic already represented naturally by host custom implementations.

This is weaker than generated host-side substitution.

## Reproducible inventory helper

This investigation now includes:

```text
audit_custom_vulkan_lookup.py
```

Usage from the investigation directory:

```sh
python3 audit_custom_vulkan_lookup.py /path/to/FEX
```

It evaluates `IS_32BIT_THUNK` branches for both guest ABIs, extracts internal `custom_host_impl` declarations from `libvulkan_interface.cpp`, extracts names from `LookupCustomVulkanFunction()`, and prints missing and lookup-only entries. A mismatch returns exit status `1` so it can serve as a local invariant check.

The parser was syntax-checked and run against a synthetic fixture in this audit session. The current execution sandbox could not resolve `github.com` for a direct local checkout, so the exact FEX revision was source-read through the GitHub connector rather than executed through this helper here. The helper should be run against the retained/local FEX checkout as the next mechanical receipt.

## Exact uncertainty

### Established

- The two reviewed FEX revisions use identical blobs for the relevant interface and host files.
- The exact internal set mismatch is three names on both 64-bit and 32-bit builds.
- All nine 32-bit-only custom-host commands are present in the dynamic lookup table.
- The three private `Vulkan_SetGuestX*` helpers are outside the Vulkan proc-address namespace and are benign exclusions.
- `vkCreateDebugReportCallbackEXT` dynamic routing is a demonstrated runtime correctness bug in the retained FEX-2608 evidence.
- `vkCreateDebugUtilsMessengerEXT` has the same source-level callback substitution requirement and is omitted from dynamic custom routing.
- `vkDestroyDebugReportCallbackEXT` has a semantic difference for non-null allocation callbacks.
- The thunk generator already retains `custom_host_impl` as analyzed function metadata and already emits namespace symbol enumerators.

### Still open

- Independent runtime reproduction of the `vkCreateDebugUtilsMessengerEXT` omission.
- Isolated A/B runtime proof for destroy-debug-report with a non-null guest allocator.
- Direct execution of the GIPA/GDPA self-query and null/scope cases.
- A fake-loader test demonstrating which candidate best preserves native availability semantics.
- Whether any internal `custom_host_impl` Vulkan command intentionally wants direct custom routing but native dynamic routing. No such exception marker was found; if one exists it should become explicit metadata.
- Current-main runtime execution. Source is identical for this lane, while the retained runtime evidence is FEX-2608.

## Reopen conditions

Reopen the three-name inventory if either reviewed source blob changes or a new `custom_host_impl` is added under `namespace internal`.

Reopen the generator-ownership recommendation if a concrete Vulkan command is found where `custom_host_impl` intentionally applies only to direct symbol calls and dynamic proc-address calls must invoke the native implementation. That case should carry explicit metadata or an explicit generated exception.

Reopen the source-level `vkCreateDebugUtilsMessengerEXT` bug classification if runtime or ABI evidence shows its dynamically returned native path still receives a host-callable callback through another mechanism before entering native Vulkan.

Reopen the destroy-debug-report classification if FEX explicitly guarantees guest allocation callbacks are always null/ignored before this path or if an independent non-null-allocator fixture demonstrates equivalence.

Reopen native-first substitution if a real driver or loader requires custom wrappers to be returned in a query context where native lookup itself returns null. That would need a precise Vulkan-contract explanation and a targeted test.

A separate adjacent question remains: `vkDestroyDebugUtilsMessengerEXT` is not declared `custom_host_impl` even though the create function is custom and the destroy signature includes `VkAllocationCallbacks`. That is outside this declaration-versus-lookup mismatch audit and deserves a successor fixture if non-null Vulkan allocation callbacks enter scope.

## Disposition

Finding A should be retained with a wider technical explanation:

> FEX has a dynamic Vulkan custom-routing completeness defect. The generator metadata declares three internal callback-related commands as `custom_host_impl` while the handwritten dynamic lookup omits them. The demonstrated `vkCreateDebugReportCallbackEXT` SIGILL is one concrete consequence. The durable fix should make dynamic custom routing derive from, or be mechanically checked against, the same metadata and preserve native Vulkan proc-address availability semantics.

The unload/lifecycle finding remains separate and is reviewed in `ADVERSARIAL_REVIEW.md`.
