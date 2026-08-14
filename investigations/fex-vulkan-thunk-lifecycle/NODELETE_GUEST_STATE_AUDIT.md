# Shared guest-thunk state audit for blanket NODELETE

## Question

The current near-term lifetime candidate marks every shared generated guest thunk built by `add_guest_lib()` with ELF `DF_1_NODELETE`.

That is coherent only if keeping the guest wrapper image and its wrapper-owned static state alive across logical `dlclose()` does not contradict an existing guest-thunk reset contract.

This pass reviews every current shared guest target created by `ThunkLibs/GuestLibs/CMakeLists.txt` at exact FEX source `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`.

Source list:
https://redirect.github.com/FEX-Emu/FEX/blob/f3ab82a73fb48271ee12a882c98bc5d823a2b4d1/ThunkLibs/GuestLibs/CMakeLists.txt

Current shared targets are:

- `asound` (64-bit only)
- `vulkan` (64-bit only)
- `drm` (64-bit only)
- `wayland-client`
- `VDSO`
- `GL`
- `EGL`
- `cuda`

The test-only `fex_thunk_test` target is excluded from product policy analysis.

## Result

No reviewed product guest thunk establishes an intermediate physical-unload/reset requirement.

No product guest target reviewed here contains an explicit guest-side destructor or thread-local wrapper state whose correctness depends on `dlclose()` physically destroying and reconstructing the wrapper image.

The stateful targets instead contain process-oriented bridge state whose addresses or initialized objects are consumed by host state that already persists independently of guest `dlclose()`.

## Per-target review

### ALSA

`ThunkLibs/libasound/libasound_Guest.cpp` is generated glue plus `LOAD_LIB(libasound)`.

It has no handwritten wrapper state to reset.

Source:
https://redirect.github.com/FEX-Emu/FEX/blob/f3ab82a73fb48271ee12a882c98bc5d823a2b4d1/ThunkLibs/libasound/libasound_Guest.cpp

### Vulkan

`ThunkLibs/libvulkan/Guest.cpp` contains:

- a process-static `HostPtrInvokers` map from Vulkan command names to guest call adapters;
- `vkGetInstanceProcAddr` / `vkGetDeviceProcAddr` bridge publication through `LinkAddressToFunction`;
- `OnInit()` publication of guest `XSync`, `XGetVisualInfo`, and `XDisplayString` callback addresses plus their generated callback unpackers to the host thunk.

Those published unpacker/caller addresses are exactly the class that becomes stale if the guest wrapper physically disappears while the host thunk persists. Keeping the wrapper image resident preserves the state already referenced by persistent host metadata.

Source:
https://redirect.github.com/FEX-Emu/FEX/blob/f3ab82a73fb48271ee12a882c98bc5d823a2b4d1/ThunkLibs/libvulkan/Guest.cpp

### DRM

`ThunkLibs/libdrm/Guest.cpp` contains per-call allocation/string ownership shims and `LOAD_LIB(libdrm)`.

The handwritten code does not keep process-static mutable wrapper state. Allocations returned to applications remain governed by the application's object lifetime, not by a wrapper-destructor reset path.

Source:
https://redirect.github.com/FEX-Emu/FEX/blob/f3ab82a73fb48271ee12a882c98bc5d823a2b4d1/ThunkLibs/libdrm/Guest.cpp

### Wayland client

`ThunkLibs/libwayland-client/Guest.cpp` contains the strongest non-Vulkan persistent guest state in the current set:

- exported `wl_interface` objects are defined in the guest wrapper and late-filled in `OnInit()` from persistent host-side interface metadata;
- host-callable listener trampoline tables are allocated per `wl_proxy` and are explicitly freed/replaced by the proxy wrapper path;
- `LOAD_LIB_INIT(libwayland-client, OnInit)` performs the one-time interface exchange.

The per-proxy listener table lifetime is tied to proxy operations, not DSO finalization. The wrapper-level interface objects are process-facing bridge metadata; keeping them resident matches the host thunk that supplied their initialized contents.

Physical guest-only unload/reload would instead reconstruct just one side of that interface exchange while host thunk state remained alive.

Source:
https://redirect.github.com/FEX-Emu/FEX/blob/f3ab82a73fb48271ee12a882c98bc5d823a2b4d1/ThunkLibs/libwayland-client/Guest.cpp

### VDSO

`ThunkLibs/libVDSO/libVDSO_Guest.cpp` is aliases/naked bridge entrypoints plus generated glue. It has no handwritten mutable process state or unload reset path.

VDSO lookup is already special in the build helper: it is found by SONAME / `RTLD_NOLOAD` semantics rather than ordinary filesystem reload. Process residency is therefore not in tension with an existing ordinary unload contract.

Source:
https://redirect.github.com/FEX-Emu/FEX/blob/f3ab82a73fb48271ee12a882c98bc5d823a2b4d1/ThunkLibs/libVDSO/libVDSO_Guest.cpp

### GL

`ThunkLibs/libGL/libGL_Guest.cpp` contains:

- a process-static `HostPtrInvokers` proc-address adapter map;
- `glXGetProcAddress` publication through `LinkAddressToFunction`;
- `OnInit()` publication of guest malloc plus X11 callback functions and generated unpackers to persistent host GL state.

