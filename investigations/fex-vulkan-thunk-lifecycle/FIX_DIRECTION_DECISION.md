# Fix-direction decision checkpoint

## Current preferred near-term direction

Keep the guest thunk wrappers that publish long-lived cross-ISA executable references resident for process lifetime with ELF `DF_1_NODELETE`.

The narrow static policy is currently the best first patch candidate:

```cmake
function(add_guest_lib NAME SONAME)
  cmake_parse_arguments(PARSE_ARGV 2 ARG "NODELETE" "" "")
  # ...
  if (ARG_NODELETE AND TARGET_TYPE STREQUAL "SHARED")
    target_link_options(${NAME}-guest PRIVATE "LINKER:-z,nodelete")
  endif()
endfunction()

add_guest_lib(vulkan "libvulkan.so.1" NODELETE)
add_guest_lib(wayland-client "libwayland-client.so.0.20.0" NODELETE)
add_guest_lib(GL "libGL.so.1" NODELETE)
add_guest_lib(cuda "libcuda.so.1" NODELETE)
```

A global `-z nodelete` inside `add_guest_lib()` remains an even smaller and more future-proof containment variant if maintainers prefer a single lifetime rule for all generated shared guest thunks.

## Why these wrappers are the current selective set

The source audit found the explicit long-lived guest executable-reference mechanisms in four wrappers:

- **Vulkan** — `vkGet*ProcAddr` calls `LinkAddressToFunction`; its guest `OnInit()` also publishes X11 guest callbacks/unpackers into the persistent host Vulkan side.
- **OpenGL** — `glXGetProcAddress` calls `LinkAddressToFunction`; `OnInit()` publishes guest malloc/X11 callbacks and unpackers.
- **CUDA** — `cuGetProcAddress` calls `LinkAddressToFunction` for dynamically returned native entrypoints.
- **Wayland client** — custom host-to-guest listener trampolines retain guest callback/unpacker dependencies.

The thunk README identifies ALSA as a non-callback example. EGL's `eglGetProcAddress` delegates to GL's proc-address implementation. No comparable persistent executable-reference mechanism was found in the current DRM or VDSO guest wrappers.

This makes the four-wrapper list a source-backed lifetime policy rather than a workload-specific Vulkan exception.

## Why NODELETE is the strongest containment mechanism

The observed defect is a lifetime asymmetry: FEX publishes native-facing references whose executable guest dependencies live in generated guest thunk DSOs, while the corresponding host thunk side persists for process lifetime.

NODELETE makes the relevant guest thunk lifetime match that persistent host side.

Evidence established so far:

- Real `vulkaninfo` pin/preload controls: keeping `libvulkan-guest.so` resident changes the teardown crash to exit 0.
- Synthetic full-pair normal unload: retained H→T and retained host→guest callback both SIGSEGV after guest thunk text is physically unmapped.
- Synthetic full-pair NODELETE: the same ordinary `dlclose()` keeps invoker/target/unpacker executable, and both retained H→T plus retained callback execute successfully immediately after close.
- Clean candidate real-Vulkan H→T test: a retained dynamic `vkEnumerateInstanceVersion` PFN still calls real ARM64 Lavapipe successfully after ordinary guest-side `dlclose()`.
- Real Vulkan X11 callback test: after guest Vulkan `dlclose()`, the persistent host X11 manager still invokes the retained guest `XSync` and `XDisplayString` trampoline path successfully.
- Real Vulkan static-state test: a *fresh* `vkGetInstanceProcAddr` lookup after `dlclose()` succeeds, proving the NODELETE wrapper's C++ proc-address state remains live rather than leaving resident text paired with destroyed globals.
- Native glibc contract test: constructors run once, intermediate `dlclose()` does not run destructors, `RTLD_NOLOAD` still finds the resident object, LOCAL→GLOBAL promotion works on reopen, and the destructor runs once at process exit.
- Every current 64-bit shared guest thunk builds under a global NODELETE policy, VDSO included.
- A real 32-bit Wayland guest thunk builds with `FLAGS_1: NOW NODELETE` under FEX's own 32-bit toolchain.
- Alternate lld/`ENABLE_CLANG_THUNKS` guest linking works with NODELETE.

NODELETE has no FEX core hot-path cost and removes physical wrapper-code reclamation from the affected lifetime problem.

## Selective static policy build proof

Owned-FEX run `31775612618`, job `94690326141`, artifact `9209783770`, workflow commit `100613e20ea79f02aa1c3bc3443f21b58b5ed54b` validated the option-style CMake policy above.

All current 64-bit shared guest thunks built successfully, with exactly this flag split:

```text
vulkan          NODELETE
GL              NODELETE
cuda            NODELETE
wayland-client  NODELETE
asound          normal
drm             normal
VDSO            normal
EGL             normal
SELECTIVE_64_OK
```

The same helper option built real 32-bit `wayland-client-guest` successfully:

