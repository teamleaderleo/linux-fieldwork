# Current FEX main thunk-lifetime audit — 2026-08-14

This is a read-only source comparison. No upstream FEX issue, pull request, comment, branch, commit, or other mutation was made.

Current upstream main inspected:

```text
f3ab82a73fb48271ee12a882c98bc5d823a2b4d1
```

Historical reproduced runtime:

```text
FEX-2608
e869aa644a16e4332cdc15c1ea0b4d13d482385d
```

## Result

The lifetime mechanisms implicated by the FEX-2608 investigation remain materially present on current main.

This does **not** prove that the exact `vulkaninfo` teardown crash still reproduces on current main; current main has not been run through the same application carrier here. It does mean the source-level ownership hazards are still relevant and should not be treated as release-2608-only archaeology.

## Dynamic native-PFN -> guest-wrapper bridge

Current `Source/Tools/LinuxEmulation/Thunks.cpp` still routes `LinkAddressToGuestFunction` through:

```text
CTX->AddThunkTrampolineIRHandler(original_callee, target_addr)
```

where the practical Vulkan roles are:

```text
H = native host function address
T = generated guest CallHostFunction<...> entrypoint inside a guest thunk DSO
```

Current `FEXCore/Source/Interface/Core/Core.cpp` still builds the thunk CustomIR with `GuestThunkEntrypoint` embedded as a constant exit target.

Therefore the compiled bridge is still discovered/compiled at the host-address key `H` while its executable dependency `T` may live in an independently unloadable guest mapping.

Invalidating the guest range containing `T` is not, by address identity alone, the same as invalidating the compiled bridge keyed at `H`.

## Duplicate/reload identity remains insert-only

Current CustomIR registration still uses `emplace` for the entrypoint map.

If an entry for `H` already exists, registration does not simply replace it with a new `T`; the existing creator/data are retained and the thunk layer can diagnose a mismatched second target.

That keeps the same reload/ABA concern identified in the FEX-2608 models: a repeated host address is not, by itself, sufficient load-instance identity for a newly loaded guest target generation.

## Host -> guest callback trampolines still retain raw guest addresses

Current `Source/Tools/LinuxEmulation/Thunks.cpp` still has host trampoline state containing the raw pair:

```text
GuestUnpacker
GuestTarget
```

and the cache identity is still based on those guest addresses rather than a DSO/load-generation owner token.

The copied executable host trampoline therefore still names guest executable addresses whose mappings can have an independent lifetime.

For Vulkan's X11 helper registrations, the important split remains:

```text
GuestUnpacker = wrapper-owned CallbackUnpack<...>::Unpack
GuestTarget   = guest X11 function
```

Keeping only the Vulkan wrapper resident protects the unpacker, not an arbitrary separately unloadable X11 target.

## Public API remains asymmetric for thunk retirement

The current public `FEXCore::Context` interface still exposes thunk trampoline registration but does not expose a matching thunk-specific remove/retire operation suitable for the Linux-emulation thunk layer.

There is internal CustomIR removal machinery, but a clean true-unload design would still need an explicit ownership/retirement interface instead of depending on an implementation downcast or address-range accident.

## Guest-wrapper build policy

Current main does not generally mark generated shared guest thunk wrappers `DF_1_NODELETE` in the common GuestLib build helper.

So the process-lifetime wrapper policy explored in Fieldwork remains a candidate policy change rather than something already adopted by current main.

## Interpretation

Two repair scopes remain distinct.

### Narrow process-lifetime wrapper policy

If FEX's contract permits generated guest thunk wrappers to remain mapped once loaded, `DF_1_NODELETE` directly prevents wrapper-owned `CallHostFunction` and `CallbackUnpack` code from disappearing underneath FEX/native bridge state. This is the smallest design for the demonstrated Vulkan wrapper failure class.

### True unload/reload support

If wrappers must really unload and later reload, the source still points toward the broader design explored in the lifetime model:

- load-instance/generation identity;
- owner-aware bridge registration;
- stable revocable indirection for externally retained host-callable bridges;
- retirement of compiled H-keyed paths that depend on a retiring T generation;
- safe handling of already-selected/in-flight transitions;
- only then unmap/reclaim the guest generation.

That broader mechanism is also required for arbitrary callback targets in unrelated guest DSOs, which a wrapper-only `NODELETE` policy cannot own.