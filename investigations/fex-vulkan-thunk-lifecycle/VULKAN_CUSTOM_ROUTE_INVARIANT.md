# Vulkan custom-route inventory invariant

## Purpose

Finding A exposed a source-maintenance defect in addition to the runtime callback-routing defect: Vulkan custom host behavior has two independently maintained inventories.

1. `custom_host_impl` metadata in `ThunkLibs/libvulkan/libvulkan_interface.cpp` declares commands that require custom host implementations.
2. `LookupCustomVulkanFunction()` in `ThunkLibs/libvulkan/Host.cpp` manually chooses custom implementations for dynamically queried Vulkan function pointers.

Those inventories had drifted. This note records the separate prevention candidate that turns their equality into an executable test.

No upstream FEX state was changed.

## Internal prevention branch

```text
repository: teamleaderleo/FEX
base branch: fix/vulkan-callback-proc-routing
base candidate SHA: c011366706eaf65a00380003989b3a10811212b6
head branch: test/vulkan-custom-route-invariant-v2
head SHA: 275f6162178ebe65c7f44904bd1b1b784c3f836c
internal draft PR: teamleaderleo/FEX #2
```

Changes are limited to:

```text
unittests/ThunkLibs/vulkan_custom_route_inventory.py
unittests/ThunkLibs/CMakeLists.txt
```

The test is registered as:

```text
VulkanCustomRouteInventory.ThunkGen
```

and therefore participates in the existing `thunkgen_tests` CTest group.

## Direct source A/B

Workflow run:

```text
Actions run: 31776688975
artifact: 9210121093
artifact SHA-256: c944d8838858e8d6887c430058340f2eb7abc3f01458530aedc2925dc85f48b2
```

The test script is run against both the old exact product source and the repaired candidate.

Old product source `71afe476751deac24adabd1adb575fd2337b6e0a` is expected to fail:

```text
x86_64: custom_host_impl=12 lookup=9
  missing: vkCreateDebugReportCallbackEXT, vkCreateDebugUtilsMessengerEXT, vkDestroyDebugReportCallbackEXT

x86_32: custom_host_impl=21 lookup=18
  missing: vkCreateDebugReportCallbackEXT, vkCreateDebugUtilsMessengerEXT, vkDestroyDebugReportCallbackEXT
```

The repaired candidate inventory passes:

```text
x86_64: custom_host_impl=12 lookup=12
  missing: (none)
  lookup-only: (none)

x86_32: custom_host_impl=21 lookup=21
  missing: (none)
  lookup-only: (none)
```

This directly demonstrates that the test would have caught the exact source drift behind Finding A.

## Repository CTest validation

The test was also validated through FEX's actual top-level test tree rather than only by direct Python execution.

Final CTest workflow receipt:

```text
Actions run: 31777230787
job: 94695124136
workflow commit: f1adc4cef1a016e3f21b3322cc7674e67092e73e
prevention source: 275f6162178ebe65c7f44904bd1b1b784c3f836c
runner: ubuntu-24.04-arm
artifact: 9210357518
artifact SHA-256: 9e2df69be4d88dce9a801aaa73eb50e751c1e7f5737c3d4d4073d7384b97bf34
```

Top-level CMake was configured with `BUILD_TESTING=ON` and `BUILD_THUNKS=ON`. CTest discovered exactly the requested test:

```text
Test #4212: VulkanCustomRouteInventory.ThunkGen
Total Tests: 1
```

CTest then executed the source inventory check:

```text
x86_64: custom_host_impl=12 lookup=12
  missing: (none)
  lookup-only: (none)
x86_32: custom_host_impl=21 lookup=21
  missing: (none)
  lookup-only: (none)
1/1 Test #4212: VulkanCustomRouteInventory.ThunkGen ... Passed
100% tests passed, 0 tests failed out of 1
```

Two earlier CTest workflow attempts stopped before test execution for harness reasons: one used an x86-64 host that FEX top-level configure intentionally rejects, and one omitted NASM required by the existing test tree. The final ARM64+NASM run above is the authoritative CTest receipt.

## Scope

This prevention patch stays separate from the runtime repair in internal draft PR #1. The runtime candidate is independently demonstrated and should not acquire generator/test cleanup merely to combine work.

The prevention test is deliberately mechanical: for each thunk ABI mode it requires exact set equality between internal `custom_host_impl` function names and `LookupCustomVulkanFunction()` entries. If either side gains or loses a command without the other, the test fails and prints the missing or lookup-only names.
