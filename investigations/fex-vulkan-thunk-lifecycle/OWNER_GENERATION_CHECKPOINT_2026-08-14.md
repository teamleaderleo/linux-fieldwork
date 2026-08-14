# FEX thunk owner-generation checkpoint — 2026-08-14

## Scope

Internal research only. This checkpoint resumes the Vulkan/thunk-lifetime investigation at FEX base `71afe476751deac24adabd1adb575fd2337b6e0a` and records the newer generic lifetime work around FEX-created `H -> T` bridges, mapping generations, destructive VM operations, and concurrency.

No upstream contact is authorized or performed. FEX's no-AI-code contribution rule still applies; the owned-fork code below is diagnostic/causal research, not an upstream-ready contribution.

## Strongest new result: old synthetic H can cross a T owner generation

A deterministic ARM64 Actions fixture proved a FEX-created bridge can retain only the numeric target address after its owning mapping generation has retired.

Fixture sequence:

1. anonymous executable mapping `T`, owner generation `0xe`, returns `111`;
2. register synthetic `H -> T` and warm it;
3. RX -> RW -> RX keeps owner `0xe` while invalidating the warmed T link;
4. worker enters old compiled H and pauses in the H redirect immediately before T selection;
5. controller replaces T with `MAP_FIXED`, new owner generation, code returns `222`;
6. lifetime candidate drops owner-`0xe` claim and installs revoked H;
7. worker resumes the already-running old H redirect;
8. worker resolves the same numeric T and returns `222` without any new registration.

Key ordering from the retained receipt:

```text
DIAG_INFLIGHT_SELECTED ... stage=before-target-selection
DIAG_ROLLBACK_PREPARE ...
DIAG_MULTI_DROP H=... T=... owner=0xe
DIAG_MULTI_RETIRE H=... OLD=... NEW=0
DIAG_REVOKED_H_INSTALL H=...
DIAG_OWNER_MAP_FIXED ... old=0xe new=0x11 success=1
DIAG_ROLLBACK_COMMIT ...
DIAG_INFLIGHT_RESUME ... stage=before-target-selection
INFLIGHT worker-return value=222
INFLIGHT final worker-value=222 reregister=0
```

Interpretation: retirement protects future H lookup, while an H block already in progress still carries naked numeric T across the generation boundary. This is distinct from the ordinary native stale-function-pointer case because H is FEX-created metadata whose registration belongs to a specific target lifetime.

## Native concurrency boundary

Separate native controls on x86-64 and ARM64 capture a DSO function pointer, unload its owner on another thread, then resume the stale pointer. Both give:

```text
unmap = 139
pin   = 0
```

A second native control lets a callback enter its DSO, block in host/libc code, unload the DSO concurrently, and then resume; this also exits `139` on both architectures.

Therefore ordinary already-selected guest/native code follows native lifetime semantics. A broad stop-the-world or execution-drain guarantee would exceed that compatibility boundary. The owner-generation repair target is narrower: FEX's own synthetic H registration must not silently retarget itself to an unrelated mapping generation.

## Callback drain experiment

Descriptor-only callback retirement and a stronger execution-drain candidate were compared while a callback was blocked in host code during final owner unload:

```text
descriptor-only = 139
drain           = 0
```

The drain lets the active callback return before unload completes, then leaves the retained stale trampoline tombstoned.

The native entered-callback controls above establish that this drain is an extra lifetime guarantee. A same-thread adversary also proved the unconditional drain can self-deadlock:

```text
descriptor-only = 139
drain           = 124
```

The drain receipt contains `DRAIN_WAIT active=1` with no completion because the callback calls `dlclose` on its own owner while holding its active lease. Keep drain as a diagnostic upper bound unless a narrower FEX-owned obligation is identified.

## MREMAP_FIXED discovery: two independent defects

With `H -> destination(111)` and `source(222)`, then:

```c
mremap(source, page, page, MREMAP_MAYMOVE | MREMAP_FIXED, destination)
```

the owner-aware candidate initially showed:

```text
direct destination immediately after move = 111
permission-only invalidation
same destination afterward                 = 222
H afterward without re-registration        = 222
fresh owner-0xf registration               = standby
```

This split two defects:

1. translated destination code survived the destructive replacement;
2. the old destination owner claim remained active, so the moved source's owner-`0xf` claim became standby.

Source inspection matched the receipt: `InvalidateCodeRangeIfNecessaryOnRemap()` invalidated the old source when `OldAddress != NewAddress` and omitted the overwritten `MREMAP_FIXED` destination.

## MREMAP_FIXED causal repair — green

Internal FEX carrier:

- branch: `ci/mremap-fixed-lifetime-repair-20260814`
- carrier head: `8116e9693909c0d74e4686c2fcffe922b3fcd21f`
- pinned FEX base: `71afe476751deac24adabd1adb575fd2337b6e0a`
- Actions run: `31788718250`
- job: `94730467825`
- artifact: `mremap-fixed-lifetime-repair-31788718250`
- artifact ID: `9214642193`
- artifact digest: `sha256:693d4a0ee59aaeef2ddb63aedd3f66008fd2c218dd61d21dd046aad7a3706754`

Candidate mechanism:

