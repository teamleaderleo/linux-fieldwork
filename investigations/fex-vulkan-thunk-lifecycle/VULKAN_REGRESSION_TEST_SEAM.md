# Vulkan regression test seam

Status: source/test-placement analysis complete; no upstream CI change made.

## Goal

Protect the Vulkan callback fixes with small deterministic regressions rather than carrying the hosted 760-name differential as permanent CI.

The minimum behaviors worth protecting are:

1. Direct and `vkGetInstanceProcAddr` callback creation for debug-report/debug-utils must route through FEX's safe custom implementation when native Vulkan reports the proc as available.
2. The native-first availability guard must return null when the host Vulkan proc lookup returns null.
3. Temporary callback-bearing nodes in `VkInstanceCreateInfo::pNext` must be suppressed during host `vkCreateInstance`, including consecutive debug-report/debug-utils nodes, without changing guest-visible input pointers after the call.

## Existing test seams

### `unittests/ThunkFunctionalTests`

This is the semantically closest existing suite. Its current CMake file registers:

- `/usr/bin/glxinfo` with `Data/CI/GLThunks.json`
- `/usr/bin/vulkaninfo` with `Data/CI/VulkanThunks.json`

The `thunk_functional_tests_thunks` target runs those programs through FEX with thunk configuration enabled.

A small x86-64 guest Vulkan probe added to this suite would naturally exercise the real generated guest thunk plus real host thunk, which is exactly the regression boundary needed here.

### `unittests/FEXLinuxTests`

This suite already cross-builds 64-bit and 32-bit guest executables with FEX's x86 toolchains and runs them through FEX. However, its current special thunk configuration is only applied to `thunk_testlib`, using `Data/CI/FEXLinuxTestsThunks.json`, which enables only `fex_thunk_test`.

It could host a Vulkan guest probe, but doing so cleanly would require a per-test Vulkan thunk configuration/environment path rather than treating all Linux tests as Vulkan-thunk tests.

### `unittests/ThunkLibs`

This suite is generator/ABI coverage (`generator.cpp`, `abi.cpp`). It does not provide an end-to-end runtime host-loader seam for Vulkan callback routing, so it is insufficient by itself for these bugs.

## Current main CI coverage gap

In `.github/workflows/ccpp.yml`, the build matrix is:

```yaml
arch: [[self-hosted, ARMv8.0], [self-hosted, ARMv8.2], [self-hosted, ARMv8.4]]
```

The thunk-functional steps are guarded by:

```yaml
if: ${{ steps.build.outcome == 'success' && matrix.arch[1] == 'x64' }}
```

No current matrix entry has `matrix.arch[1] == 'x64'`, so both `thunk_functional_tests_nothunks` and `thunk_functional_tests_thunks` are unreachable in this workflow as written.

A repository-wide search found `thunk_functional_tests_thunks` referenced only by its CMake target and this `ccpp.yml` workflow; there is no second workflow silently providing equivalent coverage.

Therefore adding a Vulkan regression only to `ThunkFunctionalTests` would not currently protect the main Build + Test workflow until the CI gate is repaired or the test is also wired into an active test path.

## Recommendation

For an upstream-quality regression:

- Add one small x86-64 Vulkan guest helper to `ThunkFunctionalTests` (or a nearby dedicated thunk-runtime test directory) that covers callback direct/GIPA routing, a native-null proc guard, and instance-pNext input preservation.
- Make the test skip cleanly when required Vulkan debug extensions/validation facilities are not available, but do not silently turn a configured Vulkan-capable CI machine into a pass on loader/thunk failure.
- Repair the dead `x64` condition or otherwise arrange for `thunk_functional_tests_thunks` to run on an active ARM64 self-hosted job with the expected Vulkan/display environment.
- Keep the full 760-name hosted differential as an investigation receipt / optional broad validation tool rather than normal per-commit CI unless maintainers explicitly want registry-wide loader parity testing.

No upstream workflow mutation has been made as part of this note.
