# Derived GL resident bridge — PFN unload/reload checkpoint

Date: 2026-08-14
Status: provisional runtime evidence; expected to be revised if later GL callback tests disagree
Scope: owned research surfaces only

## Result

The per-library resident-bridge architecture now has a second real thunk-library runtime proof beyond Vulkan.

On the owned FEX branch `diagnostic/gl-derived-bridge-output`, normal GL thunkgen output is post-processed into a process-resident `libfex-GL-bridge.so` while the ordinary `libGL-guest.so` wrapper remains physically unloadable.

Workflow run `31784431283` completed successfully on hosted ARM64. Job: `94717085534`. Carrier commit: `7aa2e1103b58094db8799de378fb113117a1d329`.

The derived bridge reproduced the complete emitted GL runtime bridge-signature set:

```text
guest signatures:  736
bridge signatures: 736
```

The RelWithDebInfo bridge ELF was:

```text
bridge_file_bytes=2578104
```

This is file size, not RSS.

## ELF lifetime split

The generated guest wrapper has:

```text
NEEDED libfex-GL-bridge.so
SONAME libGL.so.1
```

and no `DF_1_NODELETE` flag.

The bridge has:

```text
SONAME libfex-GL-bridge.so
FLAGS_1 NODELETE
```

So this is a real split lifetime rather than whole-wrapper pinning.

## Dynamic PFN after physical wrapper unload

The probe obtains the real host `glGetError` PFN through guest `glXGetProcAddress`, calls it, closes the guest GL wrapper, verifies the wrapper entrypoint is unmapped, then calls the retained PFN again.

Observed generation 1:

```text
GEN1 get=0x7ffff7bd03a0 H=0x7ffff73bd680 error=0 bridge=1
```

The old wrapper mappings were:

```text
7ffff7b12000-7ffff7b4c000
7ffff7b4c000-7ffff7bd1000
7ffff7bd1000-7ffff7bfd000
7ffff7bfd000-7ffff7bfe000
7ffff7bfe000-7ffff7c00000
```

After `dlclose`:

```text
UNMAPPED 0x7ffff7bd03a0
RETAINED_AFTER_CLOSE error=0
```

Thus the wrapper's `glXGetProcAddress` code was physically gone while the retained real native PFN remained callable through the resident bridge.

## Forced moved wrapper reload

The probe reserves the complete old wrapper mapping set before reopening GL. Generation 2 therefore loads at a different guest address:

```text
GEN2 get_old=0x7ffff7bd03a0 get_new=0x7ffff70403a0 moved=1 H_old=0x7ffff73bd680 H_new=0x7ffff73bd680 same_H=1 bridge=1
```

After the second wrapper closes, the originally retained H still works:

```text
FINAL_RETAINED error=0
DERIVED_GL_BRIDGE_OK
```

This is the same useful lifecycle property demonstrated by the full Vulkan derived bridge: wrapper generations can disappear and move while the guest-visible native H and process-lived bridge execution target remain stable.

## GL-specific ownership refinement

GL adds an important case that Vulkan did not require in the same form.

`libGL_Guest.cpp` publishes a wrapper-local `malloc_wrapper` target and a callback unpacker into persistent host state through `GL_SetGuestMalloc`. Moving only the unpacker would therefore leave the host thunk holding a dead wrapper-local target after physical guest unload.

The GL diagnostic sidecar moves both pieces:

```text
wrapper-local escaped target  -> FEXGLBridgeMalloc in resident sidecar
callback unpacker              -> resident sidecar
X11 guest target               -> remains in guest libX11
X11 callback unpacker          -> resident sidecar
```

The refined design rule is therefore:

> Every executable guest address whose lifetime FEX or a native thunk extends beyond the ordinary wrapper lifetime must be owned by the resident bridge, whether the address is an indirect-call adapter, a callback unpacker, or an escaped wrapper-local callback target.

## Generator pressure discovered during GL work

GL generated 736 indirect signatures, including at least one 23-argument dynamic-call signature. The first flat sidecar extractor attempted to instantiate `CallbackUnpack` for every emitted indirect signature and hit the existing `PackedArguments` arity constraint (`<=19` or exactly `24`).

That was an over-generation bug in the experimental extractor, not evidence that the resident caller cannot support the signature. The current diagnostic extractor defers unpacker instantiation behind a dependent template arity gate; the GL bridge then compiles and the PFN lifecycle test passes.

Longer term, the generator should retain bridge provenance/role explicitly:

```text
needs resident caller
needs resident callback unpacker
escaped wrapper-local executable target
```

Thunkgen analysis already distinguishes indirect guest calls from generated callback parameters, so a role-aware bridge manifest/output should replace the flat "every emitted signature gets every bridge role" experiment.

## Still open

This checkpoint proves the dynamic-PFN/moved-generation half for GL. It does not yet close the GL callback half.

A follow-up owned-FEX run is exercising retained GLX/X11 callback behavior after wrapper unload. That test is especially useful because GL includes both resident callback unpackers and the wrapper-local allocator target case described above.

If that callback run succeeds, the per-library sidecar will have real two-direction runtime evidence in both Vulkan and GL. If it fails, the failure should identify another escaped executable address or state dependency that the current ownership rule missed.

No upstream FEX interaction or mutation is represented by this record.