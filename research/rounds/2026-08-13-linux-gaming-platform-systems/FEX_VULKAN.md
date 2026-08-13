# FEX and Vulkan ecosystem additions

This companion note extends the Linux gaming/platform systems scout with cross-architecture execution and the core Khronos Vulkan tooling cluster.

## FEX

- `FEX-Emu/FEX` — x86/x86-64 execution on ARM64 Linux. Strong research seams include dynamic binary translation, JIT/code-cache lifetime, x86 memory-ordering emulation, signal behavior, syscall and ABI translation, host-library forwarding, OpenGL/Vulkan thunking, and Wine/Proton game compatibility.
- `FEX-Emu/RootFS` — supporting x86 root filesystem/runtime surface; useful when execution behavior crosses guest libraries, loaders, packaging, or runtime setup.

Potential Linux Fieldwork questions:

- guest/host syscall ABI differences, including architecture-sensitive interfaces;
- x86 TSO versus ARM memory ordering and the cost/correctness boundary of emulation;
- code-cache invalidation and self-modifying-code behavior;
- signal delivery and exception translation;
- graphics thunk equivalence between emulated and host-native paths;
- Wine/Proton regressions specific to cross-architecture execution;
- process, file-descriptor, mapping, and resource lifetime across translation boundaries.

## Khronos Vulkan cluster

- `KhronosGroup/Vulkan-Tools` — VulkanInfo, vkcube/vkcube++, Mock ICD, WSI and device/property enumeration.
- `KhronosGroup/Vulkan-ValidationLayers` — synchronization validation, GPU-assisted validation, state/object tracking, VUID coverage, extension semantics, and instrumentation.
- `KhronosGroup/Vulkan-Loader` — ICD and layer discovery, dispatch, configuration, environment handling, multi-driver behavior, and Linux platform integration.
- `KhronosGroup/Vulkan-Headers` — public API declarations generated from the registry and consumed throughout the Vulkan ecosystem.
- `KhronosGroup/Vulkan-Docs` — Vulkan specification and registry sources for contract tracing and extension semantics.
- `KhronosGroup/SPIRV-Tools` — SPIR-V validation, optimization and transformation.
- `KhronosGroup/glslang` — GLSL/HLSL compilation and SPIR-V generation.

Potential cross-project discriminators:

- specification versus loader versus validation-layer behavior;
- extension/version rollout mismatches across tools and drivers;
- WSI and device-enumeration differences across compositors and drivers;
- Mock ICD fidelity against real loader/tool expectations;
- synchronization cases accepted by one layer of the ecosystem and rejected by another;
- generated-header/registry changes whose consumers diverge;
- loader environment/configuration behavior under Flatpak, containers, multiple ICDs, or unusual driver layouts.

Keep broad orientation in this round. Promote only after exact current source and tests yield a bounded reproducible question with a concrete owner and consequence.
