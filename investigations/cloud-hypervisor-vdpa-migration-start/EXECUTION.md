# Cloud Hypervisor vDPA failed migration start — execution receipt

Updated: 2026-08-12
Owning issue: #585
Exact upstream source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Carrier branch: `research/ch-migration-rollback-probes`
External-contact state: false; none occurred

## TL;DR

Exact-current execution proves the local vDPA migration-start state leak.

Current source sets `migrating=true` before checking whether the backend supports suspend or whether `suspend()` succeeds. A focused unit test forces the unsupported-suspend path, then asserts that a failed migration start must leave vDPA in normal runtime state. The baseline fails because `migrating` remains true.

A minimal candidate moves the flag assignment after successful suspend. The same test passes, along with rustfmt and `virtio-devices` Clippy with warnings denied.

## Exact receipt

Run / job:

```text
31550859874 / 93973079890
```

Source:

```text
cloud-hypervisor/cloud-hypervisor@1af93ac7035cda77cd87b0c18b1134ebb0928052
```

Toolchain:

```text
rustc 1.89.0 (29483883e 2025-08-04)
```

Exact test:

```text
vdpa::unit_tests::failed_start_migration_keeps_normal_runtime_state
```

Artifact:

```text
ID: 9124450044
SHA-256: 1d20f4d9dc1a809ad0c7af0584e7659fa3c24ff09e754dca392e8ae81abc7d45
```

## Baseline

Observed:

```text
BASELINE_RC=101
running 1 test
thread 'vdpa::unit_tests::failed_start_migration_keeps_normal_runtime_state' panicked:
failed start_migration must not authorize migration-only behavior
0 passed; 1 failed
```

The test constructs a vDPA object whose backend feature set does not include `VHOST_BACKEND_F_SUSPEND`, calls `start_migration()`, requires an error, then checks two post-error facts:

```text
migrating == false
pause() outside migration == Err
```

Current source violates the first condition because it commits `migrating=true` before the failing precondition.

## Candidate

The product change is only the migration-start ordering:

```text
check VHOST_BACKEND_F_SUSPEND
suspend()? 
self.migrating = true
Ok(())
```

The migration flag becomes a commit marker for successful entry into migration rather than an optimistic precondition marker.

Candidate result:

```text
running 1 test
test vdpa::unit_tests::failed_start_migration_keeps_normal_runtime_state ... ok
1 passed; 0 failed
```

## Quality gates

```text
cargo fmt --all -- --check
    passed

cargo clippy -p virtio-devices --lib --tests -- -D warnings
    passed
```

## Interpretation

This closes the local vDPA question:

> a failed `start_migration()` must not leave migration-only lifecycle state committed.

It does not establish complete migration rollback semantics.

Separate Fieldwork owners remain:

- #586 — DeviceManager aggregate migration start is not transactional across multiple components;
- #584 — late migration failure after destructive vhost-user/vDPA snapshot preparation lacks rollback;
- #606 — once `Complete` may have committed remotely, source rollback can be unsafe regardless of component-local cleanup.

The local candidate should stay one-function small and must not absorb those broader state-machine designs.

## Evidence boundary

Established:

- exact current source exhibits the failed-start flag leak;
- unsupported suspend is enough to reproduce it without hardware;
- moving the flag assignment after successful suspend fixes the focused lifecycle invariant;
- rustfmt and focused crate Clippy are green.

Not established here:

- a real host vDPA device suspend ioctl failure;
- aggregate multi-device migration-start rollback;
- late migration cancellation after vDPA snapshot drops its backend handle;
- KVM guest behavior.

No hardware, guest, external target, or upstream interaction was used.
