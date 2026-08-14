# CUDA retained trampoline `GuestUnpacker` ownership trace — 2026-08-14

## Purpose

Resolve the contradictory CUDA moved-reload result from run `31787029666`, where a sequential same-job A/B reported:

```
native_deferred=0
local_unpacker=139
resident_unpacker=139
```

The decisive question is not whether a sidecar exists or whether its generated signature count matches. FEX host-to-guest trampolines embed a concrete `GuestUnpacker` address at guest-side allocation time. The trace instruments `MakeHostTrampolineForGuestFunction()` and classifies that embedded address against the generation-1 wrapper mappings retired by the moved-reload probe.

## Final isolated A/B with pre-close control

Workflow: `CUDA retained trampoline unpacker trace`

Run: `31788360618`

The local and resident variants execute as separate matrix jobs on separate ARM64 runners. Each job:

1. starts from exact product source `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`;
2. applies the generated `callback_member` CUDA transform;
3. instruments FEX trampoline creation to print `GuestUnpacker` and `GuestTarget`;
4. builds either the unloadable local wrapper or the unloadable wrapper + NODELETE resident bridge;
5. registers one CUDA host-node callback in generation 1;
6. calls the retained callback once while generation 1 is still mapped — required callback-generation control;
7. physically unloads generation 1 and reserves all five former wrapper mappings;
8. forces generation 2 to a different guest address;
9. invokes only the native registration retained from generation 1 — generation 2 does not re-register the callback.

## Local arm

Result: exit `139` after the post-reload retained invocation.

Relevant trace:

```
GEN1 wrapper=.../libcuda.so.1 add=0x7ffff7ea4b80 launch=0x7ffff7ea6160 callback=0x56160e617a20 ranges=5
FEX_TRAMP_CREATE unpacker=0x7ffff7ea8040 target=0x56160e617a20
FEX_TRAMP_CREATED trampoline=0x7ffff7e5b000 unpacker=0x7ffff7ea8040 target=0x56160e617a20
MARK launch1-enter pre-close-control
CUDA_RETAINED_CALLBACK count=1 user=0x12345678
MARK launch1-return rc=0 callbacks=1
RESERVED ... five generation-1 wrapper mappings ...
GEN2 add=0x7ffff7766b80 launch=0x7ffff7768160 moved=1
MARK launch2-enter retained-registration-only
```

Machine classification:

```
trampoline[0] unpacker=0x7ffff7ea8040 target=0x56160e617a20 unpacker_in_retired_wrapper=1
```

The exact generated callback path is valid while generation 1 is loaded. The concrete guest unpacker embedded in the host trampoline belongs to the unloadable wrapper; after physical unload and moved reload, the retained native registration exits 139 before the second guest callback body executes.

## Resident arm

Result: exit `0`.

Relevant trace:

```
GEN1 wrapper=.../libcuda.so.1 add=0x7ffff7eb0a70 launch=0x7ffff7eb2080 callback=0x5630c4d1ba20 ranges=5
FEX_TRAMP_CREATE unpacker=0x7ffff7e75610 target=0x5630c4d1ba20
FEX_TRAMP_CREATED trampoline=0x7ffff7e24000 unpacker=0x7ffff7e75610 target=0x5630c4d1ba20
MARK launch1-enter pre-close-control
CUDA_RETAINED_CALLBACK count=1 user=0x12345678
MARK launch1-return rc=0 callbacks=1
RESERVED ... five generation-1 wrapper mappings ...
GEN2 add=0x7ffff7742a70 launch=0x7ffff7744080 moved=1
MARK launch2-enter retained-registration-only
CUDA_RETAINED_CALLBACK count=2 user=0x12345678
MARK launch2-return rc=0 callbacks=2
```

Machine classification:

```
trampoline[0] unpacker=0x7ffff7e75610 target=0x5630c4d1ba20 unpacker_in_retired_wrapper=0
```

The exact same generated callback path succeeds before unload. Its embedded guest unpacker is outside every retired wrapper mapping, and the generation-1 native registration successfully calls the guest again after a forced moved wrapper reload without re-registration.

## Final discriminator

```
                         pre-close callback   GuestUnpacker ownership   post-move retained callback
local wrapper unpacker         PASS            retired wrapper                  exit 139
resident bridge unpacker       PASS            outside retired wrapper          PASS / exit 0
```

This is direct ownership evidence for the resident-bridge mechanism in a generated nested/deferred callback case.

The earlier sequential same-job `resident=139` result is superseded. The exact source of that earlier same-job contamination is not established; do not attribute it to a particular FEX subsystem without evidence.

## Consequence for bridge generation

For callback-capable bridge code, the important artifact is not merely a generated sidecar or matching signature count. Guest-side callback allocation must pass a bridge-resident `GuestUnpacker` into FEX **when the HostToGuestTrampoline is created**. Host-side finalization later supplies only `HostPacker` and cannot repair a stale wrapper-owned unpacker.
