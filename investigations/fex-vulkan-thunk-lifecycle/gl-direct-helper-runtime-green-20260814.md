# GL direct-helper moved-reload runtime — GREEN — 2026-08-14

## Exact source

FEX diagnostic branch:

`diagnostic/gl-direct-helper-f3ab-20260814`

Head:

`0dc102a565320d28a0b30a1f1bd53b9c5f9a799d`

Exact product base:

`f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`

This is the same source head that passed build / direct-role / ELF run `31797129061`.

## Runtime gate

GitHub Actions run:

`31797129095`

Job:

`94756564770` (`gl-runtime`)

Result:

`success`

Probe exit:

`0`

Artifact:

- name: `gl-direct-helper-runtime-31797129095`
- ID: `9217921574`
- SHA-256: `1105d87304248b076ca0f3654359672b9f16f82cfb10835dc060c148fcefed86`

## Generation 1 resident executable ownership

The probe exposed the generated caller `T` addresses for `glGetError` and `glXGetFBConfigs` through runtime-only wrapper hooks, without restoring the old companion name→caller map.

Generation 1 receipt:

```text
GEN1 get=0x7ffff7bd0400 Herr=0x7ffff73bd680 Terr=0x7ffff7ea35d0 Hcfg=0x7ffff76c5970 Tcfg=0x7ffff7ea65e0 malloc_target=0x7ffff7e9c1d0 malloc_unpack=0x7ffff7e9c250 xsync_unpack=0x7ffff7e9c270 xvisual_unpack=0x7ffff7ead9d0 xdisplay_unpack=0x7ffff7e9c290
```

Every escaped guest executable address checked by the probe mapped inside the resident companion executable mapping:

```text
7ffff7e93000-7ffff7eae000 r-xp ... /usr/lib/x86_64-linux-gnu/libfex-GL-bridge.so
```

This includes:

- `Terr=0x7ffff7ea35d0` — generated `glGetError` caller;
- `Tcfg=0x7ffff7ea65e0` — generated `glXGetFBConfigs` caller;
- `malloc_target=0x7ffff7e9c1d0`;
- `malloc_unpack=0x7ffff7e9c250`;
- `xsync_unpack=0x7ffff7e9c270`;
- `xvisual_unpack=0x7ffff7ead9d0`;
- `xdisplay_unpack=0x7ffff7e9c290`.

Before close, the GLX callback path executed and the resident allocator target ran:

```text
GUEST_XSYNC display=0x12345000 discard=0
GUEST_XDISPLAYSTRING display=0x12345000
GL_BRIDGE_MALLOC size=1920
BEFORE_CLOSE_CONFIGS configs=0x5579d5cd6a30 count=240
```

## Physical wrapper unload

The generation-1 wrapper occupied five mappings:

```text
OLD_GL_RANGE 7ffff7b08000-7ffff7b4c000
OLD_GL_RANGE 7ffff7b4c000-7ffff7bd1000
OLD_GL_RANGE 7ffff7bd1000-7ffff7bfd000
OLD_GL_RANGE 7ffff7bfd000-7ffff7bfe000
OLD_GL_RANGE 7ffff7bfe000-7ffff7c00000
```

After `dlclose`, the saved wrapper `glXGetProcAddress` entry was physically absent:

```text
UNMAPPED 0x7ffff7bd0400
```

The saved generated callers, allocator target/unpacker, and fixed X11 unpackers remained mapped in `libfex-GL-bridge.so`.

## Retained callback after wrapper close

The retained generation-1 `glXGetFBConfigs` path executed after the wrapper was gone:

```text
AFTER_CLOSE_BEGIN
GUEST_XSYNC display=0x12346000 discard=0
GUEST_XDISPLAYSTRING display=0x12346000
GL_BRIDGE_MALLOC size=1920
AFTER_CLOSE_CONFIGS configs=0x5579d5ca8c70 count=240
```

This directly exercises the escaped allocator target, allocator unpacker, generated PFN caller, and fixed X11 callback unpackers after wrapper unload.

## Forced moved reload

All five retired wrapper ranges were reserved with `MAP_FIXED_NOREPLACE`:

```text
RESERVED 7ffff7b08000-7ffff7b4c000
RESERVED 7ffff7b4c000-7ffff7bd1000
RESERVED 7ffff7bd1000-7ffff7bfd000
RESERVED 7ffff7bfd000-7ffff7bfe000
RESERVED 7ffff7bfe000-7ffff7c00000
```

Generation 2 therefore moved:

```text
GEN2 get_old=0x7ffff7bd0400 get_new=0x7fffe94a0400 moved=1 Herr_old=0x7ffff73bd680 Herr_new=0x7ffff73bd680 same_H=1 Hcfg_old=0x7ffff76c5970 Hcfg_new=0x7ffff76c5970 same_cfg_H=1 Terr_old=0x7ffff7ea35d0 Terr_new=0x7ffff7ea35d0 same_T=1 Tcfg_old=0x7ffff7ea65e0 Tcfg_new=0x7ffff7ea65e0 same_cfg_T=1
```

This proves in one receipt:

- wrapper generation 2 has a different guest base (`moved=1`);
- the same native `glGetError` PFN is reused (`same_H=1`);
- the same native `glXGetFBConfigs` PFN is reused (`same_cfg_H=1`);
- the generated resident `glGetError` caller is stable across generations (`same_T=1`);
- the generated resident `glXGetFBConfigs` caller is stable across generations (`same_cfg_T=1`).

Generation 2 callback execution succeeded:

```text
GUEST_XSYNC display=0x12347000 discard=0
GUEST_XDISPLAYSTRING display=0x12347000
GL_BRIDGE_MALLOC size=1920
RELOAD_CONFIGS configs=0x5579d5cd7bb0 count=240
```

After generation 2 closed, the retained generation-1 PFN still executed the callback path:

```text
GUEST_XSYNC display=0x12348000 discard=0
GUEST_XDISPLAYSTRING display=0x12348000
GL_BRIDGE_MALLOC size=1920
FINAL_RETAINED_CONFIGS configs=0x5579d5caca90 count=240
REAL_GL_DIRECT_HELPER_OK
```

## Runtime ELF receipt

The runtime build independently preserved the intended boundary:

- wrapper: `NEEDED libfex-GL-bridge.so`, `$ORIGIN` RUNPATH, no NODELETE;
- companion: `SONAME libfex-GL-bridge.so`, `FLAGS_1 NODELETE`.

Runtime-build `size` output:

```text
   text    data     bss     dec     hex  filename
 998483    6824      88 1005395   f5753  guest-direct/libGL-guest.so
 244689     624       8  245321   3be49  guest-direct/libfex-GL-bridge.so
```

The slight size increase versus the build-only gate comes from runtime-only diagnostic observability and `fprintf` instrumentation; those hooks stay off the clean source tranche.

## Promotion decision

The direct-helper GL implementation now has both required independent green gates from the exact same post-Fix-4 head:

- build / 736 caller-only role / ELF: run `31797129061`;
- real moved-reload PFN + retained GLX/X11 callback lifetime: run `31797129095`.

GL is ready for clean source tranche 2 atop `integration/per-library-resident-bridges-f3ab-20260814` (`48e28a2ce9da1334feb8d7b77dbade66efa24be2`). Diagnostic scripts, workflows, and runtime hooks must stay off that source branch.
