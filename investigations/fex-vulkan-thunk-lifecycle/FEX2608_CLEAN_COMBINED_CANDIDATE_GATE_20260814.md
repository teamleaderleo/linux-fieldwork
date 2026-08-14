# Clean exact-FEX-2608 combined lifetime candidate gate — 2026-08-14

## Result

The proven exact-FEX-2608 combined lifetime snapshot was cleaned of experiment-only `DIAG_*` stderr logging, squashed to one commit directly over FEX-2608, built from its own source, and passed the same four runtime gates before publication.

Exact base:

- FEX-2608
- `e869aa644a16e4332cdc15c1ea0b4d13d482385d`

Clean candidate:

- branch: `candidate/fex2608-combined-thunk-lifetime-clean`
- commit: `09197342dd27cbd2f9d68b901c8dde6862d484fd`
- branch: `https://redirect.github.com/teamleaderleo/FEX/tree/candidate/fex2608-combined-thunk-lifetime-clean`

Validation run:

- `https://redirect.github.com/teamleaderleo/FEX/actions/runs/31793400631`
- conclusion: success
- artifact: `fex2608-clean-candidate-31793400631`
- artifact digest: `sha256:5b67702b52d59ef2232a5c472054daccaed5a01383e55c409c5c5bf575cc23be`

The workflow pushes the clean branch only after all four runtime gates succeed.

## Cleanup boundary

The cleanup started from the exact proven research snapshot `d73d8b99790b311a7f53a538bcec54edc21171a5`.

A source scanner removed complete `fprintf(stderr, ...)` statements only when the statement contained the experiment prefix `DIAG_`. Guards then required:

- no remaining `DIAG_` matches in the touched FEX source areas;
- `git diff --check` success;
- every cleanup file to have zero added lines relative to the proven research snapshot.

The retained cleanup numstat is:

```text
0  7   FEXCore/Source/Interface/Core/Core.cpp
0  30  Source/Tools/LinuxEmulation/Thunks.cpp
```

So the cleanup removed 37 diagnostic-only lines and added zero lines relative to the already-passing research snapshot.

The resulting source was then reset/squashed to one commit whose direct parent is exact FEX-2608. Comparison against FEX-2608 is one commit ahead and zero behind.

## Direct build

The gate builds the clean candidate itself; it does not reapply the experiment transformers after cleanup.

It builds:

- FEX;
- FEXServer;
- `vulkan-host-64`;
- thunkgen;
- unloadable `libvulkan-guest.so`;
- resident `libfex-vulkan-bridge.so`.

ELF checks confirm the ordinary wrapper lacks `DF_1_NODELETE` while the bridge carries `DF_1_NODELETE` via the `-z,nodelete` link policy.

## Gate 1 — active callback drain

Observed output:

```text
INFLIGHT callback-entered-host-block
INFLIGHT close-done-before-release=0
INFLIGHT released-host-block
INFLIGHT worker-returned rv=70053
INFLIGHT dlclose-returned rc=0
INFLIGHT joined worker=70053 close=0
INFLIGHT child stale-first-callback exit=113
INFLIGHT DRAIN_PASS
```

The final close remains blocked while the callback is active, the callback returns normally, close then completes, and the escaped old trampoline rejects after retirement.

## Gate 2 — failed munmap rollback and wait-on-Draining

Observed output:

```text
TXWAIT A-entered-host-block
TXWAIT before-release munmap-done=0 B-done=0
TXWAIT released-A-and-queued-B
TXWAIT A-returned rv=70053
TXWAIT munmap-returned rc=-1 errno=22
TXWAIT B-returned rv=70063
TXWAIT joined A=70053 B=70063 munmap=-1 errno=22
TXWAIT stale-after-close-exit=113
TXWAIT PASS
```

The failed host `munmap(EINVAL)` rolls the transaction back to `Live`. The callback arriving during `Draining` waits for the outcome, then proceeds after rollback. A later real close commits revocation.

## Gate 3 — saved dynamic Vulkan PFN after physical wrapper unload

The probe tracks the mapping containing guest `vkGetInstanceProcAddr`, performs the final real close, and calls the saved dynamically returned `vkEnumerateInstanceVersion` PFN.

Observed:

```text
PROBE return where=before-close result=0 version=0x403113 maps=16
PROBE after-close maps=11 old-pfn=0x7ffff76c80f4
PROBE about-to-call-saved-dynamic-pfn=0x7ffff76c80f4
PROBE return where=after-real-close result=0 version=0x403113 maps=11
PROBE saved-dynamic-pfn-returned-after-close
```

FEX also logs that the native address is linked to a resident host invoker. The ordinary wrapper mappings disappear while the saved dynamic PFN remains executable through the resident bridge.

## Gate 4 — real debug-report routing plus split lifetime

Observed:

```text
COMBINED pre-create-version result=0 version=0x403113
COMBINED create-instance result=0
COMBINED dynamic-debug create=... destroy=...
COMBINED debug-report-created result=0
COMBINED debug-report-destroyed
COMBINED instance-destroyed
COMBINED after-app-close wrapper-mapped=0 ...
COMBINED post-close-dynamic-version result=0 version=0x403113
COMBINED PASS
```

This verifies both missing debug-report routes with a real `VK_EXT_debug_report` callback and the resident-PFN lifetime behavior after the normal Vulkan wrapper physically unloads.

## Candidate status

This branch is cleaner than the instrumented research snapshot and is directly gated. It still includes earlier thunk-H retirement / CustomIR hygiene from the experimental lineage in addition to the callback transaction and resident Vulkan bridge.

That extra machinery should receive a focused minimality review before any branch is designated as an upstream candidate. The primary Vulkan lifetime result remains the resident bridge; CustomIR retirement by itself was already falsified as the primary repair for the changed-base Vulkan failure.

No upstream `FEX-Emu/FEX` interaction was performed.
