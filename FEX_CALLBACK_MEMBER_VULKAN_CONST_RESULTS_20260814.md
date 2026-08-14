# FEX callback-member Vulkan + const regression receipts — 2026-08-14

This note preserves two completed lanes from the owned `teamleaderleo/FEX` fork.

## 1. All custom Vulkan allocator call sites forward generated callbacks

FEX branch: `ci/agent-b-vulkan-forward-all-allocators-20260814`
Head used by run: `669220a85abf80e34599696dbf102788956e726b`
Workflow run: `31793452808` (success)
Artifact: `9216519589` (`agent-b-vulkan-forward-all-allocators-31793452808`)

The research patch forwards already-repacked `VkAllocationCallbacks*` parameters through the custom native call sites that previously hard-coded `nullptr`:

- `vkCreateShaderModule`
- `vkCreateInstance`
- `vkCreateDevice`
- `vkAllocateMemory`
- `vkFreeMemory`
- `vkCreateDebugReportCallbackEXT`
- `vkDestroyDebugReportCallbackEXT`
- `vkCreateDebugUtilsMessengerEXT`

Generated bridge receipts remained consistent:

- normal callback signatures: 480
- resident bridge callback signatures: 480
- ordinary `libvulkan-guest.so`: unloadable; `NEEDED libfex-vulkan-bridge.so`
- `libfex-vulkan-bridge.so`: `DF_1_NODELETE`

ARM64 standard custom-host runtime matrix:

```text
DEVICE_CREATE_RETURN result=0 alloc_delta=2 free_delta=0
MEM_ALLOC_RETURN result=0 alloc_delta=1 free_delta=0
MEM_FREE_RETURN free_delta=1
SHADER_CREATE_RETURN result=0 alloc_delta=1 free_delta=0
SHADER_DESTROY_RETURN free_delta=1
DEVICE_DESTROY_RETURN free_delta=2 totals=4/0/4
PASS custom-host allocator forwarding matrix
```

Final receipt:

```text
native=0
generated_custom_host_matrix=0
OUTCOME=all_standard_custom_vulkan_allocator_sites_forward_generated_callbacks
```

Observed conclusion: the generated `callback_member` conversion is usable across Vulkan custom host implementations; those implementations do not need allocator-specific trampoline code. Their remaining responsibility is to forward the repacked allocator argument rather than discard it. Extension-specific sites were compile/call-site proved in this lane; the hosted ICD did not supply equivalent runtime coverage for every extension entrypoint.

## 2. Const-pointee thunkgen correction has zero regression delta versus exact parent

FEX branch: `ci/thunkgen-const-pointee-unit-20260814`
Semantic candidate: `715ff36bff2fd9f2353ab31613dc41ae106f3938`
Exact parent: `71afe476751deac24adabd1adb575fd2337b6e0a`
Candidate comparison run: `31793742608`
Candidate artifact: `9216592294`
Exact-parent baseline run: `31794090739` (success comparator)
Baseline artifact: `9216731040`

Focused `StructRepacking` regression adds a `const A*` parameter with a custom-repacked member and asserts that emitted `make_repack_wrapper<...>` retains both `A` and `const`. The focused test passes for both x86-32 and x86-64 generation.

The complete thunkgen suite on the candidate reports 73% passing with exactly four failures:

- `MultipleParameters.ThunkGen`
- `DataLayoutPointers.ThunkGen`
- `DataLayout.ThunkGen`
- `Mapping guest integers to fixed-size.ThunkGen`

The exact parent reports the same four failed test names. The parent comparator also confirms `StructRepacking.ThunkGen` passes.

Observed conclusion: preserving original guest pointee constness in the emitted repack wrapper introduces no additional thunkgen-suite failures relative to its exact parent. The four hosted-suite failures are pre-existing in that parent (including 32-bit header/tooling environment failures and existing matcher discrepancies), so they are not evidence against the const-pointee correction.

## Design consequence

For callback-bearing const input records such as `VkAllocationCallbacks`, thunkgen must preserve the guest pointee's `const` qualification through repack-wrapper generation. This prevents exit repacking from treating caller-owned const input as writable. The generated callback-member lane additionally uses a guest-side temporary copy for callback substitution, so callback pointer replacement itself does not mutate caller memory.
