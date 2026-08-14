# NODELETE guest-thunk lifetime containment

## Motivation

The lifetime failure has a simple loader-level containment candidate: keep generated guest thunk DSOs resident for the process, matching the effective process lifetime of their host thunk DSOs.

This prevents FEX-owned native pointers and generated host trampolines from outliving the guest invokers/unpackers they reference. It also removes the selected-code-versus-unmap race because the guest thunk text is never physically reclaimed during process lifetime.

GNU `-z nodelete` encodes this policy in the DSO as `DF_1_NODELETE` / `FLAGS_1: NODELETE`.

## Synthetic full-pair mapping result

Owned-FEX branch `ci/agent-k-arm64-20260814` builds the retained full thunk pair twice:

- normal guest DSO with no NODELETE flag;
- identical guest DSO linked with `-Wl,-z,nodelete` and verified by `readelf`.

Hosted ARM64 run `31771126183`, job `94677128018`, artifact `9208226923` uses pristine FEX core code.

The normal DSO is physically unmapped by ordinary `dlclose()`:

```text
old invoker after dlclose          0x00007ffff7da21b0 -> unmapped
old target after dlclose           0x00007ffff7da2170 -> unmapped
old unpacker after dlclose         0x00007ffff7da2190 -> unmapped
```

The NODELETE DSO stays executable-mapped after the same ordinary `dlclose()`:

```text
old invoker after dlclose          0x00007ffff7da21b0 -> ... r-xp .../nodelete/guest/liblifetime-guest.so
old target after dlclose           0x00007ffff7da2170 -> ... r-xp .../nodelete/guest/liblifetime-guest.so
old unpacker after dlclose         0x00007ffff7da2190 -> ... r-xp .../nodelete/guest/liblifetime-guest.so
```

The fixture normally treats surviving guest executable mappings as a failure because its unload mode is designed to prove physical reclamation. A follow-up carrier is therefore being used to accept expected NODELETE survival and continue into the retained H→T and host→guest callback call probes.

## Real generated Vulkan guest wrapper build

Owned-FEX branch `ci/agent-m-arm64-20260814`, commit `333be356c29994499478bd5494e2da0516ca22c9`.

Hosted ARM64 run `31771633918`, job `94678611157`, artifact `9208362750`.

The diagnostic changes only the generic guest-thunk CMake helper:

```cmake
if (TARGET_TYPE STREQUAL "SHARED")
  target_link_options(${NAME}-guest PRIVATE "LINKER:-z,nodelete")
endif()
```

FEX's real thunk generator then successfully builds the actual 64-bit x86 Vulkan guest wrapper. The result remains a normal generated FEX Vulkan wrapper:

```text
ELF 64-bit LSB shared object, x86-64
SONAME: libvulkan.so.1
FLAGS_1: NODELETE
REAL_VULKAN_GUEST_NODELETE_OK
```

This proves the generic lifetime policy is compatible with the real Vulkan guest thunk generator, generated linker inputs, and SONAME override. It is not limited to the synthetic DSO.

## Existing real-workload control

The earlier real `vulkaninfo` investigation already showed that retaining one guest loader reference for `libvulkan-guest.so` changes the teardown result from the crashing unload path to exit 0. NODELETE is a loader-level way to encode the same lifetime policy directly in the generated guest wrapper rather than relying on an external preload/reference holder.

## Tradeoffs

A NODELETE policy intentionally changes guest thunk wrapper lifetime semantics:

- wrapper code and data remain resident until process exit;
- intermediate `dlclose()` no longer performs physical DSO reclamation;
- constructor/destructor and repeated-load behavior follow a process-lifetime wrapper model;
- memory use increases by the resident guest thunk DSOs.

Those costs should be evaluated against the existing host side, whose thunk DSOs are already retained for process lifetime and whose hidden cross-ISA references can otherwise survive guest-wrapper unload.

The policy can be applied centrally in `add_guest_lib()`, covering generated shared guest thunks in one place. A full-policy test should still cover representative Vulkan, OpenGL, Wayland, CUDA, and 32-bit wrappers.

## Relation to the unload-preserving design

NODELETE is containment, not the same design as target-cell retirement. The unload-preserving path has separately proven generation-neutral H target cells and pre-unmap T→empty→new-T publication, but still needs in-flight execution reclamation and callback-state retirement.

NODELETE removes those reclamation races for guest thunk wrapper code by keeping the code resident. The two approaches can therefore be evaluated independently: small loader-lifetime policy versus larger unload-preserving runtime ownership machinery.

All edits described here are diagnostic work on owned surfaces. No upstream FEX interaction occurred.
