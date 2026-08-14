# Provisional guest-thunk lifetime checkpoint — 2026-08-14

This is a checkpoint, not a conclusion to defend. It records the best current model, the evidence that moved the ranking, and the concrete observations that would make us change direction later.

## What is now proven

The FEX Vulkan lifetime defect is real at the generated-thunk/runtime boundary, not only a theory inferred from the original Apple M5 teardown.

A real generated-Vulkan moved-generation A/B shows that the native host PFN `H` can remain stable while the guest `CallHostFunction` invoker changes from `T1` to `T2`. Stock FEX fails after moved reload. Research retirement/revocation/rebind logic can retire the old H claim and successfully reactivate the same H against T2. The same result has been reproduced on exact FEX-2608 `e869aa644a16e4332cdc15c1ea0b4d13d482385d`.

That does not make physical unload safe. A forced in-flight runtime proves a worker can select old wrapper-owned executable state, leave all lookup/invalidation guards, then resume that already-selected host code after registry/cache retirement and physical wrapper unmap. Future dispatch can be perfectly retired while already-selected execution still faults.

Therefore generation rebinding and executable reclamation are separate problems.

## Current ranking

### 1. Whole-wrapper process residency — strongest near-term containment

`DF_1_NODELETE` on shared generated guest thunks is currently the smallest fully demonstrated policy.

Real generated/runtime evidence covers both concrete escaped-address directions after ordinary guest `dlclose()`:

- dynamic native Vulkan PFN -> guest invoker;
- persistent host Vulkan/X11 state -> guest callback trampoline/unpacker.

A real logical close/reopen test also shows stable GIPA/PFN behavior while the resident Vulkan wrapper remains usable.

The policy aligns the guest half with lifetime FEX already gives the other layers: FEX keeps the host thunk loaded, the generated host thunk keeps the native library loaded, and process-owned thunk/bridge registries remain alive. Physical guest-only unload is already a half-unload rather than a symmetric fresh native-library generation.

### 2. Split process-resident bridge runtime — strongest demonstrated long-term architecture

Recent stock-FEX split-bridge experiments move only escaped generic bridge executable state out of the unloadable wrapper:

- signature-specific guest -> host call adapters / special thunk glue;
- fixed host -> guest callback unpackers whose addresses escape wrapper lifetime.

The wrapper itself can physically unload and reload.

This design now survives the exact selected-before-wrapper-unmap race: a worker selects resident bridge code, the ordinary wrapper is physically unmapped, and the worker resumes and returns correctly. Repeated wrapper generations also preserve stable bridge addresses while wrapper addresses move.

That directly removes the proven reclamation race without requiring invalidation to revoke a host-code pointer that a thread already selected.

The remaining important step is generator/CMake integration followed by real generated-Vulkan validation.

### 3. Owner/generation + revocation + execution lease/hazard — full reclamation fallback

If even the escaped bridge code must be reclaimed, true execution ownership is still required. Retirement must block new acquisitions and wait for already-acquired execution to leave before unmap.

This is the strongest full-reclamation model but also the largest runtime synchronization change.

## Practical NODELETE cost checks

### Footprint

The current eight 64-bit shared product guest thunks were built together under the generic policy.

Measured RelWithDebInfo totals:

- ELF file sizes: 10,598,320 bytes (~10.11 MiB);
- page-rounded `PT_LOAD` memory: 1,843,200 bytes (~1.76 MiB).

Largest mapped contributions in that build were GL (~956 KiB) and Vulkan (~300 KiB).

This is not measured RSS and should not be reported as RSS. It does make the raw mapping-footprint objection considerably smaller than an unbounded-residency concern would suggest.

### Current wrapper state audit

Current product shared thunks reviewed: ALSA, Vulkan, DRM, Wayland, VDSO, GL, EGL, CUDA.

No reviewed wrapper establishes an explicit requirement for intermediate physical DSO destruction/reconstruction. Search-level controls found no explicit guest-thunk destructor implementation and no `thread_local` wrapper state under `ThunkLibs`.

Vulkan, GL, CUDA, and Wayland positively contain process-facing state that is consumed by host/FEX state with longer lifetime.

### Selective NODELETE

A selective CMake policy is mechanically viable. A build/flag experiment successfully made only Vulkan, GL, CUDA, and Wayland NODELETE while leaving ALSA, DRM, VDSO, and EGL ordinary; representative 32-bit Wayland also built correctly.

This is not evidence that the allowlist is safer. It adds classification maintenance and can miss a future bridge publisher. With the measured mapping total around 1.76 MiB, selective residency has not displaced the generic policy.

## Real compatibility caveat: loader namespaces

Blanket link-time NODELETE has a concrete glibc `dlmopen()` cost.

A standalone DSO repeatedly loaded with `dlmopen(LM_ID_NEWLM, ...)` and closed recycled for 40 iterations when ordinary. The NODELETE version exhausted glibc namespace slots at iteration 15.

A real FEX/Vulkan namespace loop did not distinguish the policies before another limit: both ordinary and NODELETE Vulkan wrappers stopped at iteration 12 because guest libc exhausted static TLS for new namespaces. Therefore the standalone NODELETE namespace-retention behavior is real, while the tested FEX/Vulkan workload currently hits a different namespace limit first.

This caveat belongs in any product policy discussion. Ordinary base-namespace `dlopen`/`dlclose` is a different case.

## Runtime promotion experiment — open discriminator

A native glibc experiment shows a DSO can remain ordinary on disk, then promote only its base-namespace instance with:

`RTLD_NOLOAD | RTLD_NODELETE`.

That keeps the base instance resident while NEWLM copies remain recyclable. This could avoid the link-time NODELETE namespace cost.

However FEX has a process-global native-PFN bridge registry. A secondary loader namespace can receive the same native H with a different guest T. If that secondary T is deliberately left unloadable, closing it may poison the H route used by the still-resident base namespace.

A real FEX/Vulkan adversarial run is in progress on the owned fork to test exactly this sequence. Until that result exists, runtime promotion is an optimization candidate, not the preferred policy.

## Things that would demote whole-wrapper residency

Any one of these would be a meaningful counterexample:

1. a real thunk whose guest constructor/destructor/TLS/static state must reset on logical close/reopen for correctness;
2. measured RSS/working-set cost that is unacceptable in real applications;
3. an application that correctly depends on the thunk mapping physically disappearing;
4. a real loader-namespace workload for which NODELETE materially breaks behavior that ordinary thunks support;
5. a future symmetric FEX host-thunk/native-library unload protocol that makes physical guest generations meaningful and coordinated.

If one appears, prefer the split resident bridge first. Escalate to owner/generation/lease only when bridge reclamation itself is required.

## Evidence boundaries still preserved

The original Apple M5 terminal transfer did not capture the immediate final H/R11/post-unload synthetic-entry edge. Do not rewrite that historical receipt as if it did.

The generic H->T lifetime mechanism is now independently proven with real generated Vulkan, including exact FEX-2608, so that missing historical edge is no longer the sole basis for repair design.

Other Vulkan findings remain separate from this lifetime checkpoint, including dynamic debug-report callback routing, NULL-instance GIPA semantics, and the independent allocation-callback work.

All implementation and CI work referenced here is on owned repositories/forks. Upstream FEX remains untouched. This checkpoint is intended to be revised or contradicted when stronger evidence appears.
