# Multi-owner native-H claim promotion result

## Purpose

The dynamic thunk bridge is keyed by the native host function address `H`. Earlier changed-base experiments proved that one stable native `H` can outlive a guest wrapper generation and that stale `H -> T1` translated state can survive the physical lifetime of guest target `T1`.

This experiment asks a stronger ownership question:

> What if **two guest thunk owners are alive at the same time**, both legitimately receive the same native `H`, and each has a different guest bridge target `T`?

That state is enough to falsify any ownership model that assumes one process-global `H` implies one guest owner.

## Carrier and source under test

Owned FEX carrier branch:

`ci/thunk-multiowner-promotion-20260814`

Carrier commit:

`d80a32e56e8fb51c493e713670a5c804458b4ee0`

Workflow:

`.github/workflows/thunk-multiowner-promotion-arm64.yml`

Actions run:

`31769613134`

FEX source under test:

`71afe476751deac24adabd1adb575fd2337b6e0a`

Runner:

GitHub-hosted `ubuntu-24.04-arm` / AArch64.

The fixture creates two simultaneously loaded guest bridge owners, A and B. Both ask the same persistent host thunk for the native function address. Their guest-side invoker code lives in two different DSOs and therefore has different guest addresses.

## The simultaneous collision is real

Observed in both modes:

```text
native host A                   0x00007ffff7d80860
native host B                   0x00007ffff7d80860 (SAME)

A guest target T_A              0x00007ffff7da21b0
B guest target T_B              0x00007ffff7d7c1b0
```

Diagnostic registration sees the same relation directly:

```text
H=0x7ffff7d80860 T_A=0x7ffff7da21b0
H=0x7ffff7d80860 T_B=0x7ffff7d7c1b0
```

So this state is not a reload artifact where the first owner has already died. Two live guest owners simultaneously want:

```text
same native H
    -> target T_A owned by A
    -> target T_B owned by B
```

A single `unordered_map<H,T>` cannot represent both ownership claims.

## A/B mode 1 — single-owner retirement

The control uses the earlier exact owner-retirement diagnostic, which records one current target for each `H` and retires that relationship when the matching guest range goes away.

The two live registrations are observed:

```text
DIAG_MT_OWNER H=0x7ffff7d80860 T=0x7ffff7da21b0
DIAG_MT_OWNER H=0x7ffff7d80860 T=0x7ffff7d7c1b0
```

The fixture then reaches the multi-owner discriminator and exits with SIGSEGV:

```text
mode=single rc=139
```

Result:

```text
single process-global owner per H -> 139
```

This demonstrates that merely adding unload-aware retirement around a single `H -> T` owner record is insufficient once multiple live owners can claim the same persistent native function address.

## A/B mode 2 — retained claims with promotion

The experimental multi-owner variant changes the bookkeeping into:

```text
LinkedHostClaims[H] = [T_A, T_B, ...]
ActiveHostToGuest[H] = one currently selected live claim
```

For this discriminator, the first claim becomes active and later claims remain standby.

Observed registration:

```text
DIAG_MULTI_ACTIVE  H=0x7ffff7d80860 T=0x7ffff7da21b0
DIAG_MULTI_STANDBY H=0x7ffff7d80860 T=0x7ffff7d7c1b0
```

The active A route works:

```text
multi-owner active A            rv=1023 want=1023
```

A then closes. Its guest target becomes physically unmapped while B remains executable:

```text
multi-owner old A after close   0x00007ffff7da21b0 -> unmapped
multi-owner live B              0x00007ffff7d7c1b0 -> ... r-xp .../liblifetime-guest-b.so
```

Retirement removes A's claim and chooses the surviving B claim:

```text
DIAG_MULTI_DROP H=0x7ffff7d80860 T=0x7ffff7da21b0 range=0x7ffff7da1000+0x5000
DIAG_MULTI_RETIRE H=0x7ffff7d80860 OLD=0x7ffff7da21b0 NEW=0x7ffff7d7c1b0
```

Crucially, promotion is not just a metadata assignment. The diagnostic also retires/invalidate the old H-derived translated execution before installing the new target:

```text
DIAG_MT_SHARED H=0x7ffff7d80860 erased=1
DIAG_MT_THREAD H=0x7ffff7d80860 thread=<thread>
DIAG_MT_REMOVE_ALL H=0x7ffff7d80860 handler=1
DIAG_MT_RETIRE_ALL H=0x7ffff7d80860 ...
DIAG_MULTI_PROMOTE H=0x7ffff7d80860 T=0x7ffff7d7c1b0
```

The next call through the same native `H` reaches B and returns B's exact expected value:

```text
multi-owner promoted B          rv=2001035 want=2001035
```

The process exits `0`.

Later B retirement drops the final claim and leaves no replacement:

```text
DIAG_MULTI_DROP H=0x7ffff7d80860 T=0x7ffff7d7c1b0 ...
DIAG_MULTI_RETIRE H=0x7ffff7d80860 OLD=0x7ffff7d7c1b0 NEW=0
```

Result:

```text
retained claims + coherent active-claim promotion -> 0
```

