# Execution receipt — vDPA failed migration start

Date: 2026-08-12
Owning issue: #585
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Rust: `1.89.0`
External-contact state: false; none occurred

## Result

Current vDPA leaks migration-only state when `start_migration()` fails before suspend is available.

Focused test:

```text
vdpa::unit_tests::failed_start_migration_keeps_normal_runtime_state
```

Baseline:

```text
BASELINE_RC=101
failed start_migration must not authorize migration-only behavior
```

The test forces a backend with no `VHOST_BACKEND_F_SUSPEND`. `start_migration()` returns an error, but current source has already set `migrating=true`, so the follow-up normal-runtime pause decision is incorrectly authorized.

## Candidate

Move `self.migrating = true` after successful vDPA suspend and return `Ok(())` only after both transition steps succeed.

Focused candidate result:

```text
1 passed; 0 failed
```

## Gates

- run: `31550859874`
- job: `93973079890`
- artifact: `9124450044`
- artifact digest: `sha256:1d20f4d9dc1a809ad0c7af0584e7659fa3c24ff09e754dca392e8ae81abc7d45`
- rustfmt: pass
- `cargo clippy -p virtio-devices --lib --tests -- -D warnings`: pass

## Boundary

This proves and fixes only the local vDPA transaction bug. It does not solve aggregate migration-start rollback across multiple devices (#586), late destructive vhost-user rollback (#584), or post-commit source recovery (#606).
