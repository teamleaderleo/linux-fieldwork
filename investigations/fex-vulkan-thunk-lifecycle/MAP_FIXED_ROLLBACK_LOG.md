# Failed `MAP_FIXED` retirement rollback log

Date: 2026-08-14

## Starting point

[`MAP_FIXED_PRE_RETIRE_LOG.md`](./MAP_FIXED_PRE_RETIRE_LOG.md) proved the required successful-replacement order:

```text
retire H dependency before MAP_FIXED destroys generation 1
-> leave H revoked
-> same-address generation 2 cannot inherit H
-> explicit fresh LinkAddress claim can reactivate H
```

The causal pre-retire helper intentionally has no rollback if the kernel rejects the replacement. This log tests that transactional gap directly.

## Failed-syscall discriminator

Owned FEX branch:

```text
ci/map-fixed-failure-rollback-20260814
```

Probe commit:

```text
c800b31ec4970881e7566724e459b916e6aceed3
```

Workflow carrier:

```text
b03ca7f31da78531d0505a1f55992fe61d5d7574
```

Actions run:

```text
31781044914
```

The new `map-fixed-fail` mode does:

```text
map executable T with code returning 111
register H -> T
H() == 111
attempt mmap(T, page, PROT_READ, MAP_PRIVATE|MAP_FIXED, fd=-1, offset=0)
```

The request deliberately omits `MAP_ANONYMOUS` while using `fd=-1`, so Linux should reject the file-backed mmap. A failed mmap must leave the existing mapping at T intact.

Immediately after the syscall failure, before calling H, the probe executes T directly and requires:

```text
direct T() == 111
```

That is the key control. If direct T remains valid but H is revoked, the failure is specifically a lost thunk-claim transaction rather than destruction of guest code.

## Expected discriminator

Current integrated lifetime candidate, without the pre-MAP_FIXED helper:

```text
kernel rejects replacement
old mapping remains
H remains active
H() == 111
exit 0
```

Current candidate + pre-MAP_FIXED retirement without rollback:

```text
prepare retires H
kernel rejects replacement
old mapping remains and direct T() == 111
H remains revoked because no rollback exists
H call faults / cannot return 111
```

A green discriminator establishes that production prepare/commit/rollback is required independently of mapping-generation identity.

## Rollback requirement

Rollback must restore the complete affected claim state, not only the previously active target. For each affected H it needs the original ordered claim set plus active selection, because later owner retirement/promotion semantics depend on standby ordering.

A controlled diagnostic rollback can snapshot this state in the single-thread test. Production needs synchronization so new claims cannot race between prepare and rollback.

## External-contact state

No third-party/upstream interaction. All code, workflows, artifacts, and notes remain in repositories owned by `teamleaderleo`.
