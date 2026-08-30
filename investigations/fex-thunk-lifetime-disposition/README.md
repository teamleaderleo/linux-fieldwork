# FEX escaped-thunk lifetime: current disposition

Date: 2026-08-30

## Bottom line

The old Vulkan lifetime research is valuable evidence, but its 378-commit / 298-file draft pull
request is not a current product patch or a usable beginner entrypoint. This note separates the
parts that reached the owned FEX fork from the parts that remain hypotheses, containment options,
or research prototypes.

At this checkpoint:

- owned FEX `main` is `6593de606a6c19ea2ecbab2e8cd65552effa0bae`;
- the old Linux Fieldwork carrier is draft PR
  [`#669`](https://github.com/teamleaderleo/linux-fieldwork/pull/669) at
  `a0b556d72fb7d5e0b2fa65fadd674150a7be70e8`;
- the clean generator-only successor is FEX PR
  [`#23`](https://github.com/teamleaderleo/FEX/pull/23) at
  `b7b6ad0cdee20d4ba418856983dfb4b958c43a16`;
- no FEX library currently builds, installs, or uses a resident companion DSO;
- no current product target has gained `NODELETE` from this work.

## The bug class without the archaeology

When an x86 program asks a native library for a function pointer, FEX associates the native host
address `H` with x86-callable executable glue `T`:

```text
native function H -> FEX association -> guest adapter T -> packed host call
```

The native loader can keep `H` meaningful after the ordinary guest thunk wrapper unloads. If `T`
lives inside that wrapper, the association can outlive the executable mapping it names.

Invalidating a cache or rebinding `H` repairs later lookups. It cannot revoke an old machine-code
target from another thread that selected it immediately before unmap. Physical safety therefore
needs either:

1. executable glue whose lifetime outlives every escaped address; or
2. a full execution lease/hazard protocol before reclaiming that glue.

The historical Vulkan and GL controls demonstrated the first architecture with a small
process-resident per-library companion. That result does not mean the research prototype was
productized.

## Disposition ledger

| Research line | Current disposition | Authoritative owned-fork state |
| --- | --- | --- |
| Vulkan custom functions missing from dynamic proc lookup | **Merged** | FEX #1 routes the existing custom wrappers; #2 enforces exact route/declaration inventory; #11 explains the call flow. |
| Generated repacking erased `const` from pointees | **Merged** | FEX #5 preserves the qualifier. |
| Const custom repacking needed cleanup without guest writeback | **Merged** | FEX #14 separates host-only cleanup from mutable exit/copyback. |
| `MREMAP_FIXED` could leave destination translations valid | **Merged, separate bug** | FEX #6 invalidates the replaced destination. It is memory-map correctness, not the escaped-wrapper ownership repair. |
| Vulkan instance debug callback mediation modified a `const pNext` chain | **Merged, separate bug** | FEX #12 copies supported nodes into host-owned storage. The current explanation and ARM64 receipt are in [`fex-vulkan-instance-pnext-host-copy`](../fex-vulkan-instance-pnext-host-copy/README.md). |
| Direct driver loading can expose a guest callback to native host code | **Merged containment** | FEX #13 rejects this unsupported cross-ISA path instead of forwarding an unsafe callback. |
| Stable host `H` could retain an old CustomIR `T` after re-registration | **Merged** | FEX #15 performs exact CustomIR rebinding; #16 removes a fork-only disk-cache assertion that masked the oracle. This repairs future dispatch, not already-selected wrapper code. |
| Whole-wrapper `NODELETE` | **Demonstrated containment; not adopted** | Historical Vulkan/GL controls passed, but all wrapper code, globals, constructors and TLS remain process-long. No current FEX product target enables it. |
| Per-library resident companion | **Demonstrated architecture; product integration unresolved** | Historical Vulkan/GL unload/reload controls passed. Current FEX main still has wrapper-local `HostPtrInvokers` and fixed `CallbackUnpack` addresses. |
| First-class resident output from `thunkgen` | **Clean current-main candidate** | FEX #23 emits optional invoker/accessor outputs from one analysis pass and keeps ordinary output unchanged. It does not build a companion. |
| Callback-direction selection | **Clean current-main candidate** | FEX #23 emits unpackers only for signatures analysis saw as real callbacks. GL's current interface produces 736 invokers and zero generated unpackers. |
| Wrapper-owned custom callback targets | **Unresolved per-library work** | GL/Vulkan X11 helpers and other raw escape points are invisible to ordinary callback-parameter analysis and need explicit ownership declarations. |
| Logical stale-`H` policy after wrapper close | **Unresolved policy** | Resident executable safety does not decide whether an old handle should remain semantically callable or return a revoked result. |
| Reclaiming the resident bridge itself | **Deferred fallback** | Generation ownership plus an execution lease/hazard is needed only if process-long bridge code must also be reclaimed. No product implementation exists. |

## What was rejected or superseded

These old paths should not be revived as if they were equal current candidates:

- **Cache retirement alone:** fixes later lookup, not code already selected by another thread.
- **A mutable target cell alone:** a thread can load the old target immediately before retirement
  and branch after unmap.
- **Base-namespace-only runtime `NODELETE` promotion:** a NEWLM wrapper generation can still
  publish generation-owned callback state into persistent host state and then unload.
- **Function-arity callback heuristics:** signature shape does not prove callback direction.
  Thunkgen's semantic callback analysis supersedes this.
- **Generated-C++ scraping:** the diagnostic Python extractor proved the data shape, but one-pass
  first-class generator output supersedes it.
- **A hand-maintained giant Vulkan PFN list:** thunkgen already owns the deduplicated runtime
  signature set. Library-specific declarations should describe only semantic escape points the
  generator cannot infer.
- **Merging PR #669 wholesale:** it mixes raw receipts, abandoned carriers, alternative designs,
  workflow history and superseded policy into roughly 45,000 added lines. Preserve it as an archive,
  not as current product documentation.

## Current generator evidence

FEX PR #23 recovered only the central primitive onto current main. At clean candidate
`b7b6ad0cdee20d4ba418856983dfb4b958c43a16`:

- 61 focused helper/policy tests passed;
- exact CTest `ResidentBridgeGeneration.ThunkGen` passed 1/1;
- zero-callback and one-callback fixtures prove direction selection;
- a duplicate signature used in both directions retains one identity;
- an unproven unpacker request fails at compile time;
- current GL ordinary output is byte-identical with resident mode enabled;
- two current GL resident generations are byte-identical;
- GL emitted 736 ordinary signatures, 736 resident invokers and zero generated unpackers;
- bridge SHA-256 is `8e273e08607c9df9967004eaf140bdc35ebeb00c9a3e94dc07802e8113d0e8e6`;
- accessor SHA-256 is `a48f507a04dcddef16b051aa24b095472c591e3371e1327858282e0c3301f7ca`.

Those last two hashes exactly reproduce the accepted historical direction-aware artifacts. This is
generator equivalence, not a repeated GL runtime result.

The beginner code-reading path is
[`docs/ResidentThunkBridge.md`](https://github.com/teamleaderleo/FEX/blob/codex/resident-thunkgen-current/docs/ResidentThunkBridge.md).

## The next bounded decision

Do not replay the original Vulkan investigation or run a broad FEX matrix. The next work should be
split into explicit gates:

1. review and decide FEX #23 as a generator-only primitive;
2. separately preregister one per-library companion integration;
3. prove that the companion is the single adapter authority and that the ordinary wrapper still
   physically unloads;
4. measure bridge ELF bytes, relocations, load time and RSS/PSS before broadening libraries;
5. only then run the already-defined retained-call / forced-moved-reload oracle on ARM64;
6. keep logical stale-handle policy separate from executable mapping safety.

If bridge bytes or relocation cost are excessive, measure signature duplication before considering
cross-library deduplication. Do not add global sharing merely because the signature hash exists;
parameter annotations and wrapper semantics may make nominally equal C signatures incompatible.

## Evidence and contact boundary

Draft PR #669 and its Actions receipts remain the historical archive. Closing that draft after this
disposition is published does not delete its branch, commits, workflow logs or artifacts.

All implementation and CI work described here is on repositories owned by `teamleaderleo`. No
upstream FEX issue, pull request, comment, review, reaction or other contact is authorized or
created by this disposition.
