# Derived GL resident bridge — callback-after-unload checkpoint

Date: 2026-08-14
Status: provisional runtime evidence; may be revised by later counterexamples
Scope: owned research surfaces only

## Result

The per-library resident bridge now has real two-direction runtime evidence in a second thunk library, GL, in addition to Vulkan.

Owned FEX carrier:

```text
branch: diagnostic/gl-derived-bridge-output
head:   4d1fea9c3d8033aa23ef9fdee0dc4531edf47247
run:    31784704359
job:    94717922331
```

Artifact:

```text
name: gl-derived-bridge-31784704359
id:   9213145070
sha256: 538fa5d261c56d2d0ee0b493d206e911ee8674371aa8155a78de3f18d57dcd24
```

The ordinary GL wrapper remained unloadable; only `libfex-GL-bridge.so` carried `DF_1_NODELETE`.

The derived bridge covered the complete emitted GL runtime signature set:

```text
guest signatures:  736
bridge signatures: 736
bridge_file_bytes=2578104
```

The file size is a RelWithDebInfo ELF size, not RSS.

## Post-close GLX callback execution

The probe holds guest `libX11.so.6` open, loads guest `libGL.so.1`, obtains both:

- `glGetError` through `glXGetProcAddress`;
- `glXQueryExtension` through `glXGetProcAddress`.

Generation 1:

```text
GEN1 get=0x7ffff7bd03a0 H=0x7ffff73bd680 glxH=0x7ffff7307810 error=0 bridge=1
```

The guest GL wrapper is then finally closed. The wrapper entrypoint is confirmed unmapped:

```text
UNMAPPED 0x7ffff7bd03a0
RETAINED_AFTER_CLOSE error=0
```

The retained native `glXQueryExtension` PFN is then invoked after physical GL-wrapper unmap with a fresh guest display pointer:

```text
POST_CLOSE_GLX_BEGIN H=0x7ffff7307810 display=0x5615261388a0
GUEST_XSYNC display=0x5615261388a0 discard=0
GUEST_XDISPLAYSTRING display=0x5615261388a0
Opening host-side X11 display: 0x5615261388a0 -> 0xffee3a05b000
POST_CLOSE_GLX_END rc=1 error=158 event=95
DERIVED_GLX_CALLBACK_AFTER_CLOSE_OK
```

The workflow additionally verifies marker ordering:

```text
POST_CLOSE_GLX_BEGIN
  < GUEST_XSYNC
  < GUEST_XDISPLAYSTRING
  < POST_CLOSE_GLX_END
  < DERIVED_GLX_CALLBACK_AFTER_CLOSE_OK

GLX_CALLBACK_MARKER_ORDER_OK
```

This proves the persistent host-side GL/X11 state can enter resident guest callback-unpacker code after the ordinary GL wrapper has physically disappeared.

## Moved generation remains valid

After the post-close callback discriminator, the old GL wrapper ranges are reserved and generation 2 loads elsewhere:

```text
GEN2 get_old=0x7ffff7bd03a0 get_new=0x7ffff70403a0 moved=1 H_old=0x7ffff73bd680 H_new=0x7ffff73bd680 same_H=1 bridge=1
FINAL_RETAINED error=0
DERIVED_GL_BRIDGE_OK
```

Thus the same run combines:

1. dynamic guest->host PFN execution after wrapper unmap;
2. host->guest X11 callback execution after wrapper unmap;
3. forced moved wrapper reload with stable native H;
4. another retained-H call after generation 2 closes.

## Ownership rule strengthened by GL

GL demonstrates that the resident unit cannot be defined only as `CallHostFunction` callers plus callback unpackers.

`libGL_Guest.cpp` also publishes a wrapper-local allocator callback target to persistent host state. The diagnostic split therefore moves both target and unpacker into the resident bridge:

```text
FEX/native state outlives wrapper
        |
        +-- dynamic native H -> resident guest caller
        +-- host trampoline  -> resident callback unpacker
        +-- escaped wrapper-local callback target -> resident target
```

A more accurate rule is:

> Every executable guest address whose lifetime FEX or a native thunk extends beyond the ordinary guest wrapper lifetime must be owned by a process-lived bridge unit.

That address may be an indirect-call adapter, callback unpacker, or ordinary guest callback target.

## Cross-library status

At this checkpoint:

- Vulkan: real dynamic-PFN-after-unload, X11 callback-after-unload, and forced moved-wrapper reload all pass with a derived resident bridge.
- GL: real dynamic-PFN-after-unload, GLX/X11 callback-after-unload, and forced moved-wrapper reload all pass with a derived resident bridge.

This materially weakens the hypothesis that the sidecar is merely a Vulkan-specific workaround.

## Generator cleanup still warranted

The current second-stage extractor still starts from the deduplicated runtime-signature set emitted by normal thunkgen. GL exposed why a production generator should preserve bridge role/provenance explicitly: a 23-argument dynamic signature needed a resident caller but did not need a callback unpacker, while the flat experimental extractor initially tried to instantiate both.

Thunkgen analysis already distinguishes generated callback parameters from indirect guest-call entries. A cleaner bridge output should preserve at least:

```text
needs resident caller
needs resident callback unpacker
escaped wrapper-local executable target (library/runtime metadata)
```

The runtime result above validates the ownership architecture independently of how that role information is eventually emitted.

No upstream FEX contact or mutation is represented by this checkpoint.