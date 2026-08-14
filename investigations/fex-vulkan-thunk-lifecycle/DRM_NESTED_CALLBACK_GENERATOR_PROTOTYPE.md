# DRM nested callback-member generator prototype

Date: 2026-08-14

## Result

A focused thunkgen research prototype automatically converts callback function pointers nested inside `drmEventContext` and removes the exact current-main ARM64 `drmHandleEvent` SIGILL **without** handwritten DRM guest/host callback wrappers.

Exact FEX product base:

```text
f3ab82a73fb48271ee12a882c98bc5d823a2b4d1
```

Owned-FEX carrier:

```text
branch: ci/agent-b-drm-nested-callback-generator-20260814
head:   bacfffd271913c664702043f34a4cdd23dafbb11
run:    31781338417
job:    94707569908
artifact: agent-b-drm-nested-callback-generator-31781338417
artifact id: 9211903207
sha256: 5b4d2d3acfb67b53f37e0c1d7d4a57e6561ada3aad6426dda911defaad579817
```

The branch itself contains only the research patcher, probe, and workflow. Product source changes are applied at CI runtime after an exact-product source-diff guard.

## Runtime matrix

```text
native=0
pristine_reference=132
generated_candidate=0
```

Candidate stderr proves real callback delivery rather than suppression:

```text
DRM_PROBE callback=0x558c0a217450 handle=0x7ffff7ebc120 version=4 event_size=32
MARK handle-enter
DRM_CALLBACK count=1 fd=4 sequence=33 tv=11.22 user=0x12345678
MARK handle-return rc=0 callbacks=1
```

The native control delivers the same one callback and returns 0. The pristine exact-current-main reference is the previously retained SIGILL 132 at this callback boundary.

## What thunkgen generated

The workflow required generated-code markers before runtime was considered meaningful.

Generated guest file:

```text
guest-build/gen/thunkgen_guest_libdrm.inl
```

contains:

```text
1235:  _drmEventContext fex_callback_copy_1 {};
1237:    fex_callback_copy_1 = *a_1;
1238:    fex_callback_copy_1.vblank_handler = AllocateHostTrampolineForGuestFunction(a_1->vblank_handler);
1239:    fex_callback_copy_1.page_flip_handler = AllocateHostTrampolineForGuestFunction(a_1->page_flip_handler);
1240:    fex_callback_copy_1.page_flip_handler2 = AllocateHostTrampolineForGuestFunction(a_1->page_flip_handler2);
1241:    fex_callback_copy_1.sequence_handler = AllocateHostTrampolineForGuestFunction(a_1->sequence_handler);
1244:  args.a_1 = a_1 ? &fex_callback_copy_1 : nullptr;
```

Generated host file:

```text
build/ThunkLibs/HostLibs/gen_64/thunkgen_host_libdrm.inl
```

contains the corresponding typed finalization, for example:

```text
1669:    auto fex_callback_1_vblank_handler = args->a_1.get_pointer()->data.vblank_handler;
1670:    FinalizeHostTrampolineForGuestFunction(fex_callback_1_vblank_handler);
1671:    a_1.data->data.vblank_handler = reinterpret_cast<decltype(a_1.data->data.vblank_handler)>(uintptr_t { fex_callback_1_vblank_handler.data });
```

So the successful conversion is generated from the interface annotation; it is not hidden in `ThunkLibs/libdrm/Guest.cpp` or `Host.cpp`.

## Research annotation and generator model

The prototype adds a research-only member annotation:

```cpp
fexgen::callback_member
```

and annotates all four callback-bearing `drmEventContext` fields:

```cpp
vblank_handler
page_flip_handler
page_flip_handler2
sequence_handler
```

The prototype removes `assume_compatible_data_layout` for `drmEventContext`, lets normal layout-wrapper generation handle the structure, and treats callback fields as callback-specific repacked members.

For a pointer to a callback-bearing input structure, generated guest code:

1. allocates a stack copy of the caller structure;
2. copies the caller input unchanged;
3. replaces only annotated callback fields in that temporary copy with partially initialized host trampolines via the existing `AllocateHostTrampolineForGuestFunction` path;
4. passes the temporary copy through the normal thunk transport.

