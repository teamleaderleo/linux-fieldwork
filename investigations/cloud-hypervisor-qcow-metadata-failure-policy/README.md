# Cloud Hypervisor QCOW metadata failure-policy integration

Updated: 2026-08-12
State: EXECUTED — INTEGRATION VERIFIED
Variant: LF-R611634I
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Related canonical issues: #611, #634
Rust: `rustc 1.89.0 (29483883e 2025-08-04)`
Runner: Ubuntu 24.04.4
External-contact state: false; Cloud Hypervisor upstream remained read-only

## Result

The two independently verified QCOW metadata failure policies compose correctly on one exact-current product tree:

1. **#634 allocator ENOSPC during recursive refcount ownership** — bounded per-region undo journal restores the pre-transaction logical state; the restored metadata synchronizes successfully and final-owner close may truthfully clear DIRTY.
2. **#611 actual metadata synchronization failure** — shutdown returns before clean certification, retains DIRTY, and writable reopen takes recovery; a later successful close clears DIRTY.

This is not a blanket “keep DIRTY forever” workaround. The same build distinguishes reversible allocator exhaustion from non-reversible/ambiguous synchronization failure.

## Authoritative execution

Workflow run: `31568806972`
Job: `94026190756`
Tested Fieldwork head: `c29cacfa83254593aba23c9e43b7368283514539`
Artifact: `9130513740`
Artifact digest: `sha256:80aae11ca1b34434ef815030d463ccb7751f086dedc4a5a8f2345b721f7ed7cf`
Exact source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`

Receipt gates:

```text
source_gate=success
candidate_gate=success
probes_gate=success
discover_gate=success
journal_rollback_gate=success
journal_success_gate=success
journal_eviction_gate=success
sync_failure_gate=success
clean_close_gate=success
default_suite_gate=success
io_uring_suite_gate=success
clippy_gate=success
hygiene_gate=success
```

Default block suite: `300 passed; 0 failed`.

io_uring block suite: `328 passed; 0 failed`.

Clippy with `--features io_uring -D warnings`, rustfmt, and `git diff --check` all passed.

## Reversible allocator ENOSPC remains clean-close safe

Primary rollback output:

```text
REFBLOCK_JOURNAL_ROLLBACK post_error target=0x40000 target_refcount=0 replacement=0x80000000 replacement_refcount=0 replacement_free=true unref_count=0
REFBLOCK_JOURNAL_ROLLBACK post_sync table0=0x30000 table1=0x0 old=0x30000
REFBLOCK_JOURNAL_ROLLBACK reopened table0=0x30000 replacement_refcount=0 replacement_free=true free_tail=Some(0x80000000)
REFBLOCK_JOURNAL_ROLLBACK allocator_reuse reused=0x80000000 table0=0x30000
```

The successful recursion control also passed unchanged:

```text
REFBLOCK_JOURNAL_SUCCESS target=0x40000:1 y=0x80000000:1 z=0x80010000:1 old=0x30000:0 old_tracked=true
REFBLOCK_JOURNAL_SUCCESS reopened table0=0x80000000 table1=0x80010000 target=1 y=1 z=1 old=0 old_free=true
```

The stronger dirty-sibling / forced-cache-eviction rollback also passed on the integrated tree:

```text
REFBLOCK_JOURNAL_EVICT post_error target1=1 target2=0 y=1 z=1 a=0 b=0 free=[
    0x180000000,
    0x100000000,
]
REFBLOCK_JOURNAL_EVICT post_sync table=[
    0x80000000,
    0x80010000,
    0x0,
    0x0,
]
REFBLOCK_JOURNAL_EVICT reopened table=[
    0x80000000,
    0x80010000,
    0x0,
    0x0,
] target1=1 target2=0 y=1 z=1 a=0 b=0 a_free=true b_free=true
```

So #611's conditional DIRTY clearing does not interfere with #634 rollback: after the reversible transaction is restored, normal metadata synchronization succeeds and clean close remains truthful.

## Actual synchronization failure remains dirty

Exact integrated output:

```text
QCOW_INTEGRATION_SYNC_FAIL sync_error kind=Other raw=None dirty_before_drop=true
QCOW_INTEGRATION_SYNC_FAIL post_failed_drop dirty=true
QCOW_INTEGRATION_SYNC_FAIL recovery_close dirty=false
```

Ordinary clean-close control:

```text
QCOW_INTEGRATION_CLEAN_CLOSE post_drop dirty=false
```

So #634's journal does not cause an actual `sync_caches()` failure to be mistaken for a reversible allocator transaction. The shutdown gate preserves DIRTY, writable reopen recovers, and a later successful close clears the bit normally.

## Integrated invariant

```text
allocator ENOSPC before irreversible metadata-write ambiguity
    -> bounded refcount transaction rollback
    -> restored metadata sync succeeds
    -> clean close allowed

metadata synchronization failure / uncertain durable effects
    -> do not certify clean
    -> retain DIRTY
    -> writable recovery before trusting allocator metadata
```

This split is stronger than either mechanism alone. The journal is not extended to arbitrary write failures, and DIRTY retention is not used to hide a reversible allocator transaction that can be restored exactly.

## Disposition

**INTEGRATION VERIFIED — REVERSIBLE ENOSPC ROLLS BACK AND CLOSES CLEAN; ACTUAL SYNC FAILURE RETAINS DIRTY AND RECOVERS.**

No Cloud Hypervisor upstream issue, PR, comment, review, email, reaction, or other interaction occurred or is authorized by this carrier.
