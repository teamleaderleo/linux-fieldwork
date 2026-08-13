# Hosted Finding A checkpoint

Exact FEX source under test: `71afe476751deac24adabd1adb575fd2337b6e0a`.
Disposable Fieldwork branch: `probe/fex-vulkan-callback-ci`.

## Confirmed source result

Automated comparison of Vulkan `custom_host_impl` declarations against `LookupCustomVulkanFunction()` identifies exactly three missing callback-family custom routes on the common 64-bit path:

- `vkCreateDebugReportCallbackEXT`
- `vkDestroyDebugReportCallbackEXT`
- `vkCreateDebugUtilsMessengerEXT`

Agent A independently reproduced the same inventory for 64-bit and 32-bit thunk generation. The 32-bit-only custom implementations are already represented in the lookup.

History shows that the callback wrappers predate the shared lookup. In December 2023, the old `vkGetDeviceProcAddr` custom list was extracted into `LookupCustomVulkanFunction()` and then reused from `vkGetInstanceProcAddr`; the existing instance callback wrappers were not added. This makes proc-address command scope and native availability part of the production-fix decision.

Current preferred production direction for human re-derivation: query native GIPA/GDPA first, preserve native NULL/availability behavior, and substitute a FEX custom implementation only when native Vulkan reports the command available for the queried object/name. The simple common-table additions remain useful causal experiments.

## Hosted ARM64 result

Public `ubuntu-24.04-arm` runners can configure, build, and install exact-current FEX with Vulkan host/guest thunks using Clang/lld and cross toolchains.

Run `31727031022` completed the full hosted callback workflow. Native llvmpipe controls successfully exercised forced debug-report and debug-utils callbacks. All baseline and experimental FEX callback cases exited `132` before the existing probe logs, so that run is an environment/harness ceiling rather than a callback-candidate comparison.

The likely harness owner is FEX portable/config path resolution: runtime overlay loading reads `ThunksDB.json` from FEX's global config directory. The earlier callback workflow installed FEX under a private prefix but did not run it in portable mode. A corrected callback workflow now sets `FEX_PORTABLE=1`, `FEX_SILENTLOG=0`, and `FEX_OUTPUTLOG=stderr`.

A separate phase workflow distinguishes raw static x86 execution, dynamic guest execution, and `dlopen("libvulkan.so.1")`. Its current corrected run uses a libc-free static x86 `_start` control and portable-mode FEX.

## Evidence boundary

The original Apple-M5/FEX-2608 A/B remains the authoritative runtime demonstration for Finding A until the hosted corrected callback run reaches the same boundary. Hosted CI has independently proven the current source mismatch, exact-current buildability, native software-Vulkan fixtures, and candidate compilation path.

No FEX upstream interaction has occurred.
