# 32-bit Vulkan `pNext` inventory audit

## Purpose

Durable source-audit receipt for the 32-bit Vulkan structure repacking surface in FEX.

This audit exists because FEX keeps substantial 32-bit Vulkan host-side repacking code even though the current build intentionally does **not** produce a 32-bit Vulkan guest thunk. The repacking code is therefore best treated as dormant/future-support maintenance coverage, not as a currently user-reachable Vulkan runtime surface.

The host-side machinery has three manually synchronized pieces around `pNext` handling:

1. `libvulkan_interface.cpp` marks `Struct::pNext` members as `fexgen::custom_repack`;
2. `Host.cpp` provides matching custom-repack hook markers/implementations;
3. `Host.cpp` keeps a recursive `next_handlers` table that maps Vulkan `sType` values to concrete repackers.

If this 32-bit forwarding path is re-enabled, a legal Vulkan chain node that reaches the recursive translator without a matching `next_handlers` entry is rejected with `Unrecognized VkStructureType` and the process aborts. Missing handler coverage is therefore useful future-enablement debt, but **a source-audit miss is not by itself a confirmed current FEX runtime bug**.

## Exact source and audit receipt

```text
FEX candidate: c011366706eaf65a00380003989b3a10811212b6
owned-fork audit workflow commit: ab867272484afe43284858086780cf2d8a4442f5
Actions run: 31789230152
job: 94732114163
artifact: 9214771281
artifact SHA-256: cc450dc959ced149656ceda4e52b9046c7df00f7f4eeef3610a13faf17d536a6
Vulkan-Headers submodule: 450bd2232225d6c7728a4108055ac2e37cef6475
```

The v2 audit canonicalizes Vulkan XML struct aliases before comparing the inventories. This matters because the first raw scan saw a false one-entry mismatch between `VkCopyMemoryToImageInfo` and `VkCopyMemoryToImageInfoEXT`; those are promotion/alias spellings of the same structure family.

## Current support status

Historical upstream context explains the apparently half-wired build graph.

PR #3487, `Library Forwarding: Add experimental support for 32-bit Vulkan`, was merged on 2025-03-12. Its final commit was:

```text
8ffc6fbc6b2caadc1bdd59f2628dcab4f9aa34f2
LibraryForwarding/vulkan: Disable 32-bit guest library
```

The commit message states that the guest library did not export enough symbols to be viable for practical use and was therefore disabled. It explicitly says the 32-bit **host** library should continue to build so the relevant features continue to compile/work at that layer.

The patch moved Vulkan guest generation back inside:

```cmake
if (BITNESS EQUAL 64)
  generate(libvulkan ...)
  ...
  add_guest_lib(vulkan "libvulkan.so.1")
endif()
```

Current `c0113667...` still has that arrangement. A standalone `BITNESS=32` GuestLibs build therefore has no `vulkan-guest` target by design, while the top-level FEX build still exposes and successfully builds `vulkan-host-32`.

This is the key interpretation boundary for the rest of this note: the inventory audits code that is intentionally kept compiling for future/experimental 32-bit Vulkan forwarding, but current FEX does not ship the matching 32-bit guest Vulkan forwarding library.

## Canonicalized counts

```text
raw_header_pnext_structs:                  1045
canonical_header_pnext_structs:            1045
canonical_legal_extension_nodes:            688
canonical_top_level_roots:                  357
raw_interface_annotations:                  902
canonical_interface_annotations:            902
raw_host_hooks:                              902
canonical_host_hooks:                        902
raw_recursive_handlers:                      406
canonical_recursive_handlers:                406
canonical_annotation_only:                     0
canonical_host_only:                           0
canonical_missing_legal_handlers:            282
canonical_missing_handler_pointer_risk:       81
canonical_orphan_handlers:                     0
canonical_missing_annotations:               143
```

The strongest synchronization result is:

```text
interface annotations <-> Host hook markers: exact after alias canonicalization
annotation-only: 0
host-only: 0
recursive handlers not recognized as legal extension nodes: 0
```

So this is not evidence that the whole hand-maintained inventory is randomly drifting.

## Split of the 282 missing recursive handlers

The artifact was further classified by whether a missing recursive node already has interface/Host repack support:

```text
222  have both interface annotation + Host repacker, but no next_handlers entry
 60  have neither interface annotation nor Host repacker
```

For the 81 entries with additional pointer/ABI-sensitive members:

```text
22  are handler-table-only gaps
59  are full repack gaps
```

This is a much more useful maintenance picture than the raw 282 count. Most missing recursive nodes already have a repacker and would primarily need a decision about recursive legality/dispatch-table coverage. A smaller set would require actual new 32-bit repack implementation.

## Old/core pointer-bearing full gaps

