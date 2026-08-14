# Hosted evidence — Vulkan proc-address and callback mediation

This receipt is separate from `EVIDENCE.md` because it comes from the owned ARM64 GitHub Actions experiments rather than the original Fedora/Lima field environment.

## Source and execution boundary

- Owned FEX fork branch: `linux-fieldwork/vulkan-procaddr-native-first-experiment`
- Owned Fieldwork probe branch: `probe/fex-vulkan-callback-ci`
- Base FEX source for the experiments: `e869aa644a16e4332cdc15c1ea0b4d13d482385d`
- Runner: GitHub-hosted Ubuntu 24.04 ARM64
- Host compiler: Clang 18
- Native Vulkan: lavapipe
- Guest: x86-64 Ubuntu 24.04 rootfs under the locally built ARM64 FEX
- Guest Vulkan library: locally built FEX `libvulkan-guest.so`
- Headless X11 requirement: satisfied by the narrow `x11_symbol_fixture.c` fixture on the Fieldwork probe branch

No upstream FEX repository mutation or contact was performed.

## Static custom-host registry mismatch

The Vulkan `namespace internal` source set contains 21 `custom_host_impl` functions in the 32-bit-conditioned host configuration, while the hand-written `LookupCustomVulkanFunction()` baseline registers 18. The exact missing set is:

- `vkCreateDebugReportCallbackEXT`
- `vkDestroyDebugReportCallbackEXT`
- `vkCreateDebugUtilsMessengerEXT`

The 64-bit common set has the same three omissions: 12 custom functions versus 9 registered functions. There are no lookup-only extras.

The V3 source candidate closes that static mismatch: 21 custom / 21 registered / 0 missing in the conditioned audit.

## Dynamic callback and proc-address differential

Candidate source delta: `LINUX_FIELDWORK_NATIVE_FIRST_V3.patch` in the owned FEX fork.

The candidate changes the proc-address rule to:

1. ask native Vulkan whether the requested name is valid for the supplied instance/device context;
2. return `NULL` if native Vulkan returns `NULL`;
3. substitute the FEX custom-host implementation when the resolved Vulkan command requires FEX mediation;
4. otherwise return the native pointer;
5. on the guest side, substitute the guest GIPA/GDPA entrypoints only after successful host/native resolution.

Hosted baseline versus candidate matrix:

| Probe | Baseline | V3 candidate |
| --- | ---: | ---: |
| direct debug-report create | 0 | 0 |
| direct debug-utils create | 0 | 0 |
| dynamic debug-report create | 132 | 0 |
| dynamic debug-utils create | 132 | 0 |
| proc-address semantic matrix | 20 | 0 |

Baseline dynamic logs show the callback/messenger creation succeeds and the process then exits 132 when native ARM attempts to invoke the x86 callback address. Direct calls already enter FEX's custom wrappers and complete.

The proc-address baseline specifically returned non-NULL for invalid NULL-instance queries such as `vkCreateDevice` and `vkGetDeviceProcAddr`, while failing the GIPA self query. V3 fixes those cases while retaining `NULL` for disabled/unavailable extension commands.

## Repeated proc-address pointer use

`procaddr_repeat_probe.c` checks more than pointer non-NULL status:

- repeated `GIPA(NULL, "vkCreateInstance")` results are non-NULL and equal;
- the returned `vkCreateInstance` pointer is actually called and must create a real instance;
- repeated GIPA self-query results are non-NULL and equal;
- repeated `vkGetDeviceProcAddr` results obtained through a valid GIPA context are non-NULL and equal.

The V3 candidate passes this probe with exit 0 in the hosted runtime differential. The baseline is required by the differential workflow to remain nonzero.

## Independent `vkCreateInstance` debug-utils pNext escape

A separate callback path bypasses proc-address lookup entirely: `VkDebugUtilsMessengerCreateInfoEXT` may be supplied in `VkInstanceCreateInfo::pNext`, and the validation layer can invoke its callback during `vkCreateInstance`.

The probe deliberately supplies a validation-triggering debug-utils record.

Observed:

- native ARM64 control invokes the callback;
- untouched FEX exits 132 during instance creation;
- V3 still exits 132, proving the pNext escape is independent of proc-address routing.

A strip-node diagnostic candidate was sufficient to make instance creation succeed with guest callback count zero, but a higher-fidelity experiment retained the debug-utils record and replaced only its callback with an ARM-safe FEX dummy. In that experiment native validation visibly invoked the retained host dummy, `vkCreateInstance` succeeded, and the guest callback count remained zero.

## Clean pNext mediation candidate

`LINUX_FIELDWORK_DEBUG_UTILS_PNEXT_CLEAN.py` is the current owned-fork research delta. It:

- keeps the existing FEX policy of removing the legacy debug-report callback record;
- re-examines the replacement node after removal, so adjacent callback-bearing records are not skipped;
- retains `VkDebugUtilsMessengerCreateInfoEXT` but replaces `pfnUserCallback` with FEX's existing host-safe `DummyVkDebugUtilsMessengerCallback`;
- otherwise advances through the chain normally.

Hosted workflow run `31775767971`, job `94690774016`, completed successfully.

Exact result lines:

```text
PNEXT_ZERO_CREATE result=0 instance=0xff492ca50000 callback_count=0
PNEXT_ADJACENT_CREATE result=0 instance=0xff9b66950000 report_count=0 utils_count=0
```

The second line comes from an adjacent chain `debug-report -> debug-utils -> ...`, which is the case the old removal loop could skip after relinking the chain.

## Generator-owned custom registry experiment

The thunk generator already owns both pieces of metadata needed to avoid a second manual Vulkan registry:

- whether a function has `custom_host_impl`;
- whether its namespace participates in generated guest symtables and indirect guest calls.

The owned experiment emits a host-side `FOREACH_internal_CUSTOM_HOST_SYMBOL(...)` from that metadata and makes Vulkan's custom lookup consume it. The first build selected the correct 12 64-bit and 21 conditioned custom functions, but emitted malformed macro text with literal `\\n` sequences. That run is classified as a generator-output formatting failure, not a product result.

A corrected formatting experiment and a generator-level regression are running separately. Do not treat generated registration as validated until those gates pass.

## Current interpretation

The original missing `vkCreateDebugReportCallbackEXT` entry is a real bug, but the durable defect is broader: Vulkan dynamic dispatch duplicated `custom_host_impl` ownership in a hand-written lookup table and performed custom substitution before preserving native Vulkan's availability/NULL decision.

The runtime evidence also establishes a separate callback-bearing input-data problem in `vkCreateInstance::pNext`. Fixing proc-address routing alone does not close that path.

## Reopen conditions

Reopen the dynamic-routing conclusion if any of these occur:

- V3 fails with a different native Vulkan implementation while the same native query returns a valid pointer;
- a generated/custom wrapper needs loader state that native-first substitution does not initialize;
- repeated proc-address lookups cease to return stable callable guest-visible pointers;
- Vulkan commands outside the `internal` indirect-call namespace are found to require the same generated registry.

Reopen the pNext conclusion if:

- retaining debug-utils create-info with the host dummy changes required instance-creation behavior beyond callback delivery;
- another converter-supported callback-bearing pNext record is found to preserve a guest function pointer into native ARM execution;
- the clean chain walker fails on longer or reordered adjacent callback records.
