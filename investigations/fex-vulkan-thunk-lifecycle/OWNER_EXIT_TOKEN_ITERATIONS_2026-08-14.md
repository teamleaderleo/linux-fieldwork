# FEX synthetic-H owner exit-token iterations — 2026-08-14

Internal experimental log. Pinned FEX base: `71afe476751deac24adabd1adb575fd2337b6e0a`.

This file keeps the owner-token prototype failures separate from the confirmed old-H ABA product behavior.

## Baseline product behavior

Every complete carrier baseline before the repair patch reproduces the same deterministic result:

```text
old H selected / pending T
T owner generation replaced
old H claim retired and H revoked
old H resumes
worker returns 222 without re-registration
```

The baseline is stable across the repair iterations below.

## Iteration 1 — helper anchor failure

Actions run: `31788267690`

- base FEX build: success
- amd64 race probe: success
- owner-aware lifetime candidate: success
- baseline old-H `222` reproduction: success
- owner-token patch application: failed before repair build

Failure:

```text
branch hint: expected one anchor in .../FEXCore/Source/Interface/IR/IR.h, found 0
```

Cause: helper expected a multiline BranchHint declaration; this FEX source generation uses a one-line enum.

Class: harness/patch-carrier failure. No repaired product code executed.

## Iteration 2 — BranchOps anchor failure

Actions run: `31791437685`

The helper passed the BranchHint edit and progressed farther, while the same baseline `222` reproduction passed again. Patch application then stopped on the BranchOps lowering anchor.

Class: harness/patch-carrier failure. No repaired product code executed.

## Iteration 3/4 — carrier cleanup and rollback token propagation

The BranchOps hook was moved to the actual constant-target `ExitFunction` lowering site. Rollback was also updated so a restored H recovers the OwnerID from its restored active claim before reactivation.

Superseded Actions copies were cancelled through workflow concurrency while these carrier edits landed.

## Iteration 5 — repair builds, first repaired execution exposes SIGILL

Actions run: `31792122589`

- job: `94741175618`
- artifact: `thunk-owner-exit-token-31792122589`
- artifact ID: `9216090811`
- artifact digest: `sha256:370f9614ae20fd2fb831aa6126b6f3387c51b62b77a5d136bf0428ce04c1a22b`

For the first time:

- baseline owner candidate compiled;
- baseline old-H `222` reproduction passed;
- owner-token patch applied;
- repaired FEX compiled;
- both repaired product cases executed.

Matrix:

```text
baseline=0
repair-no-reregister=132
repair-reregister=132
```

Both repaired cases die on the **first warm H call**, before the deterministic race is armed. The last lifetime diagnostics are the initial active registration:

```text
DIAG_REVOKED_H_ACTIVATE H=0x700000020000 T=... 
DIAG_OWNER_CLAIM_ACTIVE H=0x700000020000 T=... owner=0xe new=1
```

There is no:

```text
INFLIGHT warm ...
DIAG_OWNER_EXIT_ACCEPT ...
DIAG_OWNER_EXIT_REJECT ...
```

So this result says nothing about the owner mismatch logic yet. The new H block traps while being compiled/executed for its warm call.

### Cause

The prototype encoded OwnerID by reusing `ExitFunction`'s `CallReturnAddress` GPR operand:

```text
emit Constant(OwnerID)
  -> ExitFunction GPR operand
  -> register allocation
  -> ARM64 JIT tries IsInlineConstant(post-RA operand)
```

The post-RA operand is no longer guaranteed to be represented as an inline constant. The diagnostic JIT assertion therefore traps while compiling synthetic H. Exit code `132` is consistent with the assertion/SIGILL path.

Class: repaired-prototype execution bug, before lifetime validation.

## Current transport correction

The next carrier removes OwnerID from IR GPR operands entirely.

OwnerID is stored in Context metadata keyed by synthetic H when the active H definition is installed. During ARM64 compilation of the thunk-only branch hint, the JIT queries:

```text
GetThunkTrampolineOwnerID(Entry /* H */)
```

and copies that value into the emitted exit-link record.

The custom IR returns to the ordinary `ExitFunction` operand contract; only its branch hint marks the exit as owner-checked.

The same metadata entry is erased when the H definition is removed and rewritten on activation/rollback/promotion.

Current carrier head after wiring this transport into the workflow:

```text
ci/thunk-owner-exit-token-repair-20260814
28f249dd88b379334f01b8aab13b40da7174be31
```

Actions run: `31793149026`.

## Generality limit already known

Even if this VMA OwnerID token closes the `MAP_FIXED` ABA, `MREMAP_DONTUNMAP` proves it cannot be the universal validity token: old and moved targets can share the same OwnerID while executable content leaves the old address.

The eventual general design is the per-H/active-claim generation recorded in `H_GENERATION_DISPATCH_DESIGN_2026-08-14.md`. The VMA-owner token remains a useful narrow causal experiment for the witnessed same-address MAP_FIXED generation transition.