Only five canonical missing-handler entries in the audit are simultaneously:

- provided by a core Vulkan version;
- pointer/ABI-sensitive by the simple source scan; and
- missing both interface annotation and Host repack support.

They are:

```text
VkDeviceGroupDeviceCreateInfo             core 1.1
VkFramebufferAttachmentsCreateInfo        core 1.2
VkPipelineCreationFeedbackCreateInfo      core 1.3
VkSubpassDescriptionDepthStencilResolve   core 1.2
VkWriteDescriptorSetInlineUniformBlock    core 1.3
```

These are reasonable future-enablement candidates if 32-bit Vulkan forwarding is revived.

## `VkDeviceGroupDeviceCreateInfo` investigation

This was selected first because it is unusually clean:

```text
provider: Vulkan 1.1 core / VK_KHR_device_group_creation
legal parent: VkDeviceCreateInfo
additional ABI-sensitive member: pPhysicalDevices
FEX interface pNext annotation: absent/commented
FEX interface pPhysicalDevices annotation: absent
FEX Host custom-repack marker: absent/commented
recursive next_handlers entry: absent
```

The counted `pPhysicalDevices` member is an array of dispatchable handles. Existing FEX code explicitly custom-repacks analogous arrays such as `VkSubmitInfo::pCommandBuffers` using `RepackStructArray<false>` because dispatchable handles change width between 32-bit guest and 64-bit host.

A same-driver ARM64 Lavapipe control accepts the exact proposed chain and creates/destroys the device successfully:

```text
CREATE_INSTANCE=0
PNEXT_AFTER_INSTANCE
PNEXT_BEFORE_CREATE_DEVICE group_stype=1000070001 count=1
CREATE_DEVICE=0
PNEXT_AFTER_CREATE_DEVICE
PNEXT_CLEANUP_DONE
PNEXT_RETURN
native exit=0
```

This control was recorded in hosted run `31788891680`.

### Attempted FEX runtime repro

The first hosted attempt established that:

- `vulkan-host-32` exists and builds successfully on ARM64;
- the native control succeeds;
- the initial guest CMake failure was only a harness compiler-selection issue.

A second run (`31789474866`) switched the standalone 32-bit GuestLibs build to FEX's explicit Clang-thunk mode. CMake configured cleanly with Clang 18, proving the cross-compile setup itself was valid, but Ninja then reported:

```text
ninja: error: unknown target 'vulkan-guest'
```

Reading current `ThunkLibs/GuestLibs/CMakeLists.txt` and the historical disabling commit confirms this is intentional, not another harness problem: the 32-bit Vulkan guest target does not exist by design.

Therefore the runtime repro is **retired**. Do not locally re-enable/build an unsupported guest Vulkan library merely to manufacture a runtime failure. The source audit is sufficient for its intended maintenance purpose until 32-bit Vulkan guest forwarding is officially revived.

## Likely implementation shape if support is revived

Do not apply this to current product merely from the audit. If maintainers intentionally re-enable the 32-bit Vulkan guest library, `VkDeviceGroupDeviceCreateInfo` would likely need four coordinated pieces using existing FEX machinery:

1. enable `VkDeviceGroupDeviceCreateInfo::pNext` custom repacking in `libvulkan_interface.cpp`;
2. add a `VkDeviceGroupDeviceCreateInfo::pPhysicalDevices` custom-repack annotation because it is a counted dispatchable-handle array;
3. use a non-default Host repacker that first performs normal/pNext repacking, then translates `pPhysicalDevices` with the existing `RepackStructArray<false>` pattern and frees the temporary array on exit;
4. add `VK_STRUCTURE_TYPE_DEVICE_GROUP_DEVICE_CREATE_INFO` / `VkDeviceGroupDeviceCreateInfo` to `next_handlers`.

The native control above can be retained as a future regression oracle.

## What this lane established

- The 32-bit Vulkan Host repacker is intentionally compiled even though the guest Vulkan forwarding library is intentionally disabled.
- Interface annotation and Host repacker inventories are synchronized after Vulkan alias canonicalization.
- The recursive `next_handlers` inventory is substantially smaller than the XML-legal chain-node set.
- Most recursive misses (222/282) already have repackers; 60 are full repack gaps.
- Only five old/core candidates are both full gaps and pointer/ABI-sensitive by the current simple scan.
- `VkDeviceGroupDeviceCreateInfo` is a clean future-enablement candidate, but it is **not a current user-facing repro** because current FEX does not build the 32-bit Vulkan guest library.

## Next step

Do not spend more hosted runtime cycles on 32-bit Vulkan unless the guest forwarding path is intentionally re-enabled. Keep this inventory as durable future work and return current investigation effort to supported/current Vulkan surfaces or other open items in issue #674.