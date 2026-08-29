# FEX Vulkan instance callbacks: copy the chain, not the guest

## In simple words

An x86 Vulkan program can give `vkCreateInstance` a linked list of optional records. Two of those records contain callback function pointers. On an ARM64 machine, a native Vulkan loader cannot call an x86 instruction address directly.

FEX already chooses to suppress these temporary debug callbacks. The old workaround did that by editing the application's linked list. That is wrong for a `const` input: the application may store the list on read-only pages.

The owned fork now makes a shallow host-owned copy when one of these callbacks is present:

```text
read-only x86 root -> report -> validation features -> utils
           │
           └── copy each record, relink the copies
                              │
                              ├── report callback = ARM64 dummy
                              └── utils callback  = ARM64 dummy
                                           │
                                           └── native vkCreateInstance
```

The exact ARM64 probe created an instance successfully, executed no guest callback, and left every byte of four separately protected guest pages unchanged. The change is merged in the owned FEX fork at `44e15cf5b6fd7bf9176d62a7560e33dd228428a8`.

## Current state

- State: `COMPLETE`
- Exact product candidate: `b0588b581c0245ad52329aaff08345821b1a542d`
- Merged owned-fork head: `44e15cf5b6fd7bf9176d62a7560e33dd228428a8`
- Latest authoritative gate: FEX Actions run `33266924365`, job `99138505363`
- Artifact: `9718992084`, digest `sha256:689dfec9535e9ca32b3f0d9afe3ad7cf924c0b489ebe24fcc3a9bd5c427454b4`
- First incomplete step: none for the bounded supported x86-64 debug-callback question
- Cleanup state: local probe binaries removed; duplicate run cancelled; disposable workflow registration still has to be retired after this receipt is published
- Next safe action: treat nested direct-driver callbacks and copied-chain allocation cleanup as separate measured questions
- External-contact state: no upstream contact authorized or created

## Intent and contract

