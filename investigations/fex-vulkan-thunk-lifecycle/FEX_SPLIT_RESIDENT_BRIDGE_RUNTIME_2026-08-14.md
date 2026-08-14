# FEX-integrated split resident bridge runtime

Date: 2026-08-14

## Result

A stock-FEX synthetic thunk experiment now demonstrates the split resident bridge architecture **inside FEX's real thunk dispatch machinery**, rather than only as a standalone loader model.

The experiment changes the guest thunk fixture, not FEX core runtime behavior:

```text
unloadable wrapper DSO
    owns wrapper-specific registration/state
    DT_NEEDED -> resident bridge DSO

resident bridge DSO (DF_1_NODELETE)
    owns generation-neutral CallHost-style H adapter
    owns fixed callback unpacker

main guest executable
    owns stable callback target
```

The wrapper physically unloads. The executable addresses that FEX retains/exposes process-long live outside that wrapper and remain executable.

Owned-FEX branch: `ci/thunk-callback-descriptor-20260814`.

Carrier commit used by successful runtime: `ee6800079d03a5f5fb0748284b343e1afe9ff6c7`.

Workflow run: `31775288520`.

Artifact: `fex-split-resident-bridge-31775288520`.

Artifact digest:

```text
sha256:5b274e00cf783a441d397647a67355191b52eb24601adb36a155aaa31c70f924
```

Reviewed stock FEX source: `71afe476751deac24adabd1adb575fd2337b6e0a`.

No FEX core lifetime patch was applied.

## Build identity

The resident guest bridge is a real x86-64 shared object with:

```text
SONAME: liblifetime-bridge.so
FLAGS_1: NODELETE
```

The unloadable wrapper has:

```text
NEEDED: liblifetime-bridge.so
RUNPATH: $ORIGIN
```

The bridge exports the process-lived adapter/unpacker symbols:

```text
lifetime_bridge_callhost_a
lifetime_bridge_callhost_b
lifetime_bridge_guest_unpacker
```

The wrapper owns only registration and generation-specific wrapper state.

## Runtime matrix

The runtime executes:

```text
--force-different --alias --cycles 5
```

and exits `0`.

Each cycle proves the same sequence.

Before unload:

```text
resident bridge maps            5
wrapper generation              N
pre-unload host->guest callback  rv=70053 want=70053
```

After `dlclose(wrapper)`:

```text
old invoker after dlclose   -> r-xp .../liblifetime-bridge.so
old unpacker after dlclose  -> r-xp .../liblifetime-bridge.so
proof: wrapper unmapped while bridge dependencies remain executable
```

Critically, before any wrapper reload or fresh registration:

```text
split retained Link after close      rv=29 want=29
split retained callback after close  rv=70073 want=70073
```

So stock FEX's already-retained bridge state remains valid even though the wrapper that created/registered it is physically gone.

The wrapper is then forced through a different load generation while the resident adapter remains identical:

```text
reload invoker       old=0x...c150 new=0x...c150 SAME
native host stable   old=0x...0860 new=0x...0860
reloaded wrapper generation  100N want=100N
```

Retained pre-registration state remains valid after reload as well:

```text
child retained callback reload  rv=70083
child retained callback reload  exit=0
```

Fresh registration/current callback paths also succeed.

The same behavior repeats for five wrapper generations.

## Why this is different from whole-wrapper NODELETE

The wrapper itself is demonstrably unmapped. Only the bridge glue whose addresses escape into process-owned FEX/host state is resident.

That preserves a meaningful wrapper unload/reset boundary while preventing FEX from retaining executable addresses into a reclaimed wrapper generation.

The experiment intentionally models the two relevant classes:

### Dynamic H→T

The native host function H is linked to a generation-neutral `CallHostFunction` surrogate in the resident bridge DSO. FEX can cache/compile/select that adapter process-long without depending on wrapper lifetime.

### Host→guest callback

The fixed callback unpacker lives in the resident bridge. The callback target lives outside the wrapper in the main guest executable, analogous to Vulkan's X11 target functions belonging to libX11 rather than `libvulkan-guest.so`.

The retained host callback therefore remains valid after wrapper unload without mutating or revoking its trampoline.

## Relationship to the proven in-flight race

The ordinary retirement/rebind candidate loses a forced race when another thread has already selected old wrapper-owned executable code before teardown. Cache invalidation cannot revoke that selected host-code pointer.

The split architecture attacks the dependency instead of trying to reclaim it: the selected adapter itself is process-resident, so wrapper physical unmap cannot invalidate that adapter address.

This successful run does not yet include the explicit `TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md` barrier. That exact race should be rerun with the split fixture as the next discriminator.

## What remains to integrate in FEX proper

This fixture manually separates resident bridge code from wrapper code. A real FEX implementation would need generator/build integration that emits or deduplicates process-resident signature glue.

The likely reusable units already exist conceptually:

- `CallHostFunction<signature>` / `GetCallerForHostFunction(signature)` for native-H adapters;
- `CallbackUnpack<signature>::Unpack` for fixed callback unpackers;
- existing generated thunk/signature hashes as compatibility/deduplication identity.

The central `ThunkLibs/GuestLibs/CMakeLists.txt` already constructs all guest thunk targets, so a per-bitness resident bridge target can be integrated centrally rather than per Vulkan function.

Library-specific wrapper code, constructors, mutable globals, and normal SONAME ownership can remain in unloadable wrapper DSOs.

## Evidence boundary

This is a FEX-integrated synthetic thunk test, not yet the generated Vulkan wrapper. It proves the architecture works with FEX's real H→T registration and host→guest trampoline machinery under stock FEX.

The next gates are:

1. forced selected-before-unmap race with the split fixture;
2. generator/CMake prototype for signature glue placement;
3. real generated Vulkan moved-reload/PFN and X11 callback tests using that generated split bridge.

All source changes are diagnostic/research code in owned repositories. Any upstream implementation must be independently derived and written by a human in compliance with FEX policy.

No upstream FEX interaction was made.