Generated host code:

1. creates the normal host repack wrapper;
2. reads each annotated raw trampoline field from guest layout;
3. finalizes it through the existing typed `FinalizeHostTrampolineForGuestFunction` path;
4. writes the finalized native-callable function pointer into the host-side structure copy;
5. calls native libdrm normally.

This is the same proven FEX callback protocol already used for direct callback parameters and handwritten Wayland nested listener callbacks, extended into structure members.

## Caller-input integrity

The generated guest stack copy is important: callback conversion does not overwrite the application-owned `drmEventContext` merely to replace callback pointers. The caller's structure remains the source; the transformed object is a temporary thunk-side copy.

This avoids repeating the kind of caller-owned input mutation separately identified in the Vulkan `vkCreateInstance` debug-report pNext path.

## Scope of this first prototype

This is deliberately narrower than a production generator feature.

- **64-bit guest only was exercised.**
- The callback-bearing structure is treated as **input-only**. The prototype suppresses automatic exit copyback for a type whose manual fields are only `callback_member`s; it does not define general in/out semantics for callback-bearing structures.
- All four `drmEventContext` callback fields were generated and compiled. The runtime discriminator exercises only `vblank_handler`.
- This run does **not** move the generated `CallbackUnpack<signature>::Unpack` bodies into a resident sidecar. For synchronous `drmHandleEvent`, the ordinary wrapper stays mapped for the duration of the native call, so no post-unload lifetime claim follows from this run.
- This does **not** solve `drmServerInfo`. Native libdrm retains that containing structure pointer after `drmSetServerInfo` returns, so persistent replacement-object ownership is a separate axis even after nested callback conversion is generated.
- Variadic callback members are rejected by this prototype rather than guessed.
- The annotation syntax is research-only and not proposed as final FEX API design.

## Relation to the resident-bridge work

The derived Vulkan resident bridge already demonstrates automatic per-library resident `CallHostFunction` and callback-unpacker generation for ordinary thunkgen-recognized signatures.

This DRM result closes the missing **classification/code-generation** half for a different API shape: callbacks hidden inside a structure previously declared inert/ABI-compatible.

A natural next integration is:

1. make `callback_member` signatures enter the same per-library bridge signature set as direct callback parameters;
2. have generated nested-field allocation select the resident per-library `CallbackUnpack<signature>::Unpack` by type;
3. keep the ordinary wrapper reclaimable where native state can outlive it.

The earlier `drmServerInfo::load_module` moved-reload A/B already proves why this matters for retained callbacks:

```text
wrapper-owned unpacker = 139
resident unpacker = 0
```

under the same forced physical wrapper unload/moved-reload fixture with no callback re-registration.

## Separate retained-object problem

Even a fully generated callback-member feature cannot infer native retention of the containing object from C/C++ type shape alone.

For `drmHandleEvent`, a temporary guest/host structure copy is sufficient because native libdrm consumes it synchronously.

For `drmSetServerInfo`, native libdrm retains the supplied `drmServerInfo*` and later calls `load_module` from a separate `drmOpen` invocation. A temporary `repack_wrapper` would therefore leave a dangling host structure pointer after the registration thunk returns.

Generator design should keep these as two separate metadata questions:

- **callback member:** how does the callable pointer cross ISA safely?
- **retained containing object:** who owns the replacement structure and until when?

## Conclusion

The current callback defect class is not limited to Vulkan and does not require bespoke per-library handwritten bridge code for every synchronous nested callback.

This run demonstrates that thunkgen can reuse its existing callback allocation/finalization machinery for a nested callback-bearing input structure and preserve real callback semantics:

```text
native 0 / pristine FEX 132 / generated candidate 0
```

The strongest next generator work is to connect nested callback-member signatures to the already-derived per-library resident bridge output, then treat retained containing-object lifetime as a separate explicit contract.

No upstream FEX repository was modified or contacted. This prototype ran only on owned research surfaces and is not an upstream contribution.
