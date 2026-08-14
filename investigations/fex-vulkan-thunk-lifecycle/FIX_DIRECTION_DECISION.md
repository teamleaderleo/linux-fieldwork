# Fix-direction decision checkpoint

## Current preferred near-term direction

Keep generated shared guest thunk wrappers resident for process lifetime with ELF `DF_1_NODELETE`.

Candidate build policy:

```cmake
if (TARGET_TYPE STREQUAL "SHARED")
  target_link_options(${NAME}-guest PRIVATE "LINKER:-z,nodelete")
endif()
```

This policy belongs in the existing `add_guest_lib()` helper, where shared guest thunk DSOs are created.

## Why this is currently the strongest candidate

The observed defect is a lifetime asymmetry: FEX publishes native-facing references whose executable guest dependencies live in generated guest thunk DSOs, while the corresponding host thunk side persists for process lifetime.

NODELETE makes the guest thunk lifetime match that persistent host side.

Evidence already established:

- Real `vulkaninfo` pin/preload controls: keeping `libvulkan-guest.so` resident changes the teardown crash to exit 0.
- Synthetic full-pair normal unload: retained H→T and retained host→guest callback both SIGSEGV after guest thunk text is physically unmapped.
- Synthetic full-pair NODELETE: the same ordinary `dlclose()` keeps invoker/target/unpacker executable, and both retained H→T plus retained callback execute successfully immediately after close.
- Real generated Vulkan/GL/Wayland/CUDA wrappers build with their normal SONAME plus `FLAGS_1: NODELETE`.
- Every current 64-bit shared guest thunk target builds under the generic policy, VDSO included.
- A real 32-bit Wayland guest thunk builds under FEX's own `-m32` toolchain with `FLAGS_1: NOW NODELETE`.
- Clean candidate branch real-Vulkan test: a retained dynamic `vkEnumerateInstanceVersion` PFN still calls real ARM64 Lavapipe successfully after ordinary guest-side `dlclose()`.

NODELETE has no FEX core hot-path cost and removes physical wrapper-code reclamation from the problem entirely.

## Cost of the containment

The policy deliberately gives generated guest thunk wrappers process lifetime:

- wrapper mappings remain resident until process exit;
- intermediate `dlclose()` does not reclaim wrapper code/data;
- load constructors effectively become process-lifetime initialization;
- final unload/destructor behavior moves to process teardown;
- resident memory increases by the guest thunk wrapper set actually loaded by the process.

The source audit found guest load constructors centered on thunk glue initialization (Vulkan/GL X11 bridges, Wayland mirror/interface setup) and no active guest-thunk unload-management design that depends on intermediate physical wrapper reclamation.

External application callback targets remain governed by their own lifetime; NODELETE specifically protects generated wrapper code/unpackers and FEX-owned cross-ISA glue.

## Unload-preserving alternative

If reclaiming guest thunk DSOs during process lifetime is a hard requirement, the investigation has already established a viable H→T state model:

```text
H -> T(gen1)
H -> empty       # pre-unmap retirement
H -> T(gen2)     # later generation publication
```

A generation-neutral compiled H block can load T from a stable target cell, so generation handoff needs no handler replacement or L1/L2/L3 invalidation.

That alternative still needs several correctness mechanisms before it is product-ready:

1. peer execution quiescence for a thread that selected old T just before retirement;
2. rollback when physical `munmap` fails after target retirement;
3. stable host→guest callback state keyed by logical callback identity;
4. callback retirement keyed by both guest target and guest unpacker;
5. a grace-period/lease design with acceptable overhead for Vulkan/GL/CUDA dynamic entrypoint hot paths.

The first shared-counter/call-return lease prototype compiled but hung on the initial thunk call. A per-thread hazard/grace-period scheme remains a possible lower-contention design, but it is larger core work.

## Decision boundary

Use NODELETE as the near-term containment candidate unless preserving intermediate physical guest-thunk unload is an explicit product requirement.

Keep the target-cell/retirement work as the long-term unload-preserving design reference. It has strong causality evidence and a clean generation state machine, but its reclamation protocol remains unfinished.

The independent Vulkan `VkAllocationCallbacks` SIGILL remains a separate bug and should not be folded into either lifetime repair.

All code and CI work referenced here is on owned fork/investigation surfaces. No upstream FEX interaction occurred.
