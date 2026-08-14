# Exact FEX-2608 callback VM mapping gate — 2026-08-14

## Result

The generic host->guest callback descriptor repair now covers destructive guest VM operations beyond `munmap`, and the independently discovered `mremap` destination translation-cache defect has a separate focused repair.

Final integrated branch:

- `https://redirect.github.com/teamleaderleo/FEX/tree/candidate/fex2608-combined-thunk-lifetime-vm-codecache`
- tip: `24d7f251e6ab0afdb9d3f80d55e634139c6aef49`
- base: exact FEX-2608 `e869aa644a16e4332cdc15c1ea0b4d13d482385d`
- comparison: 3 commits ahead, 0 behind

Final integrated run:

- `https://redirect.github.com/teamleaderleo/FEX/actions/runs/31796492324`
- conclusion: success
- artifact: `fex2608-vm-lifetime-plus-codecache-31796492324`
- artifact digest: `sha256:2b1cf060e0723cc0c1bade4ff2156d68b9c781714d90ad5a81491180e343ffec`

The final run builds one FEX/Vulkan tree and requires the full VM mutation matrix, both original callback race gates, saved Vulkan PFN after physical wrapper unload, and the combined real debug-report path to pass before publication.

## Baseline VM-generation defects

A deterministic guest fixture publishes an escaped native host trampoline whose guest target is a tiny executable JIT page. Mapping operations then replace, move, shrink, detach, or preserve that guest generation. The old native pointer is called in a child so missing retirement becomes an observable exit status instead of losing the harness.

Corrected minimal-candidate baseline:

- run: `https://redirect.github.com/teamleaderleo/FEX/actions/runs/31795650272`
- branch under test: `candidate/fex2608-combined-thunk-lifetime-minimal`

Results:

```text
map-fixed              20
map-fixed-fail          0
map-noreplace           0
mremap-move             20
mremap-dest             11
mremap-shrink-tail      20
mremap-shrink-prefix    0
mremap-fail             0
mremap-dontunmap        20
shmdt                   20
shm-remap               20
```

The destructive cases demonstrate two stale-pointer forms:

- unmapped old generations can crash when the escaped host trampoline enters stale guest code;
- same-address replacement can resurrect an old escaped native pointer into a numerically reused guest address, an ABA failure.

The expected preservation cases remain callable: failed `MAP_FIXED`, `MAP_FIXED_NOREPLACE`, failed `mremap`, and a callback in the prefix retained by an in-place shrink.

## VM callback-retirement extension

The callback lifetime transaction was extended to mapping operations that can destroy or replace guest generations:

- `MAP_FIXED`: drain the requested destination range before the fallible host mapping; commit on success, roll back on failure;
- `mremap`: transactionally cover potential source retirement, shrink tail, and `MREMAP_FIXED` destination replacement; preserve the source descriptor when the mapping remains at the same address;
- `MREMAP_DONTUNMAP`: retire the old generation even though the old virtual range remains mapped;
- `SHM_REMAP`: drain the destination range before replacement;
- `shmdt`: preflight the tracked SysV attachment size, drain outside the VMA mutex, revalidate under the mutex, then commit/rollback around the host detach.

Overlapping drains reuse the existing descriptor `DrainRequests` accounting. Callback drain waits remain outside FEX's global thunk registry mutex and outside the VMA tracking mutex.

VM-lifetime branch:

- `https://redirect.github.com/teamleaderleo/FEX/tree/candidate/fex2608-combined-thunk-lifetime-vm`
- tip: `32745fe6289d1d35a0a76ebacb26a2857804dbe0`
- validation: `https://redirect.github.com/teamleaderleo/FEX/actions/runs/31796001853`

That run changes every stale destructive VM invocation into descriptor rejection status 113 while preserving the rollback/non-destructive cases. It also reruns the original active callback drain, failed-`munmap` rollback/wait, saved Vulkan PFN, and combined debug-report gates successfully.

