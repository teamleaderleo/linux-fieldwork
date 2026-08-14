# Callback in-flight unmap race on current clean source — 2026-08-14

## Source and question

Exact clean resident-bridge source:

`1e8b042e7d50335cdbf2b1b6bfd0c888296dd73a`

The generic question is whether an already-selected host-to-guest callback can be resumed after the guest mapping containing its unpacker/target has been unmapped. The resident contrast asks whether moving the retained unpacker into a NODELETE per-library companion removes that specific wrapper-unmap hazard for a real DRM callback.

No product source changes are under test in this note. Runtime-only instrumentation pauses callback entry #2 inside `ThunkHandler_impl::CallCallback`, records the selected unpacker/target, and releases the pause immediately if the subsequent guest unmap covers either selected address.

## Generic current-clean replay — reproduced

Diagnostic branch:

`diagnostic/callback-inflight-current-clean-20260814`

Workflow:

`.github/workflows/callback-inflight-current-clean.yml`

Run:

`31818408405`

Job:

`94825520709`

Artifact:

- ID: `9226099077`
- SHA-256: `24328ade41048867183122bd8433847997b1ff886e4a8f18a6f2ee9bf6597c67`

The pin arm exits 0. Entry #2 is selected with both guest addresses in the retained DSO, no unmap occurs, the 1.5-second diagnostic pause times out, and the callback returns normally:

```text
DIAG_CALLBACK_INFLIGHT_SELECTED entry=2 unpacker=0x7ffff7da2190 target=0x7ffff7da2170
CALLBACK_RACE_PINNED target=0x7ffff7da2170 unpacker=0x7ffff7da2190
DIAG_CALLBACK_INFLIGHT_PIN_TIMEOUT_RESUME unpacker=0x7ffff7da2190 target=0x7ffff7da2170
DIAG_CALLBACK_INFLIGHT_RESUME entry=2 unpacker=0x7ffff7da2190 target=0x7ffff7da2170
CALLBACK_RACE_WORKER_RETURN rv=10063
```

The unmap arm intentionally exits 139. Exact sequence:

```text
DIAG_CALLBACK_INFLIGHT_SELECTED entry=2 unpacker=0x7ffff7da2190 target=0x7ffff7da2170
CALLBACK_RACE_DLCLOSE_BEGIN target=0x7ffff7da2170 unpacker=0x7ffff7da2190
DIAG_CALLBACK_TOMBSTONE trampoline=0x7ffff7dbe000 unpacker=0x7ffff7da2190 target=0x7ffff7da2170 range=0x7ffff7da1000+0x5000
DIAG_CALLBACK_POST_UNMAP_RELEASE unpacker=0x7ffff7da2190 target=0x7ffff7da2170 range=0x7ffff7da1000+0x5000
DIAG_CALLBACK_INFLIGHT_RESUME entry=2 unpacker=0x7ffff7da2190 target=0x7ffff7da2170
```

The process then segfaults. Recorded ordering offsets are:

- selected: 289
- tombstone: 457
- post-unmap release: 581
- resume: 688

Gate:

`CURRENT_CLEAN_CALLBACK_INFLIGHT_RACE_OK`

Classification: the generic selected-callback/unmap race is still present at the clean resident source. Tombstoning the trampoline after callback selection does not protect that already-entered invocation; once its selected guest code mapping disappears, resuming it faults.

## DRM resident contrast run 1 — host-created pthread boundary, not wrapper-close evidence

Workflow:

`.github/workflows/drm-resident-inflight-wrapper-close.yml`

Run:

`31818524079`

Job:

`94825902394`

Artifact:

- ID: `9226155941`
- SHA-256: `1adb1c70a22020d61e2fd99f615736dec06f1b64ae56bb832ceb9c6b9c86986e`

All source provenance, runtime-only instrumentation, FEX/DRM builds, ELF checks, native fake build, rootfs construction, and probe build pass before execution.

The tested DRM pair has the intended ownership boundary:

- ordinary `libdrm.so.2` wrapper: NEEDED `libfex-drm-bridge.so`, `$ORIGIN`, no NODELETE;
- `libfex-drm-bridge.so`: NODELETE;
- diagnostic vblank unpacker export: `FEXDRMDiagVBlankUnpacker`;
- actual vblank unpacker address maps inside the resident companion.

Runtime begins correctly:

```text
DRM_RESIDENT_RACE_ADDR handle=0x7ffff7eb9180 available=0x7ffff7eb7500 unpacker=0x7ffff7eaf210 target=0x55ee385f46a0
MAP 0x7ffff7eaf210 ... /usr/lib/x86_64-linux-gnu/libfex-drm-bridge.so
HOST_DRM_SAVE trampoline=0x7ffff7eaa000
DRM_RESIDENT_RACE_CALLBACK count=1 fd=5 seq=41 tv=42.43 user=0x11112222
HOST_DRM_ASYNC_STARTED trampoline=0x7ffff7eaa000
DRM_RESIDENT_RACE_TRIGGER_RETURN rc=17 callbacks=1
HOST_DRM_ASYNC_ENTER trampoline=0x7ffff7eaa000
```

It then exits 139 before these required markers ever occur:

- `DIAG_CALLBACK_INFLIGHT_SELECTED entry=2`
- `DRM_RESIDENT_RACE_DLCLOSE_BEGIN`

This is not a resident-wrapper-close failure. The native fake created a host pthread and invoked the saved host-to-guest trampoline from that thread. FEX's thunk callback implementation requires a registered per-thread `ThreadObject`; `CallCallback` explicitly aborts if that TLS object is absent, reporting that a thunked library attempted to invoke a guest callback asynchronously. A host-created pthread therefore cannot serve as this race trigger without an attach/registration path.

Run 1 is preserved as a harness-boundary receipt only.

## Guest-thread resident contrast — active design

A replacement workflow uses a guest-created pthread, so FEX owns/registers the emulated thread. The worker enters a synchronous native `drmHandleEvent` callback while the wrapper remains loaded. Callback entry #2 is paused inside FEX. The main guest thread then closes the ordinary wrapper and verifies:

1. the wrapper entry becomes unmapped;
2. the selected DRM unpacker remains mapped in `libfex-drm-bridge.so`;
3. the guest callback target remains mapped in the main executable;
4. wrapper unmap does not emit `DIAG_CALLBACK_POST_UNMAP_RELEASE` for the selected resident callback;
5. the diagnostic pause times out normally;
6. the callback enters the application target after wrapper close.

The second callback deliberately stays in main-executable code after entry. The main thread exits the process after observing that entry, avoiding a separate return-path fault through the intentionally unmapped wrapper stub on the worker thread.

Workflow:

`.github/workflows/drm-resident-inflight-wrapper-close-guest-thread.yml`

Carrier commit:

`c55b3307b9ea2a8e85d96104638d58dc07ee0ba8`

Run:

`31819276326`

Status at note creation: queued. Append the final runtime receipt before classifying whether the resident companion removes this specific in-flight wrapper-unmap hazard.