The [Khronos `VkInstanceCreateInfo` reference](https://docs.vulkan.org/refpages/latest/refpages/source/VkInstanceCreateInfo.html) says its `pNext` list may contain `VkDebugReportCallbackCreateInfoEXT` and `VkDebugUtilsMessengerCreateInfoEXT`. Those callbacks receive events during instance creation and destruction. The [`vkCreateInstance` signature](https://docs.vulkan.org/refpages/latest/refpages/source/vkCreateInstance.html) receives a `const VkInstanceCreateInfo*`.

FEX's existing custom wrappers replace application debug callbacks with native dummy callbacks rather than building persistent x86-to-ARM callback bridges. This investigation preserves that policy. The question is where the replacement happens: guest storage is read-only input; host-owned copies are writable mediation state.

## Source

- Project: `teamleaderleo/FEX`, an owned experimental fork
- Upstream main observed at completion: `98964c552773b374676610776357a030a6825e53`
- Owned-fork base: `5dfbda3b8eb7a3460ace66fedb6bdb54389304d3`
- Candidate: `b0588b581c0245ad52329aaff08345821b1a542d`
- Merge: `44e15cf5b6fd7bf9176d62a7560e33dd228428a8`
- Pull request: [`teamleaderleo/FEX#12`](https://github.com/teamleaderleo/FEX/pull/12)
- Product source: `ThunkLibs/libvulkan/Host.cpp`
- Inventory guard: `unittests/ThunkLibs/vulkan_instance_pnext_copy_inventory.py`
- Local clone: `/home/leo/Projects/FEX`
- Exact investigation issue: [`teamleaderleo/linux-fieldwork#674`](https://github.com/teamleaderleo/linux-fieldwork/issues/674)

At completion, the owned fork was 46 commits ahead and zero behind the observed upstream main.

## What current main was doing

The supported x86-64 path classified `VkInstanceCreateInfo` as layout-compatible. Generated-code inspection showed a direct pointer wrapper rather than a private `repack_wrapper`:

```cpp
host_layout<const struct VkInstanceCreateInfo *> a_0 { args->a_0 };
```

That detail killed the first draft. Merely changing callback fields inside `Host.cpp` would still change guest memory. The generator's recently merged const-pointee fix protects pointees that actually take the repacking path; it does not turn every compatible pointer into a copy.

The old handwritten debug-report workaround also used `const_cast` to rewrite predecessor `pNext` links. Historical protected-input execution showed this can segfault before native Vulkan returns. The same loop did not handle the newer debug-utils creation callback.

## Candidate design

The surviving x86-64 path first scans for a debug-report or debug-utils record. When neither exists, it retains the existing direct call.

When either exists, it:

1. copies the root `VkInstanceCreateInfo`;
2. copies every structure currently allowed to extend that root in the pinned Vulkan XML;
3. relinks only the copies;
4. replaces `pfnCallback` and `pfnUserCallback` in their corresponding copies;
5. passes the copied root to native Vulkan.

The seven current extension types are:

- debug report callback;
- debug utils messenger;
- direct driver loading list;
- export Metal object request;
- layer settings;
- validation features;
- validation flags.

The data behind ordinary pointer members remains guest-addressable, matching the pre-existing compatible-layout path. A future unknown structure combined with debug callback mediation returns `VK_ERROR_INITIALIZATION_FAILED`; it does not guess a structure size or write the guest chain.

The x86-32 host library retains its prior code. Current FEX intentionally does not build a 32-bit Vulkan guest forwarding library, so its build is maintenance coverage rather than runtime acceptance.

## Fast local gates

The owned fork's focused development helper built only the affected libraries:

```sh
./Scripts/ResearchDevBuild.py --lane pnext-host-copy --source "$PWD" build vulkan-host-64 --jobs 8
./Scripts/ResearchDevBuild.py --lane pnext-host-copy --source "$PWD" build vulkan-host-32 --jobs 8

ctest --test-dir /home/leo/.cache/fex-dev/views/pnext-host-copy/build \
  --output-on-failure \
  -R '^(VulkanCustomRouteInventory|VulkanInstancePNextCopyInventory)\.ThunkGen$'
```

On Ubuntu 26.04.1 x86-64 (`big-red`), kernel `7.0.0-30-generic`, Clang 21.1.8, CMake 4.2.3, Ninja 1.13.2, and ccache 4.12.3:

| Gate | Result |
| --- | --- |
| `vulkan-host-64` after the surviving design | green, 6.46 s |
| `vulkan-host-32` maintenance compile | green, 41.75 s |
| route inventory | 12/12 x86-64 and 21/21 x86-32 |
| instance-chain inventory | 7 XML types / 7 copy cases |
| removed-validation-flags negative control | failed as 6/7 and named `VkValidationFlagsEXT` |
| both named CTest inventories | 2/2 green, 0.39 s |

These local receipts reported base `HEAD` plus a dirty source tree. They are developer feedback for the exact patch content, not immutable exact-head acceptance. The hosted run below is the clean exact-candidate result.

## Authoritative ARM64 result

Carrier commit `ad812bf454ae6cd25327d4fc1b48d3994cbed512` asserted that `ThunkLibs`, `FEXCore`, `Source`, and `unittests` had zero delta from candidate `b0588b581c0245ad52329aaff08345821b1a542d`.

The runner was `ubuntu-24.04-arm`, kernel `6.17.0-1022-azure`, AArch64. It built one FEX/Vulkan host-and-guest thunk pair and a minimal Ubuntu 24.04 amd64 rootfs. The probe put these values on four separate read-only pages:

```text
VkInstanceCreateInfo
  -> VkDebugReportCallbackCreateInfoEXT
  -> VkValidationFeaturesEXT
  -> VkDebugUtilsMessengerCreateInfoEXT
```

Native ARM64/Lavapipe plus the validation layer proved the temporary callback route was live:

```text
PROBE_AFTER_CREATE result=0 instance=... callbacks=0/1 unchanged=1
PROBE_RETURN callbacks=0/1 unchanged=1
```

The same x86 binary through FEX produced:

```text
PROBE_AFTER_CREATE result=0 instance=... callbacks=0/0 unchanged=1
PROBE_RETURN callbacks=0/0 unchanged=1
```

This establishes, for this exact chain and driver, successful instance creation, zero guest callback execution, and byte equality for the protected root and all three nodes.

## CI and evidence-path lessons

The first carrier run, `33266799900`, did not test the candidate. Its native classifier demanded both debug callback families fire in one mixed chain. Native created successfully, kept the chain unchanged, and delivered utils only (`0/1`), so the classifier stopped. Historical single-family evidence already establishes report reachability. The corrected oracle requires utils-positive/report-optional for this mixed chain and left the probe and product unchanged.

That first run also exposed Node 20 deprecation warnings from `actions/checkout@v4` and `actions/upload-artifact@v4`; the disposable carrier moved to v6 before the authoritative rerun.

GitHub registered the same branch-only workflow twice on the correction push. Run `33266924442` was cancelled before product build. It is not evidence.

Owned-fork PR #12 itself reported no checks and created zero inherited skipped matrices. The noisy skipped runs seen earlier predated the fork's already-merged manual-only CI policy.

## Evidence boundary and successors

Demonstrated:

- supported x86-64 FEX Vulkan;
- one current Vulkan XML/header inventory;
- one hosted Ubuntu ARM64/Lavapipe/validation-layer stack;
- a read-only mixed chain with a non-callback node between the two debug nodes;
- callback suppression and input byte equality during successful creation.

Not demonstrated:

- guest callback trampoline delivery;
- 32-bit guest Vulkan runtime;
- every legal non-callback node in runtime, although the XML-derived source guard covers all seven names;
- future Vulkan structure types;
- Apple/Venus or proprietary drivers;
- allocator callback mediation;
- a broad FEX suite.

`VkDirectDriverLoadingListLUNARG::pDrivers` leads to another structure containing a guest function pointer. Shallowly preserving that existing path does not make its callback host-callable; it needs a separate lifetime/bridge experiment.

The generic Vulkan repacker also deserves a bounded allocation-lifetime probe. Its `VkInstanceCreateInfo` custom exit does not visibly traverse/free copied `pNext` allocations. This candidate avoids that repacker and owns its copies with `std::vector`, so the possible leak is not part of this repair.

## Decision

The bounded read-only callback defect is repaired in the owned fork. Reopen this decision if the legal instance-chain inventory changes, a current supported 64-bit ABI stops being layout-compatible, a driver rejects a copied chain accepted by the original, or a guest write/callback appears under the same protected-input oracle.

No upstream issue, pull request, comment, review, or other contact was authorized or created.