## Independent `mremap` destination translation-cache defect

The mapping fixture exposed a second defect that is independent of callback descriptor lifetime.

With `MREMAP_FIXED`, FEX-2608's remap invalidation path invalidated translations for the old/source range when the address changed, but omitted the new/destination range. If executable destination code had already run, a replacement mapping at that same numeric address could continue executing the old cached translation.

The fixture makes the distinction visible:

- destination's old JIT code returns `70423`;
- moved source code returns `70433`.

Before the cache repair, a fresh callback registered after the remap still returned `70423`.

Focused independent branch:

- `https://redirect.github.com/teamleaderleo/FEX/tree/candidate/fex2608-mremap-destination-codecache`
- tip: `f42a66b4e9e23287ae22c82d83ad778d659dff87`
- validation: `https://redirect.github.com/teamleaderleo/FEX/actions/runs/31796099294`

Its single-file change invalidates `NewAddress/NewSize` when a remap moves. On exact FEX-2608 without callback retirement, the old escaped callback intentionally remains live for this focused test, but both old and freshly registered invocations now execute the moved source bytes (`70433`). Failed-remap and retained-prefix neighbors remain correct.

## Final integrated gate

The final branch applies the focused destination translation invalidation on top of the VM-lifetime branch.

All 11 mutation modes exit 0:

```text
map-fixed              0
map-fixed-fail         0
map-noreplace          0
mremap-move             0
mremap-dest             0
mremap-shrink-tail      0
mremap-shrink-prefix    0
mremap-fail             0
mremap-dontunmap        0
shmdt                   0
shm-remap               0
```

The key destination replacement now reports:

```text
MAPMUT mremap-dest stale-exit=113
MAPMUT mremap-dest fresh=70433
MAPMUT mode=mremap-dest rc=0
```

So both identities are current:

- the old escaped host trampoline remains bound to its revoked generation and rejects;
- a new registration at the reused guest address executes the newly mapped source code.

The original callback transaction gates also remain green:

```text
INFLIGHT close-done-before-release=0
INFLIGHT worker-returned rv=70053
INFLIGHT dlclose-returned rc=0
INFLIGHT child stale-first-callback exit=113
INFLIGHT DRAIN_PASS
```

and:

```text
TXWAIT before-release munmap-done=0 B-done=0
TXWAIT A-returned rv=70053
TXWAIT munmap-returned rc=-1 errno=22
TXWAIT B-returned rv=70063
TXWAIT stale-after-close-exit=113
TXWAIT PASS
```

Vulkan remains green in the same build:

- the ordinary `libvulkan-guest.so` physically unloads;
- a saved dynamic `vkEnumerateInstanceVersion` PFN still returns success through the resident bridge;
- a real `VK_EXT_debug_report` callback is dynamically resolved, created, destroyed, and followed by successful post-close PFN execution (`COMBINED PASS`).

## Exec image replacement audit

FEX's guest exec handler eventually performs a real host `SYS_execveat` in both paths: either the target image directly or `/proc/self/exe` for loader-mediated guest execution. A successful exec therefore replaces the host process image and discards the descriptor arena with every other process-local FEX object. If exec fails, the current guest image and descriptors remain. No separate callback-retirement transaction is needed for successful `execve`/`execveat`.

## Current ownership model

The evidence now supports the same two ownership rules across loader and VM lifetime boundaries:

1. FEX-generated executable bridge code intentionally returned beyond an unloadable wrapper receives process lifetime in a small resident bridge DSO.
2. Guest-owned callback code retains guest mapping lifetime, while escaped native pointers refer to permanent generation-specific descriptor identities. Mapping destruction/replacement drains active execution and transactionally revokes only when the destructive VM operation succeeds.

Numeric guest-address reuse never reactivates an escaped old native trampoline. Current translations at a reused address are separately invalidated when `mremap` replaces the destination mapping.

No upstream `FEX-Emu/FEX` interaction was performed.
