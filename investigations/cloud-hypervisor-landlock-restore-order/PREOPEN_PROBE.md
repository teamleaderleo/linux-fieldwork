# Landlock pre-opened file probe

Updated: 2026-08-12

Parent: `investigations/cloud-hypervisor-landlock-restore-order/README.md`
Receive-migration comparison: `RECEIVE_MIGRATION_COMPARISON.md`
Internal validation PR: `teamleaderleo/cloud-hypervisor#29`
Exact upstream base: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Exact probe head: `832ab0cbf40ad1e4542a3f229068c3e3b300a5ac`
External-contact state: **disabled / no upstream contact performed**

## Question

Does activating Cloud Hypervisor's Landlock rules revoke access through a file descriptor that was already opened before `restrict_self()`?

This is the kernel/file-descriptor mechanism that can make snapshot restore observably different from fresh create when device construction opens a secondary disk path before Landlock becomes active.

## Probe

The validation-only change adds one test to `vmm/src/landlock.rs`.

The unrestricted parent test thread:

1. creates two disposable directories;
2. writes one file in each;
3. opens the file in the directory that will *not* be allowed;
4. moves that open descriptor into a child thread.

The child thread then:

1. constructs Cloud Hypervisor's `Landlock` ruleset;
2. grants read access only to the first directory;
3. calls `restrict_self()`;
4. opens the allowed file successfully;
5. attempts a fresh open of the unlisted file and expects `PermissionDenied`;
6. reads the bytes successfully from the descriptor opened before restriction.

The Landlock restriction is confined to the child thread. After it exits, the unrestricted parent retains both temporary directories, so cleanup is not blocked by the ruleset.

## Why this is the right negative/positive control

The test distinguishes three states using the same ruleset:

```text
allowed path + new open      -> should succeed
unlisted path + new open     -> should fail
unlisted path + old open FD  -> should remain usable
```

If all three outcomes hold, then an ordering difference that opens a secondary file before `restrict_self()` is semantically meaningful: the later ruleset prevents future opens but does not retroactively remove authority already captured in the descriptor.

That result does not depend on QCOW parsing, KVM, guest boot, or snapshot serialization. Those remain separate layers in the product-level differential.

## Evidence boundary

The internal PR is a **validation carrier**, not a candidate product patch.

At creation time:

- the test is source-reviewed and isolated to one file;
- CI has not yet completed;
- repository CI compiles/clippies test targets but may not execute this unit test;
- therefore a green PR proves build/quality compatibility, not the runtime Landlock result by itself.

The runtime result must come from an actual `cargo test` execution on a Landlock-capable Linux kernel. Until that receipt exists, keep the outcome as expected from the kernel/file-descriptor model rather than demonstrated Fieldwork behavior.

## Connection to the product differential

Source already establishes:

```text
fresh create:
  restrict -> later disk/backing opens

snapshot restore:
  Vm::new / disk/backing opens -> restrict

receive migration:
  restrict -> memory/device reconstruction
```

If this pre-open probe passes at runtime, it explains why snapshot restore can retain access to a path that the same active ruleset would deny if the path were first opened after restriction.

The next product-level test remains:

```text
same overlay + same Landlock policy
fresh create/boot  vs  snapshot restore
```

with the backing path deliberately omitted from the allowlist and the snapshot source explicitly accounted for.

## Stop rule

Do not promote the mechanism probe itself into upstream product code. Close the internal carrier after its compile/quality and runtime receipts are retained.

Promote the restore-order finding only when the QCOW product-level differential reproduces on exact current source, or another real device path demonstrates the same pre-open authority gap.
