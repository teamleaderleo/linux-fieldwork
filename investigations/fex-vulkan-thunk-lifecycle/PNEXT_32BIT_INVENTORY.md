# 32-bit Vulkan `pNext` inventory audit

## Purpose

Durable source-audit receipt for the 32-bit Vulkan structure repacking surface in FEX.

This audit exists because FEX's 32-bit Vulkan path has three manually synchronized pieces around `pNext` handling:

1. `libvulkan_interface.cpp` marks `Struct::pNext` members as `fexgen::custom_repack`;
2. `Host.cpp` provides matching custom-repack hook markers/implementations;
3. `Host.cpp` keeps a recursive `next_handlers` table that maps Vulkan `sType` values to concrete repackers.

A legal Vulkan chain node that reaches the recursive 32-bit translator without a matching `next_handlers` entry is rejected with `Unrecognized VkStructureType` and the process aborts. This makes missing handler coverage a concrete compatibility risk, but **a source-audit miss is not by itself a confirmed runtime bug**.

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

The v2 audit canonicalizes Vulkan XML struct aliases before comparing the three inventories. This matters because a first raw scan saw a false one-entry mismatch between `VkCopyMemoryToImageInfo` and `VkCopyMemoryToImageInfoEXT`; those are promotion/alias spellings of the same structure family.

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

So this is not evidence that the entire hand-maintained inventory is randomly drifting. The useful open surface is narrower: legal chain nodes that do not have recursive handler coverage, especially those with extra pointer/layout-sensitive members.

## Interpretation of the 282 missing handlers

Do **not** describe this as 282 confirmed FEX bugs.

The Vulkan XML registry describes legal structure relationships across core versions and many optional extensions. A node may be irrelevant to a particular driver, unsupported extension set, platform, or command path. Some entries also need more nuanced interpretation than a simple source scan can provide.

The audit is instead a ranked candidate generator. Runtime confirmation should require:

- the exact structure is legal in the parent chain;
- the native Vulkan driver accepts the same chain/data;
- the FEX 32-bit path reaches that command;
- failure is attributable to repacking/handler coverage rather than unsupported Vulkan functionality.

## First selected runtime candidate

`VkDeviceGroupDeviceCreateInfo` is the first candidate because it is unusually clean:

```text
provider: Vulkan 1.1 core / VK_KHR_device_group_creation
legal parent: VkDeviceCreateInfo
additional ABI-sensitive member: pPhysicalDevices
FEX interface pNext annotation: absent/commented
FEX Host custom-repack marker: absent/commented
recursive next_handlers entry: absent
```

It is preferable to a newer extension for initial proof because device groups have been core since Vulkan 1.1 and the test requires no window system.

The current same-driver ARM64 Lavapipe control already accepts the exact test chain and creates/destroys the device successfully:

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

That native control was recorded in hosted run `31788891680`. The first FEX runtime attempt did not execute the 32-bit guest because the harness initially selected FEX's GCC-mode `toolchain_x86_32.cmake` without installing its expected `x86_64-linux-gnu-gcc`; the 32-bit host Vulkan thunk itself built successfully. This is a harness/compiler-selection issue, not a product result.

A second run switches only the generated guest thunk build to FEX's explicit `ENABLE_CLANG_THUNKS=ON` mode; product source and the probe remain frozen.

## Likely fix shape if runtime confirms the defect

Do not apply this merely from the audit. If the baseline FEX run fails at the missing `sType` as expected, the likely implementation is small and uses existing FEX machinery:

1. enable `VkDeviceGroupDeviceCreateInfo::pNext` custom repacking in `libvulkan_interface.cpp`;
2. use a non-default Host repacker for `VkDeviceGroupDeviceCreateInfo`;
3. call the normal/default repacker, then translate the counted `pPhysicalDevices` dispatchable-handle array using the same `RepackStructArray<false>` pattern already used for other Vulkan handle arrays;
4. free that temporary array on repack exit;
5. add `VK_STRUCTURE_TYPE_DEVICE_GROUP_DEVICE_CREATE_INFO` / `VkDeviceGroupDeviceCreateInfo` to `next_handlers`;
6. rerun the same native/FEX probe as a baseline/candidate A/B.

## Nearby high-priority audit candidates

Other old/core pointer-bearing misses worth considering only after this first runtime result include:

- `VkFramebufferAttachmentsCreateInfo` — core 1.2 / imageless framebuffer;
- `VkPipelineCreationFeedbackCreateInfo` — core 1.3 / pipeline creation feedback;
- `VkSubpassDescriptionDepthStencilResolve` — core 1.2;
- `VkWriteDescriptorSetInlineUniformBlock` — core 1.3;
- `VkDeviceGroupBindSparseInfo` — core 1.1, though the simple source scan does not classify it as extra-pointer-sensitive.

There are also structures that have interface/Host annotations but no recursive handler entry. Those should be investigated separately: some may be intentionally top-level or otherwise special, while others may be genuine recursive-table omissions.

## Next step

Finish the exact 32-bit `VkDeviceGroupDeviceCreateInfo` FEX runtime baseline. Only if it demonstrates a product failure should this lane move from inventory/audit to a source candidate.