- prepare retirement transactions for the old source range and the overwritten fixed destination range;
- defer syscall failure return until rollback can run outside the VMA critical section;
- rollback prepared retirements on syscall failure;
- commit on success;
- keep the existing old-source remap invalidation;
- additionally invalidate the fixed destination translated-code range on success.

Observed matrix:

```text
fail=0
no-reregister=139
reregister=0
```

Failure rollback control:

```text
DIAG_MREMAP_PREPARE_SOURCE ...
DIAG_MREMAP_PREPARE_DEST ...
DIAG_ROLLBACK_PREPARE token=0x1 ... hosts=1
DIAG_MULTI_DROP H=... owner=0xe
DIAG_REVOKED_H_INSTALL H=...
DIAG_ROLLBACK_RESTORE H=... claims=1
DIAG_ROLLBACK_DONE token=0x1 ...
DIAG_MREMAP_ROLLBACK result=0xffffffffffffffea ...
MREMAP_REUSE rollback errno=22 (Invalid argument) direct=111 H-value=111
```

Successful no-reregister control:

```text
DIAG_MULTI_DROP H=... owner=0xe
DIAG_REVOKED_H_INSTALL H=...
DIAG_ROLLBACK_COMMIT token=0x1 snapshot=1
DIAG_MREMAP_INVALIDATE_DEST ...
MREMAP_REUSE direct-before-invalidate value=222
MREMAP_REUSE direct-after-invalidate value=222
DIAG_REVOKED_H_COMPILE H=...
```

The process then exits `139` on the revoked H call, as intended for the diagnostic tombstone.

Successful explicit re-registration control:

```text
DIAG_MREMAP_INVALIDATE_DEST ...
MREMAP_REUSE direct-before-invalidate value=222
DIAG_REVOKED_H_ACTIVATE H=... T=...
DIAG_OWNER_CLAIM_ACTIVE H=... T=... owner=0xf new=1
MREMAP_REUSE reregistered H=... T=...
MREMAP_REUSE final H-value=222 reregister=1 direct-before=222 direct-after=222
```

This closes the two defects demonstrated by the `MREMAP_FIXED` fixture while preserving rollback after an invalid fixed move.

## Owner-token repair experiment — active

Goal: bind an in-flight synthetic H exit to the target owner generation that created it, while leaving ordinary guest exits unchanged.

Prototype design:

- H custom IR receives `(H, T, OwnerID)`;
- its exit-link record carries trailing `{ThunkHost, ThunkOwnerID}` metadata;
- only synthetic H uses a private `ThunkOwnerCheck` branch hint;
- after the deterministic old-H pause and before selecting T, the exit linker compares the current T owner to the recorded owner;
- mismatch redirects lookup through H's current definition;
- revoked current H should fault in the no-reregister case;
- a legitimate fresh registration should activate current H for the new owner and return `222`.

Expected A/B/C:

```text
owner baseline, no new registration     -> old H crosses generation -> 222
owner-token repair, no registration     -> owner mismatch -> revoked H -> 139
owner-token repair, explicit register   -> owner mismatch -> current H -> 222
```

First repair attempt:

- run: `31788267690`
- artifact ID: `9214538710`
- artifact digest: `sha256:3c4c1393ded64a494a4a40f16c80b2dbf75801ef11400ba3d86e50481000a82c`
- base build, probe, owner candidate, deterministic pause, and baseline `222` reproduction all passed;
- repair application stopped before product build because the helper expected a multiline `BranchHint` enum while this source generation uses a one-line enum.

Retained first harness failure:

```text
branch hint: expected one anchor in .../FEXCore/Source/Interface/IR/IR.h, found 0
```

The helper now matches the exact one-line enum. Current rerun:

- branch: `ci/thunk-owner-exit-token-repair-20260814`
- head: `78448300426fcb3655a441765cadd84a5491b3ee`
- run: `31791437685`
- state at checkpoint: base FEX build in progress.

## Next discriminators

After the owner-token A/B/C finishes, attack these in order:

1. **Warm direct-link control:** let H->T become directly linked, perform the destructive T transition, and verify normal target invalidation/delinking still returns through the owner check. This removes the fixture's explicit pre-race relink reset.
2. **Promotion race:** active claim A plus standby claim B; pause an old A bridge, retire A so B becomes active, resume old A, and require the old token to bounce through current H/B rather than crossing into an unrelated A-address generation.
3. **Rollback while H is paused:** failed destructive replacement after H has entered should restore the old owner claim; resuming the old H token should accept owner A and return `111`.
4. **`MREMAP_DONTUNMAP` discriminator:** source lifetime semantics differ because the old source VA remains mapped. Re-check the two-range retirement rule before generalizing the `MREMAP_FIXED` repair to this flag combination.
5. **`shmdt` owner transition:** once mapping-generation semantics are stable across mmap/mremap, test shared-memory detach with the same claim/tombstone model.

## Evidence boundary

The owner-generation and remap results are synthetic real-FEX ARM64 Actions experiments against the pinned source revision above. They establish mechanisms and causal repairs for FEX-created dynamic H bridges. They do not by themselves reproduce the historical hosted `vulkaninfo` exit-139 environment, whose reconstructed llvmpipe runs later exited cleanly. The original application failure remains environment/order-sensitive; the lower-level fixtures give the stronger lifetime discriminators.