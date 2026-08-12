# Cloud Hypervisor QCOW refblock failure DIRTY containment audit

Updated: 2026-08-12
State: EXECUTED — CONTAINMENT VERIFIED, NOT FULL REPAIR
Worker/variant: LF-R634C
Canonical issue: #634
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Rust: `rustc 1.89.0 (29483883e 2025-08-04)`
Runner: Ubuntu 24.04.4
External-contact state: false; Cloud Hypervisor upstream remained read-only

## Question

Can a small recovery-containment change block #634's clean-reopen allocator corruption chain without claiming to solve recursive refcount ownership transactionality?

Candidate:

1. add a per-open `refcount_update_failed` flag to `QcowState`;
2. initialize it false in `parse_qcow()`;
3. if an externally requested `set_cluster_refcount_track_freed()` returns an error, set the flag before propagating the error;
4. final-owner shutdown may still flush metadata, but must not clear DIRTY while that flag is set.

The flag is deliberately conservative: it marks any tracked refcount-update failure, even if a particular error occurred before a mutation. The safety goal is recovery containment, not leak minimization.

## Required witness

Reuse #634's real 64 KiB / 16-bit region-crossing recursive ENOSPC state:

```text
refcount_table[0] -> Y
refcount(Y) = 0
outer tracked refcount update returns ENOSPC
```

Then require:

```text
refcount_update_failed == true
final-owner shutdown leaves QCOW DIRTY set
writable reopen takes refcount rebuild path
no post-rebuild state has Y both reachable from refcount_table and allocator-free
```

A negative control must show ordinary successful open/close still clears DIRTY.

## First execution: invalid recovery fixture, useful partial evidence

Workflow run: `31564421803`
Job: `94013228759`
Carrier head: `14b04db1e8006b6dfecb3dc8db5f560bc35567ec`
Artifact: `9128932118`
Artifact digest: `sha256:9d24e613ef460c4b07d97ee711d2f02c5d232d9298b2fc81933f167638dd94f7`

The candidate and probe compiled and the focused test reached the intended partial-failure state:

```text
REFBLOCK_DIRTY_CONTAIN pre_close target=0x40000 target_refcount=1 replacement=0x80000000 replacement_refcount=0 poisoned=true
REFBLOCK_DIRTY_CONTAIN post_shutdown dirty=true replacement=0x80000000
```

That proved the candidate did poison the session and retained DIRTY through final-owner shutdown.

However, the first probe used a tiny virtual image (`4 * 64 KiB`) while sparse-extending the physical file across two refcount regions. DIRTY recovery correctly rejected that impossible physical/declared geometry with:

```text
InvalidRefcountTableSize(720896)
```

So run 1 cannot establish recovery containment. This was a fixture incompatibility, not a counterexample to the candidate. It is retained here rather than discarded because it independently confirms the poison/retain-DIRTY half of the mechanism.

## Corrected execution: recovery containment passes

The corrected probe changes only the virtual geometry: a normal 4 GiB virtual QCOW image, matching the geometry already used by #634's parser-free-list realism control. The deterministic two-region physical horizon is then valid input to the real rebuild path.

Workflow run: `31564598000`
Job: `94013744702`
Carrier head: `fb9ba03d7bdde8fd4f5e1db1125110a7832b5e44`
Artifact: `9128995973`
Artifact digest: `sha256:4b2bec5bf421a3fc19382e4fca822e8521fd9533cc49017f8a4a3b0e04ee4e98`

All gates passed:

- exact source pin;
- containment candidate application;
- focused probe application/discovery;
- recursive-ENOSPC containment witness;
- ordinary clean-close negative control;
- full `block` library suite: `296 passed; 0 failed`;
- `cargo clippy --locked -p block --lib -- -D warnings`;
- `cargo fmt --all -- --check`;
- `git diff --check`;
- receipt and artifact upload.

Exact focused output:

```text
REFBLOCK_DIRTY_CONTAIN pre_close target=0x40000 target_refcount=1 replacement=0x80000000 replacement_refcount=0 poisoned=true
REFBLOCK_DIRTY_CONTAIN post_shutdown dirty=true replacement=0x80000000
REFBLOCK_DIRTY_CONTAIN reopened table0=0x30000 table1=0x40000 replacement_refcount=0 reachable=false free=true
```

Focused result: `1 passed; 0 failed`.

The rebuilt image does not merely increment Y's refcount. It discards the failed table topology and constructs new refcount blocks at `0x30000` and `0x40000`. Y remains refcount 0/free, but it is no longer reachable from the refcount table. This is safe reclamation rather than the reachable-free state from #634.

The ordinary lifecycle control also passed:

```text
formats::qcow::parser::unit_tests::dirty_bit_set_on_open_cleared_on_close_v3 ... ok
```

So the poison is not sticky for clean sessions: successful ordinary close still clears DIRTY.

## What this proves

**Recovery containment is viable for the verified #634 failure.**

The important sequence becomes:

```text
partial recursive refcount mutation
-> tracked refcount update returns error
-> poison this metadata session
-> final-owner shutdown may flush but leaves DIRTY set
-> writable reopen rebuilds refcounts before allocator reconstruction
-> failed replacement Y may be free only after it is no longer reachable
```

This specifically blocks #634's dangerous clean-close transition from:

```text
reachable + refcount 0 + DIRTY clear
```

to allocator-visible reuse.

## Boundary / what this does not prove

Passing this test does **not** prove the full #634 ownership invariant. The inconsistent refcount-table pointer can still exist in memory and can be flushed to disk during the poisoned session. Safety comes from refusing to certify that image clean and forcing recovery on the next writable reopen.

The complete repair still needs either:

1. bottom-up ownership of the recursive refblock dependency chain before publication; or
2. transactional rollback of refcount-table pointer swaps, cache mutations, refcounts, and allocator bookkeeping.

This containment also intentionally does not absorb #611. Current `shutdown()` separately ignores `sync_caches()` errors before clearing DIRTY. A complete hardening change may eventually unify the concepts around a broader "metadata state is not safe to certify clean" condition, but this experiment only validates poisoning on propagated tracked refcount-update failure.

## Scope review

The poison is applied at `set_cluster_refcount_track_freed()`, which is the caller-facing tracked mutation boundary for the mapping/deallocation operations relevant to #634. Recursive errors propagate through this boundary and therefore poison the session.

A resize cleanup path has a direct refcount-drop call whose error is deliberately ignored after old L1 clusters are already unreachable; the existing comment treats failure there as leaked space. This candidate intentionally does not poison the session for that leak-tolerant cleanup path.

## Disposition

**VERIFIED CONTAINMENT, NOT FULL REPAIR.**

For the executed recursive-refblock ENOSPC witness, retaining DIRTY after a tracked refcount mutation failure forces writable recovery to remove the reachable-free refcount-block state before allocator publication. Normal successful close behavior remains intact, the full block library suite passes, and Clippy/format/diff hygiene are clean.
