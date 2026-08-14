# CUDA direct role-aware resident bridge — parser-free moved-reload proof — 2026-08-14

## Result

Branch:

`teamleaderleo/FEX:diagnostic/cuda-direct-role-bridge-f3ab-20260814`

Exact product base:

`f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`

Workflow run:

`31791958327` — both isolated ARM64 matrix jobs passed.

This is the first CUDA retained-callback lifetime proof using **direct thunkgen bridge definitions and typed accessors only**. The branch contains no `LinuxFieldwork/extract_guest_bridge.py`, and the workflow's provenance gate verifies there are no `ThunkLibs`, `FEXCore`, or `Source` changes relative to the exact product commit before applying the diagnostic transforms.

## Generator path

Resident arm uses:

```
thunkgen_guest_libcuda.inl
thunkgen_bridge_libcuda.inl
thunkgen_bridge_accessors_libcuda.inl
```

The unloadable wrapper includes the generated accessor fragment and routes:

- dynamic PFN invokers through `FEXGetResidentCallerForHostFunction`;
- generated callback allocations through `FEXAllocateResidentHostTrampolineForGuestFunction`.

The companion includes `thunkgen_bridge_libcuda.inl` and is linked `DF_1_NODELETE`.

No generated-C++ parser or post-extraction bridge copy is involved.

## Role evidence

The direct role-aware CUDA bridge contains the normal CUDA caller surface plus one generated nested callback-member unpacker for `CUDA_HOST_NODE_PARAMS_st::_0`:

```
FEX_BRIDGE_ROLE ... caller=0 unpacker=1 ... void (void *)
```

The callback signature hash is:

```
b62eaf2cec768f827f7500f0e98ef0d9c299071c87e2685c70bcaa36f65d36ff
```

The rest of the dynamic CUDA API surface is emitted as caller roles where required.

## Local arm

Pre-close control succeeds:

```
GEN1 ... add=0x7ffff7ea4b80 launch=0x7ffff7ea6160 callback=0x55fe4c991a20 ranges=5
FEX_TRAMP_CREATE unpacker=0x7ffff7ea8040 target=0x55fe4c991a20
FEX_TRAMP_CREATED trampoline=0x7ffff7e5b000 unpacker=0x7ffff7ea8040 target=0x55fe4c991a20
MARK launch1-enter pre-close-control
CUDA_RETAINED_CALLBACK count=1 user=0x12345678
MARK launch1-return rc=0 callbacks=1
```

Then generation 1 physically unloads, its five former wrapper mappings are reserved, generation 2 is forced elsewhere, and generation 2 invokes only the generation-1 native retained registration.

Ownership receipt:

```
retired_ranges=5
trampolines=1
trampoline[0] unpacker=0x7ffff7ea8040 target=0x55fe4c991a20 unpacker_in_retired_wrapper=1
```

Final result:

```
exit=139
```

No second guest callback executes.

## Direct resident arm

Pre-close control also succeeds:

```
GEN1 ... add=0x7ffff7eb0a70 launch=0x7ffff7eb2080 callback=0x55cdcee30a20 ranges=5
FEX_TRAMP_CREATE unpacker=0x7ffff7e788c0 target=0x55cdcee30a20
FEX_TRAMP_CREATED trampoline=0x7ffff7e37000 unpacker=0x7ffff7e788c0 target=0x55cdcee30a20
MARK launch1-enter pre-close-control
CUDA_RETAINED_CALLBACK count=1 user=0x12345678
MARK launch1-return rc=0 callbacks=1
```

After physical unload, reserved generation-1 mappings, and forced moved generation 2:

```
GEN2 add=0x7ffff7742a70 launch=0x7ffff7744080 moved=1
MARK launch2-enter retained-registration-only
CUDA_RETAINED_CALLBACK count=2 user=0x12345678
MARK launch2-return rc=0 callbacks=2
```

Ownership receipt:

```
retired_ranges=5
trampolines=1
trampoline[0] unpacker=0x7ffff7e788c0 target=0x55cdcee30a20 unpacker_in_retired_wrapper=0
```

Final result:

```
exit=0
```

Generation 2 never re-registers the callback.

## Conclusion

The direct role-aware thunkgen path reproduces the already-established causal CUDA lifetime result:

```
local generated unpacker
    -> embedded in FEX trampoline inside unloadable wrapper
    -> generation-1 unload retires it
    -> retained native callback exits 139

direct-generated resident unpacker
    -> embedded in FEX trampoline from libfex-cuda-bridge.so
    -> ordinary wrapper unload/reload does not retire it
    -> retained native callback reaches guest and returns
```

The Python generated-C++ extractor is therefore no longer part of the preferred architecture. It remains useful only as historical prototype evidence.

## Next integration gate

The build-system prerequisite list is now complete:

- direct Vulkan resident caller bridge: green;
- direct GL role separation: green;
- direct CUDA `callback_member` retained-callback lifetime: green;
- generalized Wayland per-library companion runtime regression: green.

Next: replace repeated experimental CMake wiring with a small **per-library** guest-bridge helper and rerun Vulkan, CUDA, and Wayland without changing their runtime success criteria.
