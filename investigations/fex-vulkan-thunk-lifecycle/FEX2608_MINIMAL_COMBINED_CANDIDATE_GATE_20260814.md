# Minimal exact-FEX-2608 combined lifetime candidate gate — 2026-08-14

## Result

The integrated lifetime candidate no longer needs the earlier host-H / CustomIR retirement experiment to pass the exact-FEX-2608 combined gate.

Minimal candidate:

- exact base: `e869aa644a16e4332cdc15c1ea0b4d13d482385d`
- branch: `candidate/fex2608-combined-thunk-lifetime-minimal`
- commit: `966b65cbc9727c92ab9a3f12ccd4a8fde4828562`
- branch: `https://redirect.github.com/teamleaderleo/FEX/tree/candidate/fex2608-combined-thunk-lifetime-minimal`
- one commit ahead / zero behind exact FEX-2608

Validation:

- `https://redirect.github.com/teamleaderleo/FEX/actions/runs/31793889098`
- conclusion: success
- artifact: `fex2608-minimal-candidate-31793889098`
- artifact digest: `sha256:c05d13a596575b2f10777da216997414d12ca904f83d15367bc1c71463a99396`

The branch was pushed only after all four runtime gates passed.

## What was removed

Starting from the already-green clean candidate `09197342dd27cbd2f9d68b901c8dde6862d484fd`, the minimality experiment restored the exact FEX-2608 versions of the seven files that had changed only for host-H / CustomIR retirement:

- `FEXCore/Source/Interface/Context/Context.h`
- `FEXCore/Source/Interface/Core/Core.cpp`
- `FEXCore/Source/Interface/Core/LookupCache.h`
- `FEXCore/include/FEXCore/Core/Context.h`
- `FEXCore/include/FEXCore/HLE/SyscallHandler.h`
- `Source/Tools/LinuxEmulation/LinuxSyscalls/Syscalls.h`
- `Source/Tools/LinuxEmulation/LinuxSyscalls/ThreadManager.h`

It also removed the `LinkedHostClaims` / `ActiveHostToGuest` bookkeeping and host-H transition work from `Thunks.cpp`, and restored dynamic thunk linking to the original:

```cpp
CTX->AddThunkTrampolineIRHandler(args->original_callee, args->target_addr);
```

The callback descriptor transaction remained intact.

Relative to the clean candidate, this reduction removed 218 lines while adding 33 lines in the rewritten callback-only commit path:

```text
8 files changed, 33 insertions(+), 218 deletions(-)
```

## Minimal candidate scope

The resulting exact-FEX-2608 delta is now only nine files:

```text
Source/Tools/LinuxEmulation/LinuxSyscalls/SyscallsSMCTracking.cpp
Source/Tools/LinuxEmulation/Thunks.cpp
Source/Tools/LinuxEmulation/Thunks.h
ThunkLibs/GuestLibs/CMakeLists.txt
ThunkLibs/libvulkan/ExtractBridgeSymbols.py
ThunkLibs/libvulkan/ExtractBridgeThunks.py
ThunkLibs/libvulkan/Guest.cpp
ThunkLibs/libvulkan/GuestBridge.cpp
ThunkLibs/libvulkan/Host.cpp
```

Overall diff against FEX-2608:

```text
9 files changed, 413 insertions(+), 46 deletions(-)
```

This isolates the two repair families supported by the causal evidence:

1. transactional descriptors for host -> guest callbacks whose guest code follows mapping lifetime;
2. a resident Vulkan bridge for FEX-generated executable addresses intentionally allowed to escape the normal wrapper lifetime;
3. the independent Vulkan debug-report lookup routing correction.

## Gate results

### Active callback drain

```text
INFLIGHT close-done-before-release=0
INFLIGHT worker-returned rv=70053
INFLIGHT dlclose-returned rc=0
INFLIGHT child stale-first-callback exit=113
INFLIGHT DRAIN_PASS
```

### Failed munmap rollback / callback arrival during Draining

```text
TXWAIT before-release munmap-done=0 B-done=0
TXWAIT A-returned rv=70053
TXWAIT munmap-returned rc=-1 errno=22
TXWAIT B-returned rv=70063
TXWAIT stale-after-close-exit=113
TXWAIT PASS
```

### Saved dynamic Vulkan PFN after wrapper unload

```text
PROBE return where=before-close result=0 version=0x403113
PROBE after-close maps=11
PROBE return where=after-real-close result=0 version=0x403113
PROBE saved-dynamic-pfn-returned-after-close
```

### Real debug-report route plus split lifetime

```text
COMBINED create-instance result=0
COMBINED debug-report-created result=0
COMBINED debug-report-destroyed
COMBINED instance-destroyed
COMBINED after-app-close wrapper-mapped=0
COMBINED post-close-dynamic-version result=0 version=0x403113
COMBINED PASS
```

## Conclusion

The host-H / CustomIR retirement machinery is unnecessary for the tested combined repair. Removing it leaves all four outcomes unchanged.

That strengthens the preferred ownership split:

- FEX-generated executable bridge code that escapes a wrapper receives process lifetime in a small resident bridge;
- guest-owned callback code remains unloadable behind stable generation-specific descriptors with active drain and transactional revoke/rollback.

CustomIR retirement remains possible hygiene for other cases, but it is outside the minimal candidate justified by this Vulkan/callback evidence.

No upstream `FEX-Emu/FEX` interaction was performed.
