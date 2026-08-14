# DRM callback_member resident bridge prep — 2026-08-14

## Current clean-source state

Clean integration tranche 1 already contains generic `callback_member` generator support and direct role-aware guest bridge generation, but the DRM interface on source commit `48e28a2ce9da1334feb8d7b77dbade66efa24be2` still treats `drmEventContext` as compatible inert data:

```cpp
template<>
struct fex_gen_type<drmEventContext> : fexgen::assume_compatible_data_layout {};
```

The next DRM source step should replace that assumption with callback-member annotations for all four callback-bearing fields:

- `drmEventContext::vblank_handler`
- `drmEventContext::page_flip_handler`
- `drmEventContext::page_flip_handler2`
- `drmEventContext::sequence_handler`

The already-integrated generic generator support registers callback_member signatures as unpacker-needed bridge roles.

## Earlier generated callback execution proof

Branch:

`ci/agent-b-drm-nested-callback-generator-20260814`

The earlier generator candidate proved that generated callback_member conversion can execute a real pipe-fed `drmHandleEvent` callback under FEX. The probe builds a `DRM_EVENT_VBLANK`, gives `drmHandleEvent` a `drmEventContext` with `vblank_handler`, and requires:

```text
DRM_CALLBACK count=1
MARK handle-return rc=0 callbacks=1
```

This establishes generated nested callback conversion/execution; it is separate from unload lifetime.

## Earlier resident sidecar proof — useful baseline, deprecated implementation path

Branch:

`ci/agent-b-drm-nested-resident-bridge-20260814`

Green run:

`31782481709`

Head:

`a1cdc1d9b25519fef9655505897e8791f17962ea`

Artifact:

- name: `agent-b-drm-nested-resident-bridge-31782481709`
- ID: `9212317970`
- SHA-256: `ecfa672256ba2dee982521b28f64b1de9d4ef36ad8b1457689568e6db8ace5b9`

Exact final matrix:

```text
native=0
pristine_reference=132
generated_local_unpacker_reference=0
generated_resident_unpacker=0
```

Candidate callback receipt:

```text
DRM_PROBE callback=0x556348490450 handle=0x7ffff7ebc180 version=4 event_size=32
MARK handle-enter
DRM_CALLBACK count=1 fd=4 sequence=33 tv=11.22 user=0x12345678
MARK handle-return rc=0 callbacks=1
```

The four annotated callback-bearing fields collapsed to three unique callback signatures:

```text
normal_callback_signatures=3
bridge_callback_signatures=3
```

The old ELF receipt showed:

- ordinary `libdrm.so.2` wrapper depended on `libfex-drm-bridge.so`;
- companion carried `NODELETE`;
- wrapper stayed unloadable.

Its wrapper RUNPATH was a build-directory path from the prototype wiring, rather than the common helper's `$ORIGIN` packaging.

### Why this old branch is reference-only

That prototype derived a second generated C++ bridge file from the normal generated guest output with `LinuxFieldwork/extract_guest_bridge.py`. The current design explicitly prefers thunkgen's direct `-guest-bridge` / `-guest-bridge-accessors` outputs, stable canonical/hash identity, and explicit caller/unpacker roles.

The old resident run also kept the wrapper loaded during the callback. It proved resident sidecar execution, but it did not prove that a host-retained trampoline survives wrapper unload and a forced moved reload.

## Direct-helper conversion to test next

The clean direct path should mirror CUDA's integrated resident callback wiring:

1. In `ThunkLibs/libdrm/libdrm_interface.cpp`, annotate all four `drmEventContext` callback members.
2. In `ThunkLibs/libdrm/Guest.cpp`, include `thunkgen_bridge_accessors_libdrm.inl` and wrap the normal generated guest include with:

```cpp
#define AllocateHostTrampolineForGuestFunction FEXAllocateResidentHostTrampolineForGuestFunction
#include "thunkgen_guest_libdrm.inl"
#undef AllocateHostTrampolineForGuestFunction
```

3. Add `ThunkLibs/libdrm_bridge/Guest.cpp` that includes `<xf86drm.h>`, `common/Guest.h`, and direct `thunkgen_bridge_libdrm.inl`.
4. Wire `drm_bridge` through the common `add_guest_bridge` helper with:
   - `OUTPUT_NAME "fex-drm-bridge"`
   - `WRAPPER_TARGET drm-guest`
   - `GENERATOR libdrm`
   - `DEP_TARGETS libdrm-guest-deps`
5. Require direct generated DRM bridge roles to be unpacker-only for callback_member signatures. The old prototype gives an expected unique-signature count of three; the direct role gate must confirm the actual current count rather than hard-coding the expectation before generation.
6. Require the common packaging boundary: wrapper unloadable, `NEEDED libfex-drm-bridge.so`, `$ORIGIN`, companion NODELETE.
7. Reuse the pipe-fed callback probe as an execution control.
8. Add a separate retained-callback/moved-reload harness that deliberately keeps a generation-1 host trampoline after wrapper close, reserves the retired wrapper mappings, forces generation 2 to move, avoids generation-2 re-registration for the retained callback under test, and triggers the saved host trampoline again.

## Remaining proof

DRM still needs the direct-helper build/role/ELF gate and the retained-callback/moved-reload test. The older green callback execution is evidence for callback_member conversion, not the unload-lifetime proof.