```text
ELF 32-bit LSB shared object, Intel 80386
SONAME: libwayland-client.so.0.20.0
FLAGS_1: NOW NODELETE
SELECTIVE_32_OK
```

So a selective policy does not require per-target linker hacks and works across both guest bitnesses.

## Cost of the containment

NODELETE deliberately gives the selected wrappers process lifetime:

- wrapper mappings remain resident until process exit;
- intermediate `dlclose()` does not reclaim wrapper code/data;
- load constructors effectively become process-lifetime initialization;
- final destructor behavior moves to process teardown;
- resident memory increases by the selected guest wrappers actually loaded by the process.

Measured page-rounded PT_LOAD memory for the entire current 64-bit shared guest-thunk set is about **1.76 MiB**. Relevant members are approximately:

```text
vulkan          300 KiB
GL              956 KiB
cuda            188 KiB
wayland-client   40 KiB
```

Pinning only those four therefore retains roughly **1.45 MiB** of wrapper PT_LOAD mappings if all four are loaded. Dynamic allocations and dependent guest libraries have their own costs.

The source audit found guest load constructors centered on thunk glue initialization and no active guest-thunk unload-management design that depends on intermediate physical wrapper reclamation.

External application callback targets remain governed by their own lifetime; NODELETE protects generated wrapper code/unpackers and FEX-owned cross-ISA glue.

## Historical alignment with FEX loader behavior

Merged upstream PR `FEX-Emu/FEX#2583` moved XCB callback-thread cleanup away from a thunk-library destructor because the destructor could not be relied on when the shared library was removed.

During review, maintainers discussed hooking `dlclose()` manually. Sonicadvance1 explained that once FEX redirects the FD used to load a thunk library, FEX loses control of that point and no good workaround had been found.

A loader-enforced NODELETE policy works after that redirection and avoids needing to recover the missing unload interception point.

The dormant `libfex_malloc_loader` guest code also contains an explicit `RTLD_NODELETE` load, giving process-lifetime guest thunking conceptual precedent in the tree.

## `dlmopen` namespace caveat

A native glibc discriminator found one concrete semantic cost of a static ELF NODELETE flag:

```text
normal DSO:     40/40 LM_ID_NEWLM create/close cycles
NODELETE DSO:   fails at iteration 15 with "no more namespaces available"
```

NODELETE pins one object copy in each loader namespace, so disposable namespaces cannot be reclaimed normally.

A real FEX/Vulkan A/B test weakens the practical concern for this workload. Both the normal and NODELETE Vulkan guest wrappers completed 12 namespace cycles and then failed at the same earlier guest-glibc limit:

```text
/lib/x86_64-linux-gnu/libc.so.6: cannot allocate memory in static TLS block
```

The NODELETE variant therefore did not reduce the successful namespace count in that real FEX test. Its guest Vulkan copy moved to a different address in every namespace while the native PFN remained usable through all successful iterations.

This caveat still belongs in review because other guest workloads could have a different dependency/TLS profile.

## Base-namespace runtime promotion fallback

If maintainers want process lifetime for the ordinary application copy while preserving disposable `LM_ID_NEWLM` copies, glibc supports a more surgical mechanism.

A normal DSO without ELF NODELETE can, during load:

1. identify itself with `dladdr()`;
2. reopen itself with `RTLD_NOLOAD`;
3. read its namespace through `dlinfo(..., RTLD_DI_LMID, ...)`;
4. when `LM_ID_BASE`, reopen the existing object with `RTLD_NOLOAD | RTLD_NODELETE`.

This was proven on glibc **2.31, 2.35, and 2.39**. The base copy survives close, while NEWLM copies remain reclaimable; a native test recycled 40/40 disposable namespaces after promoting only the base copy.

This is technically cleaner around namespace lifetime, but it adds guest-side loader calls and libc/linkage compatibility work. It is therefore a refinement/fallback, not the first implementation choice.

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

## Decision hierarchy

For discussion, bring the choices in this order:

1. **Selective static NODELETE for Vulkan/GL/CUDA/Wayland** — current preferred patch candidate. Small implementation, zero runtime hot-path work, limits changed loader semantics to wrappers with source-backed persistent executable references.
2. **Global static NODELETE for every shared guest thunk** — simplest and most future-proof containment. Best if maintainers prefer one uniform thunk lifetime rule and accept the broader loader-semantic change.
3. **Base-namespace runtime NODELETE promotion** — proven refinement if `dlmopen` namespace reclamation is a blocking objection to static NODELETE.
4. **Target-cell + retirement/reclamation machinery** — use only if intermediate physical guest-thunk unloading is an explicit product requirement.

The independent Vulkan `VkAllocationCallbacks` SIGILL remains a separate bug and should stay out of the lifetime patch.

All code and CI work referenced here is on owned fork/investigation surfaces. No upstream FEX interaction occurred.
