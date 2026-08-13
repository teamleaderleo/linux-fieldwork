# Callback-routing cross-review addendum

This addendum records what changed after comparing the independent source audit with the hosted callback lane and its newer history/design work.

## Stronger historical diagnosis

The missing callback routes are best described as an incomplete 2023 retrofit rather than a later deletion.

The parallel history pass traced the common proc-address custom-routing helper to FEX commit `c10402f4f9d589209b70b250cd94a1a98c55a7c7`. The callback-safe custom wrappers already existed, but the device-oriented manual custom list reused for instance lookup omitted:

- `vkCreateDebugReportCallbackEXT`
- `vkDestroyDebugReportCallbackEXT`
- `vkCreateDebugUtilsMessengerEXT`

That matches the current three-name inventory exactly. The older list also already contained broader-scope names such as `vkCreateInstance`, so the native-availability/scope issue is older than the callback regression itself.

This strengthens the "two sources of truth drifted" diagnosis: dynamic routing was introduced from an incomplete pre-existing list.

## Production sequencing refinement

The long-term design still benefits from making `custom_host_impl` metadata the owner of dynamic custom registration. Cross-review suggests a smaller first correctness patch is easier to verify:

1. add the three missing callback-family entries to the existing registry;
2. make host GIPA/GDPA query native Vulkan first and preserve native `NULL`;
3. substitute the FEX custom implementation only after native lookup succeeds;
4. repair the guest GIPA shortcut so `vkGetDeviceProcAddr` is substituted only after host/native lookup says it is valid in that context;
5. add a mechanical completeness test so the manual registry cannot silently diverge from `custom_host_impl` again.

Generated runtime registration can then be a follow-up cleanup. This splits the immediate correctness fix from a larger thunk-generator change while retaining the invariant.

## Latest hosted run classification

Hosted run `31731074124` does not reach the callback-routing boundary.

Its native controls are useful: the new proc-address semantics probe passes the expected native cases, including null-instance scope checks, valid-instance GIPA self-query, and disabled debug-extension NULL results.

Every FEX baseline variant in that run exits `132` before the callback/proc-address probe can execute:

- direct debug report: `132`
- direct debug utils: `132`
- dynamic debug report: `132`
- dynamic debug utils: `132`
- proc-address semantics probe: `132`

The common failure is FEX Vulkan guest initialization attempting to create a host trampoline for a null X11 guest function target. This is a fixture failure, not evidence for or against Finding A.

The minimal hosted rootfs lacks the x86 X11 symbols expected by Vulkan guest initialization. The parallel lane added a narrow X11 shim exporting only `XSync`, `XGetVisualInfo`, and `XDisplayString`; integrating that fixture is required before the hosted callback differential is meaningful.

The same run later stopped while staging the report-only candidate because the workflow searched a temporary install path that did not contain the expected host thunk. The candidate host thunk had built; the workflow failed to locate/package it. This is also harness evidence, not a product compile/runtime result.

## Cross-lane blind spots now considered

The combined test plan should retain all of these independent gates:

- **Direct versus dynamic:** direct exported custom functions should already receive FEX mediation; dynamic baseline should be the differentiating path.
- **Native availability:** a custom wrapper must not turn a native Vulkan `NULL` proc-address result into a function pointer.
- **Sibling control:** a report-only candidate should not change debug-utils behavior.
- **Non-null allocator fixture:** needed before independently claiming the destroy-debug-report omission is demonstrated at runtime.
- **32-bit runtime:** source inventory covers it, hosted execution does not yet.
- **Repeated queries / multiple objects:** exercise pointer/link consistency across repeated GIPA/GDPA resolutions.
- **Fake native Vulkan provider:** preferred deterministic test for exact command scope, availability, and callback/allocator values reaching native code.
- **Adjacent `vkDestroyDebugUtilsMessengerEXT`:** review separately if non-null allocation callbacks enter scope.

## Current conclusion after cross-review

The core Finding A conclusion is stronger, not weaker:

> FEX's dynamic Vulkan custom routing was introduced from an incomplete manual list. Three callback-related functions that already required custom host mediation were omitted, and the retained Apple-M5/FEX-2608 experiment demonstrates the consequence for `vkCreateDebugReportCallbackEXT`.

The production contract is now more precise:

> Native Vulkan owns whether a proc-address query succeeds. FEX may substitute its custom implementation only after that native query succeeds, and every dynamically queryable internal `custom_host_impl` must be covered by that substitution policy.

What remains unproved is the clean hosted ARM64 callback A/B for debug-utils and the allocator-sensitive destroy case. The latest hosted failure occurs before those tests and should not change their confidence classification.

## Owned FEX fork experiment

An owned fork branch exists at `teamleaderleo/FEX:linux-fieldwork/vulkan-procaddr-native-first-experiment`. It records the native-first experiment contract and is available for local/fork implementation work. FEX upstream remains untouched.
