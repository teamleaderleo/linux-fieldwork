# Landlock pre-opened file probe

Updated: 2026-08-12

Parent: `investigations/cloud-hypervisor-landlock-restore-order/README.md`
Receive-migration comparison: `RECEIVE_MIGRATION_COMPARISON.md`
Internal validation PR: `teamleaderleo/cloud-hypervisor#29`
Exact upstream base: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Current exact probe head: `6d5de27d1f8a3976ae01e5140f0098c9a2bcd0d0`
Initial probe head retained in history: `832ab0cbf40ad1e4542a3f229068c3e3b300a5ac`
Intermediate lint/format head: `d12c8667e6062a221e1fc92a664c421a51a5a531`
Runtime workflow head: `dddb6eb773dcaced3c6846c82d208cf69e780df2`
Runtime workflow/run/job: `Fieldwork Landlock pre-open runtime` / `31547742820` / `93963728979`
Runtime environment: GitHub-hosted `ubuntu-24.04`, Ubuntu 24.04.4 LTS, Rust 1.97.1
Runtime result: **PASS — 1 passed, 0 failed**
External-contact state: **disabled / no upstream contact performed**

## TL;DR

Cloud Hypervisor's Landlock rules were executed on a real Ubuntu 24.04.4 kernel against a three-way file-descriptor discriminator.

After `restrict_self()` granted read access only to one directory:

```text
allowed path + new open      -> succeeded
unlisted path + new open     -> PermissionDenied
unlisted path + old open FD  -> remained readable
```

The focused unit test passed exactly once with no ignored tests and no failures. This demonstrates the mechanism needed by the restore-order investigation: activating the ruleset blocks future opens outside the allowlist, but it does not revoke access already captured by an open descriptor.

That result makes the current snapshot ordering materially different from fresh create whenever `Vm::new()` opens a secondary file before Landlock is applied. It still does not, by itself, prove that QCOW snapshot restore exercises that exact sequence; the QCOW-specific differential remains the next layer.

## Question

Does activating Cloud Hypervisor's Landlock rules revoke access through a file descriptor that was already opened before `restrict_self()`?

**Answer on the tested environment: no.**

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

The carrier then received two non-semantic packaging fixes:

- import `ErrorKind` instead of spelling `std::io::ErrorKind` inline, satisfying `clippy::absolute_paths`;
- apply the exact rustfmt layout requested by CI.

## Runtime receipt

Disposable runtime branch:

`teamleaderleo/cloud-hypervisor:linux-fieldwork/landlock-preopen-runtime`

Workflow-only runtime commit:

`dddb6eb773dcaced3c6846c82d208cf69e780df2`

Command:

```text
cargo test -p vmm --lib --no-default-features --features kvm \
  test_preopened_file_remains_usable_after_restriction -- --nocapture
```

Run/job:

```text
31547742820 / 93963728979
```

Hosted environment reported:

```text
Ubuntu 24.04.4 LTS
ubuntu-24.04 runner image
rustc 1.97.1 (8bab26f4f 2026-07-14)
```

Observed test output:

```text
running 1 test
test landlock::test_preopened_file_remains_usable_after_restriction ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 103 filtered out
```

### First failed runtime carrier

The first workflow run, `31547600867`, did **not** execute the Landlock test. It invoked `cargo test -p vmm` without a hypervisor feature and failed compiling existing VMM code around `VfioDeviceFd::try_clone`.

Failure owner: **runtime harness / feature selection**, not product or test semantics.

The repair changed only the workflow command to match the repository's normal KVM build family:

```text
--no-default-features --features kvm
```

The probe source bytes were unchanged between the failed and passing runtime attempts.

## Why this is the right negative/positive control

The test distinguishes three states using the same ruleset:

```text
allowed path + new open      -> succeeds
unlisted path + new open     -> denied
unlisted path + old open FD  -> stays usable
```

All three outcomes held in one real execution.

Therefore, an ordering difference that opens a secondary file before `restrict_self()` is semantically meaningful: the later ruleset prevents future opens but does not retroactively remove authority already captured in the descriptor.

That result does not depend on QCOW parsing, KVM guest execution, guest boot, or snapshot serialization. Those remain separate layers in the product-level differential.

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

The passing pre-open probe now supplies the missing executable mechanism underneath that source ordering.

The next product-level test remains:

```text
same overlay + same Landlock policy
fresh create/boot  vs  snapshot restore
```

with the backing path deliberately omitted from the allowlist and the snapshot source explicitly accounted for.

Before paying the KVM/integration cost, add a QCOW-specific process-local discriminator if possible:

```text
open/parse QCOW backing chain before restrict -> remains usable
restrict first, then open same backing chain   -> denied
```

That can prove the block-layer connection without guest execution while keeping the final snapshot/restore test as the end-to-end gate.

## Evidence boundary

Established:

- Cloud Hypervisor's actual `Landlock` helper executed successfully on Ubuntu 24.04.4;
- a newly opened unlisted path was denied after restriction;
- an already-open descriptor for that same unlisted path remained readable;
- an explicitly allowed path remained openable;
- the test ran under the KVM feature family used by normal VMM builds;
- the first failed runtime run was a harness feature-selection failure and never reached the test.

Still pending:

- direct QCOW backing-chain execution under both orderings;
- full fresh-create versus snapshot-restore differential;
- the minimum snapshot-source rule needed by an earlier enforcement candidate;
- candidate product CI.

## Stop rule

Do not promote the mechanism probe itself into upstream product code. Close the internal carrier after its normal compile/quality matrix is retained.

Promote the restore-order finding only when the QCOW product-level differential reproduces on exact current source, or another real device path demonstrates the same pre-open authority gap.