## Exact A/B

```text
single H -> T owner bookkeeping       => 139
multiple live claims + promotion      =>   0
```

The successful path preserved these properties simultaneously:

- `H` remained bit-for-bit identical;
- A and B were live together before A closed;
- `T_A != T_B`;
- A physically unmapped;
- B remained physically mapped;
- H-derived translated state was invalidated during active-claim change;
- the same `H` subsequently dispatched to B and returned B's expected generation-specific result.

## What this proves

A full physical-unload design needs **claims**, not a single owner slot.

Conceptually the state needs to express something like:

```text
H
  claim(owner=A, generation=G_A, target=T_A, state=active)
  claim(owner=B, generation=G_B, target=T_B, state=standby/live)
```

Retiring A cannot mean `erase(H)`. It means:

```text
drop only A's claim
if A was active:
    choose an eligible surviving claim
    coherently invalidate old H-derived execution
    install/rebind H to the selected surviving target
else:
    leave the active route alone
if no claims remain:
    revoke/remove H
```

This is a different ownership model from both the current process-global `H -> T` mapping and the earlier one-owner retirement diagnostic.

## What the successful prototype does *not* prove

The experimental implementation uses a deliberately simple selection rule:

```text
first registered claim becomes active
later claims are standby
when active retires, promote Claims.front()
```

That policy is enough to test whether retaining and promoting surviving claims can solve the synthetic collision. It is **not established as the correct ABI/loader semantic rule**.

Important unanswered questions include:

1. If two loader namespaces receive the same native `H`, which namespace should an indirect guest call through raw H belong to?
2. Is the active claim determined by load order, current loader namespace, call-site provenance, guest thread/context, or some other owner token?
3. Can two claims for the same H both need to be callable concurrently from different guest contexts?
4. If yes, is a process-global raw H still a sufficiently expressive guest-visible identity?
5. If the active claim retires while another thread has already selected it, promotion still cannot retract that in-flight target; the earlier quiescence requirement remains.
6. If physical owner teardown aborts, claim promotion/retirement must participate in the same prepare/commit/rollback transaction established by the failed-munmap experiment.

## New design constraint

The physical-reclamation contract now needs at least these independent properties:

1. **generation identity** to defeat same-address ABA;
2. **multi-owner claim identity** because one H can have multiple simultaneously live T owners;
3. **registry and translated-code coherence** during H target changes;
4. **all-thread invalidation** for future selections;
5. **execution quiescence** for already-selected/already-entered old targets;
6. **transactional teardown semantics** so failed physical teardown does not retire live claims;
7. **stable escaped callback retirement** for host-to-guest trampolines.

A raw process-global `H -> T` map lacks enough identity to encode this contract.

## Implications for the three repair contracts

### Contract A — process-resident shared guest thunks

Residency collapses many generations that would otherwise compete over the same persistent H. If one thunk DSO image remains process-resident and ordinary `dlclose()` does not physically destroy its generated bridge code, the dangerous `H`-survives-while-`T`-dies transition disappears for that owner.

Namespace behavior still deserves direct testing. `DF_1_NODELETE` is scoped through dynamic-loader object semantics, while FEX's H-key CustomIR state is process-level; multiple namespaces may therefore expose a separate identity question even without physical unload.

### Contract B — true physical unload/reload

Multi-owner claims are now another required subsystem. An unload-aware `erase(H)` repair is too weak, because retiring one owner can destroy a valid surviving owner's route.

The full protocol is becoming a distributed owner transaction:

```text
identify owner generation
    -> mark only that owner's claims draining
    -> block new acquisitions for those claims
    -> choose/promote surviving claims where required
    -> coherently invalidate/rebind H-derived execution
    -> tombstone escaped callbacks for retiring owner
    -> drain in-flight old-generation execution
    -> commit physical teardown
    -> rollback claim state if teardown aborts
```

### Contract C — stable resident bridge runtime + unloadable wrapper-specific state

This result strengthens the appeal of giving escaped bridge identities an owner independent of wrapper mappings. However, the dispatch layer would still need enough context to choose between simultaneous logical wrapper owners if the same stable native H can map to owner-specific behavior.

The split design therefore reduces executable-lifetime risk but does not automatically answer namespace/owner selection semantics.

## Next discriminator — loader namespaces

The highest-value next experiment is a real `dlmopen()` / multiple-loader-namespace case:

```text
namespace N1 loads guest thunk owner A -> H, T_A
namespace N2 loads guest thunk owner B -> same H, T_B
both remain live
calls are made from each namespace/context
then one namespace closes its owner
```

Questions to answer:

- Does current FEX conflate both into one process-global H redirect?
- Does `DF_1_NODELETE` keep each loader namespace's guest object resident independently?
- Can a raw native H call be correctly routed without namespace/generation provenance?
- If not, should the stable process-owned bridge identity itself carry an owner token instead of exposing raw H as the complete guest-call identity?

That experiment will tell us whether multi-owner promotion is merely a teardown requirement or evidence that the current raw-H guest-visible identity is under-specified for namespace-aware operation.