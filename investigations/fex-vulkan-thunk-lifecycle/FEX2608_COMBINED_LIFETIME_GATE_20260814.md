# Exact FEX-2608 combined thunk-lifetime gate — 2026-08-14

## Result

One exact-FEX-2608 build now carries the callback-lifetime transaction, the unload-preserving resident Vulkan bridge, and the Vulkan debug-report dynamic lookup repair together and passes all focused lifetime gates in the same binary.

Exact product base:

- FEX-2608
- `e869aa644a16e4332cdc15c1ea0b4d13d482385d`

Canonical combined run:

- `https://redirect.github.com/teamleaderleo/FEX/actions/runs/31792506486`
- conclusion: success

The carrier branch is `ci/fex2608-staged-lifetime-integration-20260814`. The workflow first verifies that product source still matches the exact FEX-2608 base, then applies the tested transforms, builds FEX plus the 64-bit Vulkan guest wrapper and resident bridge, prepares one amd64 rootfs, and executes all four gates against that same build.

## Combined candidate contents

### Arbitrary host -> guest callbacks

The callback path uses stable process-lifetime descriptor identity. A published host trampoline reaches the descriptor, which owns the guest unpacker/target generation and a state machine:

- `Live`
- `Draining`
- `Revoked`

Active executions acquire a descriptor lease. Destructive guest unmap runs as a transaction:

`BeginDrain -> host munmap -> CommitRevoke / RollbackLive`

New callback arrivals wait while a descriptor is `Draining`, so failed `munmap` can restore `Live` without exposing a transient false callback failure. A draining-range registry covers registrations that race the initial descriptor scan. Active-drain waits happen after releasing the global thunk registry mutex.

### Vulkan dynamic PFNs and FEX-owned escaping executable code

The ordinary `libvulkan-guest.so` remains unloadable. Generated executable adapters whose addresses can escape wrapper lifetime live in `libfex-vulkan-bridge.so`, which is linked process-resident with `-z,nodelete`.

The bridge includes:

- generated dynamic Vulkan `CallHostFunction<...>` adapters selected by the split generator path;
- the optional fatal unknown-function invoker;
- the three Vulkan/X11 callback unpackers.

The wrapper publishes resident bridge addresses while its ordinary API/constructor state can still follow real `dlopen` / `dlclose` lifetime.

### Debug-report routing

`LookupCustomVulkanFunction()` now routes both existing custom implementations:

- `vkCreateDebugReportCallbackEXT`
- `vkDestroyDebugReportCallbackEXT`

This remains a separate repair from the thunk lifetime work.

## Gate 1 — active callback drain

The deterministic fixture enters a guest callback through FEX's native host trampoline and blocks inside host code while another guest thread performs the final close.

Observed in the combined run:

- descriptor enters `Draining` with one active execution;
- final close remains blocked before release;
- callback returns `70053` normally;
- active count reaches zero;
- drain completes and retirement commits;
- `dlclose` returns 0;
- a later escaped old trampoline reaches the permanent revoked descriptor and exits 113;
- fixture reports `INFLIGHT DRAIN_PASS`.

This preserves the earlier causal result in the full combined candidate.

## Gate 2 — failed-munmap rollback and arrivals during Draining

The fixture intentionally issues an unaligned `munmap` whose retirement range covers the live callback. Linux rejects the host operation with `EINVAL`.

Observed:

- callback A is active while the descriptor drains;
- callback B arrives during `Draining` and waits;
- before release, neither the `munmap` transaction nor callback B has completed;
- callback A returns `70053`;
- host `munmap` returns `-1`, `errno=22`;
- transaction rolls the descriptor back to `Live`;
- callback B wakes and returns `70063`;
- a later valid final close commits revocation;
- the escaped old callback then exits 113;
- fixture reports `TXWAIT PASS`.

This preserves both required transactional properties: rollback on failed unmap and wait-on-Draining for concurrent arrivals.

## Gate 3 — saved dynamic Vulkan PFN after real wrapper unload

The retained Vulkan PFN probe obtains `vkEnumerateInstanceVersion` dynamically through `vkGetInstanceProcAddr`, calls it, performs the final real application `dlclose`, and calls the saved PFN again.

Observed:

- the generation-1 ordinary Vulkan wrapper mapping disappears;
- the saved dynamic PFN remains executable through the resident bridge;
- native Vulkan returns success after wrapper unload.

This is the intended split-lifetime behavior. The probe source on `probe/fex-vulkan-combined-repair` has been updated to describe the successful post-close call as resident-bridge behavior.

## Gate 4 — real debug-report path plus split lifetime

The combined retained probe:

1. opens Vulkan;
2. enumerates the API version;
3. creates a `VkInstance` with `VK_EXT_debug_report`;
4. dynamically resolves `vkCreateDebugReportCallbackEXT` and `vkDestroyDebugReportCallbackEXT` through `vkGetInstanceProcAddr`;
5. creates a real guest callback;
6. destroys the callback;
7. destroys the instance;
8. performs the final application Vulkan close;
9. verifies the wrapper address is unmapped;
10. calls a previously saved dynamic version PFN through the resident bridge.

Observed:

- instance creation succeeds;
- debug-report callback creation succeeds;
- debug-report callback destruction completes;
- instance destruction completes;
- ordinary wrapper is unmapped after close;
- saved dynamic PFN returns success after that unmap;
- probe reports `COMBINED PASS`.

This exercises the original routing repair and the preferred lifetime repair together in one exact historical build.

## Promoted fork-local research snapshot

The exact transform stack that passed the combined gate was materialized as one source commit directly on top of FEX-2608:

- branch: `candidate/fex2608-combined-thunk-lifetime`
- commit: `d73d8b99790b311a7f53a538bcec54edc21171a5`
- branch: `https://redirect.github.com/teamleaderleo/FEX/tree/candidate/fex2608-combined-thunk-lifetime`

The comparison against FEX-2608 is one commit ahead and zero behind. It tracks the resident bridge implementation files (`GuestBridge.cpp`, `ExtractBridgeSymbols.py`, and `ExtractBridgeThunks.py`) in addition to the core callback/unmap changes and Vulkan routing changes.

This branch is a proven research snapshot. It still contains diagnostic logging and earlier thunk-H retirement hygiene from the experimental lineage; those pieces should be cleaned and independently re-gated before calling the branch a polished product candidate.

## Design conclusion

The combined gate supports two distinct ownership rules:

1. FEX-generated executable bridge code whose address intentionally escapes an unloadable wrapper receives process lifetime in a small resident per-library bridge.
2. Guest-owned callback executable code keeps guest lifetime, while FEX publishes it through stable permanent generation-specific descriptors that drain active execution and transactionally revoke only after successful destructive unmap.

Whole-wrapper process residency remains a conservative fallback. CustomIR retirement alone remains insufficient for the primary changed-base Vulkan failure and is not the main Vulkan repair represented by this result.

## Evidence boundary

The exact terminal transfer from the historical Apple M5 teardown remains uncaptured. The lifetime repair no longer depends on recreating that final workstation-specific edge: focused real-FEX fixtures causally exercise the escaping PFN, callback execution, rollback, and concurrent-arrival lifetime boundaries directly.

No interaction with upstream `FEX-Emu/FEX` was performed.