This mirrors Vulkan's lifetime shape. The wrapper owns executable adapter/unpacker addresses that host-side thunk state can retain. NODELETE keeps those published addresses valid rather than introducing a guest-only generation reset.

Source:
https://redirect.github.com/FEX-Emu/FEX/blob/f3ab82a73fb48271ee12a882c98bc5d823a2b4d1/ThunkLibs/libGL/libGL_Guest.cpp

### EGL

`ThunkLibs/libEGL/libEGL_Guest.cpp` has no independent proc-address bridge state: `eglGetProcAddress` delegates to the GL thunk, and the target is linked against `GL-guest`.

With the blanket policy, both sides of that guest dependency remain resident together. No EGL wrapper-destructor reset contract was found.

Source:
https://redirect.github.com/FEX-Emu/FEX/blob/f3ab82a73fb48271ee12a882c98bc5d823a2b4d1/ThunkLibs/libEGL/libEGL_Guest.cpp

### CUDA

`ThunkLibs/libcuda/libcuda_Guest.cpp` contains:

- a process-static `HostPtrInvokers` map;
- a static proc-address override table;
- dynamic `cuGetProcAddress_v2` publication through `LinkAddressToFunction`;
- `LOAD_LIB(libcuda)`.

Like Vulkan and GL, physically reclaiming only the guest wrapper would invalidate executable adapters while persistent FEX bridge state could still reference them. NODELETE preserves those guest adapters for the same process lifetime as the host thunk.

Source:
https://redirect.github.com/FEX-Emu/FEX/blob/f3ab82a73fb48271ee12a882c98bc5d823a2b4d1/ThunkLibs/libcuda/libcuda_Guest.cpp

## Search-level negative controls

A current-source search for `thread_local` returned no `ThunkLibs` guest-wrapper hit.

A current-source search for `destructor` returned no `ThunkLibs` guest-wrapper destructor implementation.

The one explicit constructor-oriented special case found in `libfex_malloc_loader` already performs its own `dlopen(..., RTLD_NODELETE, ...)`; that loader is disabled from the current product `add_guest_lib()` set and does not argue for intermediate physical teardown.

Source:
https://redirect.github.com/FEX-Emu/FEX/blob/f3ab82a73fb48271ee12a882c98bc5d823a2b4d1/ThunkLibs/libfex_malloc_loader/Guest.cpp

## glibc NODELETE lifecycle semantics

A direct glibc loader-source cross-check removes an ambiguity in the phrase "the wrapper stays mapped."

In glibc's NODELETE handling, a `DF_1_NODELETE` object's pending NODELETE status is promoted to active in the final stages of `dlopen`, before ELF constructors are called. In `_dl_close`, an active NODELETE map is rejected from removal immediately: the close path unlocks and returns instead of entering the normal object-removal/destructor walk.

Primary glibc source/history reference:
https://sourceware.org/pipermail/glibc-cvs/2019q4/068278.html
(commit `f8ed116aa574435c6e28260f21963233682d3b57`)

For this candidate that means an intermediate logical `dlclose()` is not "guest finalizers ran but executable pages happened to remain." The constructor-created guest thunk generation remains active as one loader generation. This matches the real Vulkan NODELETE receipt where the same guest wrapper address remains mapped after close and the retained PFN remains callable.

The distinction matters for stateful wrappers such as Vulkan, GL, CUDA, and Wayland: their one-time constructor/`OnInit()` state is retained along with the code addresses it published, instead of being destructed underneath persistent FEX host-side bridge state.

Process-exit finalization remains a separate boundary and should still be covered by ordinary shutdown tests; this audit only establishes the semantics of intermediate `dlclose()` under active NODELETE.

## Conclusion

The per-target source audit did not find a product guest-thunk state-reset requirement that contradicts blanket shared-wrapper NODELETE.

For the three major dynamic-proc-address wrappers—Vulkan, GL, and CUDA—process residency is positively aligned with their current implementation because executable guest adapter state is intentionally published into longer-lived FEX state. Wayland likewise owns wrapper-resident interface metadata initialized from persistent host state.

The glibc loader cross-check strengthens that interpretation: active NODELETE prevents the intermediate unload/finalizer path rather than merely preserving executable mappings after wrapper state has been torn down.

This does **not** prove that no external application depends on a thunk mapping physically disappearing after `dlclose()`, and it does not quantify dependency/RSS overhead. Those remain the two most meaningful policy risks to test.

The mapped wrapper footprint has now been measured separately in `NODELETE_BUILD_MATRIX.md`: all eight current 64-bit wrapper DSOs sum to about 1.69 MiB of ELF `PT_LOAD` memory before dependency/RSS effects.

The next adversarial checks for blanket NODELETE should therefore focus on:

1. the real repeated close/reopen stress currently exercising Vulkan dynamic PFN identity and calls across many handle cycles;
2. runtime RSS/PSS and transitive dependency retention if memory cost becomes a practical concern;
3. any concrete application that probes mapping disappearance or expects wrapper static state to reset.

All mutation and CI execution remains confined to owned repositories/forks. Upstream FEX was read-only.