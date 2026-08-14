# CUDA retained trampoline `GuestUnpacker` ownership trace — 2026-08-14

## Purpose

Resolve the contradictory CUDA moved-reload result from run `31787029666`, where a sequential same-job A/B reported:

```
native_deferred=0
local_unpacker=139
resident_unpacker=139
```

The decisive question is not whether a sidecar exists or whether its generated signature count matches. FEX host-to-guest trampolines embed a concrete `GuestUnpacker` address at guest-side allocation time. The trace therefore instruments `MakeHostTrampolineForGuestFunction()` and classifies that embedded address against the generation-1 wrapper mappings later retired by the moved-reload probe.

## Isolated-run design

Workflow: `CUDA retained trampoline unpacker trace`

Run: `31788089785`

The local and resident variants execute as separate matrix jobs on separate ARM64 runners. Each job:

1. starts from exact product source `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`;
2. applies the same generated `callback_member` CUDA transform;
3. instruments FEX trampoline creation to print `GuestUnpacker` and `GuestTarget`;
4. builds either the unloadable local wrapper or the unloadable wrapper + NODELETE resident bridge;
5. registers one CUDA host-node callback in generation 1;
6. physically unloads generation 1 and reserves all five former wrapper mappings;
7. forces generation 2 to a different guest address;
8. invokes only the native registration retained from generation 1.

## Local arm

Result: exit `139`.

Trace:

```
GEN1 ... add=0x7ffff7ea4b80 ... callback=0x56042b4e3980 ranges=5
FEX_TRAMP_CREATE unpacker=0x7ffff7ea8040 target=0x56042b4e3980
FEX_TRAMP_CREATED trampoline=0x7ffff7e5b000 unpacker=0x7ffff7ea8040 target=0x56042b4e3980
RESERVED 0x7ffff7e8d000-0x7ffff7e94000
RESERVED 0x7ffff7e94000-0x7ffff7eb2000
RESERVED 0x7ffff7eb2000-0x7ffff7ebc000
RESERVED 0x7ffff7ebc000-0x7ffff7ebd000
RESERVED 0x7ffff7ebd000-0x7ffff7ebe000
GEN2 ... moved=1
MARK launch2-enter retained-registration-only
```

Machine classification:

```
trampoline[0] unpacker=0x7ffff7ea8040 ... unpacker_in_retired_wrapper=1
```

The embedded guest unpacker lies in the retired generation-1 wrapper. The retained host trampoline therefore has a stale executable target after unload, and the moved-reload call exits 139 before the guest callback body executes.

## Resident arm

Result: exit `0`.

Trace:

```
GEN1 ... add=0x7ffff7eb0a70 ... callback=0x557764ac0980 ranges=5
FEX_TRAMP_CREATE unpacker=0x7ffff7e75610 target=0x557764ac0980
FEX_TRAMP_CREATED trampoline=0x7ffff7e24000 unpacker=0x7ffff7e75610 target=0x557764ac0980
RESERVED 0x7ffff7e8f000-0x7ffff7e9d000
RESERVED 0x7ffff7e9d000-0x7ffff7eb5000
RESERVED 0x7ffff7eb5000-0x7ffff7ebc000
RESERVED 0x7ffff7ebc000-0x7ffff7ebd000
RESERVED 0x7ffff7ebd000-0x7ffff7ebe000
GEN2 ... moved=1
MARK launch2-enter retained-registration-only
CUDA_RETAINED_CALLBACK count=1 user=0x12345678
MARK launch2-return rc=0 callbacks=1
```

Machine classification:

```
trampoline[0] unpacker=0x7ffff7e75610 ... unpacker_in_retired_wrapper=0
```

The embedded guest unpacker is outside every retired wrapper mapping. The same generation-1 retained native registration successfully calls the guest after a forced moved wrapper reload.

## Conclusion

This is direct ownership evidence for the resident-bridge mechanism in the CUDA nested/deferred callback case:

```
local callback allocation
  -> HostToGuestTrampoline.GuestUnpacker belongs to unloadable wrapper
  -> wrapper unload retires its mapping
  -> retained callback exits 139

resident callback allocation
  -> HostToGuestTrampoline.GuestUnpacker belongs outside unloadable wrapper
  -> wrapper unload/reload does not retire the unpacker
  -> retained callback returns successfully
```

The earlier sequential same-job `resident=139` result is superseded by this isolated-run trace. The exact source of that earlier harness contamination is not yet established; do not attribute it to a specific FEX component without evidence.

## Remaining control

Run `31788089785` did not invoke the CUDA callback before generation-1 unload. A follow-up trace workflow now adds a pre-close `cuGraphLaunch` control. It must prove the exact callback path executes while generation 1 is mapped before the post-reload lifetime result is accepted as the final CUDA A/B checkpoint.
