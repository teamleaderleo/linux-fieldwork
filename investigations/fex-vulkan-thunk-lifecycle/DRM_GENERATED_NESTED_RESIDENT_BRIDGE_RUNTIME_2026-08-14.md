# Generated DRM nested callback + resident bridge runtime — 2026-08-14

## Result

Owned-fork ARM64 run [`31782481709`](https://redirect.github.com/teamleaderleo/FEX/actions/runs/31782481709) completed successfully against exact FEX product source:

`f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`

The branch carries research harness/patcher commits only before the workflow applies the diagnostic product-source change. The pre-patch product-source diff guard is empty.

Artifact:

- id: `9212317970`
- name: `agent-b-drm-nested-resident-bridge-31782481709`
- digest: `sha256:ecfa672256ba2dee982521b28f64b1de9d4ef36ad8b1457689568e6db8ace5b9`

## Generated callback surface

The research `callback_member` prototype marks all four callback-bearing `drmEventContext` fields. Thunkgen emits three unique callback signatures for those fields, and the derived per-library bridge contains the same three signatures:

```text
normal_callback_signatures=3
bridge_callback_signatures=3
```

The generated normal guest thunk contains the nested callback conversion itself, including:

```text
fex_callback_copy_1.vblank_handler = AllocateHostTrampolineForGuestFunction(a_1->vblank_handler);
```

The generated bridge accessors expose `FEXAllocateResidentHostTrampolineForGuestFunction`, and the unloadable DRM wrapper redirects generated callback allocation to that resident-by-signature helper before including `thunkgen_guest_libdrm.inl`.

This is therefore not a handwritten `drmHandleEvent` callback wrapper: nested callback discovery/conversion is generated, while the per-library bridge is derived from the normal generated signature set.

## ELF ownership

The workflow verifies:

- ordinary `libdrm-guest.so` has **no** `DF_1_NODELETE`;
- ordinary `libdrm-guest.so` has a `DT_NEEDED` dependency on `libfex-drm-bridge.so`;
- `libfex-drm-bridge.so` has `DF_1_NODELETE`.

Thus the ordinary API wrapper remains unloadable while the fixed FEX callback unpacker/signature bridge is process-resident.

## Runtime matrix

The same pipe-fed `DRM_EVENT_VBLANK` discriminator used for the pristine defect and the local-unpacker generator prototype reports:

```text
native=0
pristine_reference=132
generated_local_unpacker_reference=0
generated_resident_unpacker=0
```

Resident candidate stderr reaches:

```text
MARK handle-enter
DRM_CALLBACK count=1 fd=4 sequence=33 tv=11.22 user=0x12345678
MARK handle-return rc=0 callbacks=1
```

So moving nested generated callback allocation onto the derived resident sidecar preserves real guest callback delivery; it is not merely crash suppression.

## Interpretation

This closes an important composition gap in the resident-bridge design:

1. thunkgen can recognize function-pointer fields nested inside a callback-bearing structure;
2. generated guest code can copy caller input rather than mutate it and allocate host-callable trampolines for those fields;
3. generated host code can finalize those trampolines by exact callback type;
4. the same signature set can be derived into a per-library resident bridge automatically;
5. generated nested callbacks can then use resident unpackers while the ordinary wrapper remains unloadable.

The four DRM callback fields collapsing to three unique generated signatures also shows the bridge can operate at function-signature granularity rather than requiring a manually maintained per-field sidecar list.

## Boundary

This run exercises synchronous `drmHandleEvent` callback delivery. It does **not** by itself solve ownership of a containing structure that the native library retains after the thunk call returns, such as `drmSetServerInfo`. The earlier moved-reload `drmSetServerInfo::load_module` result separately proves that a resident unpacker is sufficient for the exercised retained callback once host-side retained-structure ownership is handled.

The `callback_member` implementation and bridge wiring in this run are fork-local research diagnostics, not upstream-ready contribution code.