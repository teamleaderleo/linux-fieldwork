# Generator-derived GL resident bridge and post-unload GLX callback runtime

Date: 2026-08-14

This checkpoint extends the resident executable companion work from Vulkan to real generated GL thunks. The ordinary `libGL-guest` wrapper remains physically unloadable while a small `NODELETE` companion owns guest executable bridge code whose addresses escape into persistent FEX/native state.

## Branch and generator source

Owned FEX branch:

- `diagnostic/gl-derived-bridge-output`

The branch uses the same `ThunkLibs/Generator/extract_guest_bridge.py` mechanism already exercised for Vulkan. The normal generated GL guest inl is the single source consumed by the extractor, so the resident bridge and wrapper accessors inherit the same callback numbering and signature set.

The current diagnostic extractor additionally avoids eagerly instantiating host-to-guest callback unpackers for signatures whose `PackedArguments` arity cannot support that direction. This was exposed by GL's much larger function-pointer signature set and is a useful reason to move resident generation into thunkgen itself, where callback-direction usage is already known explicitly.

## Baseline generated GL PFN lifetime run

Workflow run:

- `31784431283`
- job `94717085534`

Carrier commit:

- `7aa2e1103b58094db8799de378fb113117a1d329`

Generation/build assertions:

- normal generated GL guest `MAKE_CALLBACK_THUNK` count: **736**
- generated resident bridge count: **736**
- normalized generated callback sets: exact equality
- wrapper has `NEEDED libfex-GL-bridge.so`
- wrapper has no `NODELETE`
- resident bridge has `NODELETE`
- resident bridge ELF file size: **2,578,104 bytes**

Runtime assertions all passed:

1. `glXGetProcAddress` from generation 1 is physically unmapped after `dlclose(libGL.so.1)`.
2. The resident bridge remains mapped.
3. A retained native `glGetError` pointer remains callable after wrapper close.
4. The old wrapper address ranges are reserved before reload, forcing generation 2 to move.
5. The generation-2 wrapper entrypoint changes address.
6. The native `glGetError` H remains exactly the same.
7. The retained generation-1 H remains callable after the second close.

Success marker:

- `DERIVED_GL_BRIDGE_OK`

Artifact ZIP SHA256:

- `9a361ceb29003cb6276e916925dc5006b7b5152b1da2c781ff497451c4f89977`

This gives GL the same generator-derived guest-to-host dynamic-PFN lifetime result already established for Vulkan.

## Post-wrapper-unload GLX / X11 callback discriminator

A second run added a host-to-guest callback lifetime discriminator using a retained Display-taking GLX function.

Workflow run:

- `31784704359`
- job `94717922331`

Carrier commit:

- `4d1fea9c3d8033aa23ef9fdee0dc4531edf47247`

Artifact:

- artifact ID `9213145070`
- artifact ZIP SHA256 `538fa5d261c56d2d0ee0b493d206e911ee8674371aa8155a78de3f18d57dcd24`

### Isolation policy

The guest probe independently holds `libX11.so.6` open. This deliberately preserves the guest X11 **target** functions while allowing the GL wrapper to disappear. The discriminator therefore isolates the GL-wrapper-owned callback-unpacker lifetime that the resident companion is intended to repair.

The guest X11 stub logs `XSync` and `XDisplayString`. Xvfb runs on host display `:99`.

The probe obtains both:

- retained `glGetError` H;
- retained `glXQueryExtension` H via `glXGetProcAddress`.

After closing the GL wrapper and verifying its generation-1 GIPA address is unmapped, it calls `glXQueryExtension` with a fresh guest Display pointer. FEX's `X11Manager::GuestToHostDisplay()` always invokes retained guest `XSync`; for a newly seen guest Display it also invokes retained guest `XDisplayString`. This forces the path:

`retained native GLX H -> host GL thunk -> X11Manager -> retained host trampoline -> resident CallbackUnpack -> still-live guest X11 target`

### Exact runtime evidence

```text
GEN1 get=0x7ffff7bd03a0 H=0x7ffff73bd680 glxH=0x7ffff7307810 error=0 bridge=1
OLD_GL_RANGE 7ffff7b12000-7ffff7b4c000
OLD_GL_RANGE 7ffff7b4c000-7ffff7bd1000
OLD_GL_RANGE 7ffff7bd1000-7ffff7bfd000
OLD_GL_RANGE 7ffff7bfd000-7ffff7bfe000
OLD_GL_RANGE 7ffff7bfe000-7ffff7c00000
UNMAPPED 0x7ffff7bd03a0
RETAINED_AFTER_CLOSE error=0
POST_CLOSE_GLX_BEGIN H=0x7ffff7307810 display=0x5615261388a0
GUEST_XSYNC display=0x5615261388a0 discard=0
GUEST_XDISPLAYSTRING display=0x5615261388a0
Opening host-side X11 display: 0x5615261388a0 -> 0xffee3a05b000
POST_CLOSE_GLX_END rc=1 error=158 event=95
DERIVED_GLX_CALLBACK_AFTER_CLOSE_OK
GEN2 get_old=0x7ffff7bd03a0 get_new=0x7ffff70403a0 moved=1 H_old=0x7ffff73bd680 H_new=0x7ffff73bd680 same_H=1 bridge=1
FINAL_RETAINED error=0
DERIVED_GL_BRIDGE_OK
GLX_CALLBACK_MARKER_ORDER_OK
```

The workflow asserts the post-close marker ordering:

1. `POST_CLOSE_GLX_BEGIN`
2. `GUEST_XSYNC`
3. `GUEST_XDISPLAYSTRING`
4. `POST_CLOSE_GLX_END`
5. `DERIVED_GLX_CALLBACK_AFTER_CLOSE_OK`

Generation assertions remained **736 / 736** with exact normalized set equality. Bridge size remained **2,578,104 bytes**.

## What this proves

The same generator-derived per-library resident companion mechanism now works in real generated Vulkan and GL experiments for both escaped executable directions:

- guest -> host dynamic function-pointer invokers;
- host -> guest callback unpackers.

The ordinary GL wrapper physically unloads. A retained native GLX H can subsequently traverse FEX's persistent X11 callback state through a resident unpacker and reach a separately retained guest target. Forced moved reload still preserves the same native H and retained invocation.

This strengthens the resident-companion design as a cross-library mechanism instead of a Vulkan-specific workaround.

## Generator consequence

The Python extractor is now useful evidence and an awkward product boundary.

Thunkgen's existing analysis already distinguishes the information needed by each direction:

- `thunked_funcptrs` contains signatures that need guest-to-host runtime function-pointer thunking;
- `ThunkedFunction::callbacks` identifies actual host-to-guest callback parameters and their semantics.

A first-class resident-output mode should therefore use **one thunkgen analysis pass** to emit:

1. the normal unloadable guest wrapper output;
2. resident guest-to-host invoker definitions for the deduplicated runtime function-pointer signature set;
3. resident host-to-guest callback unpacker definitions only for signatures actually used in callback direction;
4. typed wrapper accessors that reference those resident definitions.

That removes the postprocessor, callback-number coupling concerns between independent passes, and the temporary broad arity filter exposed by GL.

Custom raw escape points invisible to normal thunkgen analysis, including the Vulkan/GL X11 setter helpers, still need a small explicit resident escaped-signature/type declaration mechanism.

## Boundary

This is hosted ARM64 mechanism proof. It does not claim an instruction-for-instruction replay of the original Apple M5 final teardown edge.

CustomIR cache retirement remains an independent Finding-B repair. Resident executable ownership handles already-published guest executable addresses; cache retirement handles future H -> T rebinding. Both concerns remain separately testable.