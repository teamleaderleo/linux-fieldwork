# NODELETE guest-thunk lifetime containment

## Motivation

The lifetime failure has a simple loader-level containment candidate: keep generated guest thunk DSOs resident for the process, matching the effective process lifetime of their host thunk DSOs.

This prevents FEX-owned native pointers and generated host trampolines from outliving the guest invokers/unpackers they reference. It also removes the selected-code-versus-unmap race because the guest thunk text is never physically reclaimed during process lifetime.

GNU `-z nodelete` encodes this policy in the DSO as `DF_1_NODELETE` / `FLAGS_1: NODELETE`.

## Synthetic full-pair direct runtime proof

Owned-FEX branch `ci/agent-k-arm64-20260814` builds the retained full thunk pair twice:

- normal guest DSO with no NODELETE flag;
- identical guest DSO linked with `-Wl,-z,nodelete` and verified by `readelf`.

### Mapping discriminator

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

### Retained-pointer execution discriminator

Hosted ARM64 run `31772072759`, job `94679892829`, artifact `9208551221`, FEX branch commit `0b31afb60639398c8b4e64ab2dec9b4fcf484787`, makes the NODELETE fixture accept expected mapping survival and continue into every retained-call probe. FEX core itself remains pristine.

The normal arm confirms the stale-pointer baseline immediately after physical unload:

```text
old invoker after dlclose          0x00007ffff7da21b0 -> unmapped
old target after dlclose           0x00007ffff7da2170 -> unmapped
old unpacker after dlclose         0x00007ffff7da2190 -> unmapped
child stale Link/CallHost         signal=11 (Segmentation fault)
child stale first callback        signal=11 (Segmentation fault)
```

The NODELETE arm keeps all three embedded guest executable addresses mapped and both retained cross-ISA directions execute successfully immediately after the same ordinary `dlclose()`:

```text
old invoker after dlclose          0x00007ffff7da21b0 -> ... r-xp .../nodelete/guest/liblifetime-guest.so
old target after dlclose           0x00007ffff7da2170 -> ... r-xp .../nodelete/guest/liblifetime-guest.so
old unpacker after dlclose         0x00007ffff7da2190 -> ... r-xp .../nodelete/guest/liblifetime-guest.so
NODELETE proof: all embedded guest executable addresses remain mapped; continuing retained-call probes
child stale Link/CallHost         rv=1029
child stale Link/CallHost         exit=0
child stale first callback        rv=10073
child stale first callback        exit=0
```

The retained pointers also remain usable through the following reopen/reload phase:

```text
child retained Link after reload  rv=1001032
child retained Link after reload  exit=0
child retained callback reload    rv=10010083
child retained callback reload    exit=0
child first callback after new    rv=10010093
child first callback after new    exit=0
child current callback after new  rv=10010093
child current callback after new  exit=0
```

This is direct causal evidence for the containment policy. Ordinary `dlclose()` plus `DF_1_NODELETE` prevents the physical guest-wrapper reclamation that creates both observed stale-reference failures, and both H→T plus host→guest callback paths remain executable with no FEX core lifetime machinery.

The normal arm in this non-forced-reload fixture later regains retained-call success because the loader reuses compatible addresses on reopen. The earlier forced-different-VA runs remain the discriminator for ABA/reload movement; the immediate post-`dlclose()` normal stale calls above are the clean comparison against NODELETE.

## Real generated guest-wrapper builds

Owned-FEX branch `ci/agent-m-arm64-20260814` applies only this policy in the generic `add_guest_lib()` helper:

```cmake
if (TARGET_TYPE STREQUAL "SHARED")
  target_link_options(${NAME}-guest PRIVATE "LINKER:-z,nodelete")
endif()
```

### Vulkan

Run `31771633918`, job `94678611157`, artifact `9208362750`, commit `333be356c29994499478bd5494e2da0516ca22c9` successfully built the actual 64-bit x86 Vulkan guest wrapper. It retained its generated FEX identity and SONAME while gaining NODELETE:

```text
ELF 64-bit LSB shared object, x86-64
SONAME: libvulkan.so.1
FLAGS_1: NODELETE
REAL_VULKAN_GUEST_NODELETE_OK
```

### Representative matrix

Run `31771955071`, job `94679544293`, artifact `9208477160`, commit `ca4390de6024f8225fca7710b574fed371f558db` widened the same generic policy across four real generated guest wrappers representing both lifetime classes observed in this investigation:

```text
REAL_vulkan_NODELETE_OK
REAL_GL_NODELETE_OK
REAL_wayland_client_NODELETE_OK
REAL_cuda_NODELETE_OK
```

Each output was a real x86-64 FEX guest DSO with its expected SONAME and `FLAGS_1: NODELETE`:

- Vulkan: `libvulkan.so.1`
- OpenGL: `libGL.so.1`
- Wayland client: `libwayland-client.so.0.20.0`
- CUDA: `libcuda.so.1`

The build matrix covers dynamic H→T/proc-address users (Vulkan, GL, CUDA) and persistent host→guest callback/unpacker users (Vulkan/GL X11 helpers and Wayland listener machinery). No per-library build exception was required.

This demonstrates that the NODELETE policy can live centrally in `add_guest_lib()` instead of growing library-specific lifetime flags. A 32-bit guest-thunk build remains the main compile-policy gate still worth checking.

## Existing real-workload control

The earlier real `vulkaninfo` investigation already showed that retaining one guest loader reference for `libvulkan-guest.so` changes the teardown result from the crashing unload path to exit 0. NODELETE is a loader-level way to encode the same lifetime policy directly in the generated guest wrapper rather than relying on an external preload/reference holder.

## Constructor and unload-semantics audit

Guest-side load constructors are concentrated in wrappers such as Vulkan, GL, and Wayland. Their initialization performs thunk glue setup: Vulkan/GL populate helper callbacks such as X11 bridges, while Wayland initializes guest mirror/interface pointers from the persistent host side. No guest-thunk unload-management design was found in the thunk tree; the only `dlclose` search hit there is an unrelated disabled SDL path.

A process-lifetime guest-wrapper policy therefore aligns with the existing process-lifetime host-thunk model and keeps hidden cross-ISA glue paired with the code that implements it.

External application callback targets still follow their own application/native lifetime rules. NODELETE guarantees the generated guest wrapper code and unpackers remain resident; it does not create lifetime for arbitrary external guest DSOs.

## Tradeoffs

A NODELETE policy intentionally changes guest thunk wrapper lifetime semantics:

- wrapper code and data remain resident until process exit;
- intermediate `dlclose()` no longer performs physical DSO reclamation;
- constructor/destructor and repeated-load behavior follow a process-lifetime wrapper model;
- memory use increases by the resident guest thunk DSOs.

Those costs should be evaluated against the existing host side, whose thunk DSOs are already retained for process lifetime and whose hidden cross-ISA references can otherwise survive guest-wrapper unload.

The policy can be applied centrally in `add_guest_lib()`, covering generated shared guest thunks in one place.

## Relation to the unload-preserving design

NODELETE is containment, not the same design as target-cell retirement. The unload-preserving path has separately proven generation-neutral H target cells and pre-unmap T→empty→new-T publication, but still needs in-flight execution reclamation and callback-state retirement.

NODELETE removes those reclamation races for guest thunk wrapper code by keeping the code resident. The two approaches can therefore be evaluated independently: small loader-lifetime policy versus larger unload-preserving runtime ownership machinery.

All edits described here are diagnostic work on owned surfaces. No upstream FEX interaction occurred.
