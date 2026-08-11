# QCOW backing-chain Landlock ordering probe

Updated: 2026-08-12

Parent: `investigations/cloud-hypervisor-landlock-restore-order/README.md`
Generic pre-open mechanism: `PREOPEN_PROBE.md`
Receive-migration comparison: `RECEIVE_MIGRATION_COMPARISON.md`
Internal validation PR: `teamleaderleo/cloud-hypervisor#30`
Exact upstream source: `cloud-hypervisor/cloud-hypervisor` `main` @ `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Frozen generic-probe base: `6d5de27d1f8a3976ae01e5140f0098c9a2bcd0d0`
QCOW probe head: `65df6e8b50c26b13cb8d3d9156476e795db70c37`
Runtime workflow head: `4c8232ffee5eaa9988b0981d643146efb3d6a321`
Runtime workflow/run/job: `Fieldwork QCOW Landlock ordering runtime` / `31548103949` / `93964786948`
Runtime environment: GitHub-hosted `ubuntu-24.04`, Ubuntu 24.04.4 LTS, Rust 1.97.1, qemu-img 8.2.2
Runtime result: **PASS — 1 passed, 0 failed**
External-contact state: **disabled / no upstream contact performed**

## TL;DR

The real Cloud Hypervisor QCOW backend shows an observable Landlock ordering difference with the same overlay/backing pair.

Fixture:

```text
allowed/
  overlay.qcow2  -> absolute raw backing path outside allowed/
denied/
  base.raw       -> begins with bytes LFQCOW42
```

The Landlock rules grant `rw` only to `allowed/`.

Two executions use the same files:

```text
restrict first
  -> open allowed overlay
  -> QcowDisk::new() tries to open denied/base.raw
  -> BackingFileIo(..., PermissionDenied)

QcowDisk::new() first
  -> backing descriptor is captured
  -> restrict to allowed/
  -> read offset 0 through QCOW
  -> returns LFQCOW42 from denied/base.raw
```

The focused test passed on Ubuntu 24.04.4. This connects the generic pre-opened-file result directly to Cloud Hypervisor's actual QCOW backing-chain opener.

It does **not** yet prove the complete `vm.restore` differential. It proves the block-layer premise that makes the current snapshot ordering consequential: constructing a QCOW disk before Landlock can retain access to a transitive backing path that the same ruleset would deny if construction happened after restriction.

## Exact source owner

At upstream head `1af93ac7035cda77cd87b0c18b1134ebb0928052`, `block/src/formats/qcow/parser.rs` resolves the backing configuration and `BackingFile::new()` opens `config.path` with `OpenOptions`.

A failed backing open becomes:

```text
QcowError::BackingFileIo(path, io::Error)
```

The QCOW probe therefore observes the actual backend operation whose ordering differs between fresh VM creation and snapshot restoration.

## Disposable runtime fixture

The runtime workflow created only disposable runner state:

```text
root="$RUNNER_TEMP/fieldwork-qcow-landlock"
mkdir -p "$root/allowed" "$root/denied"
truncate -s 1M "$root/denied/base.raw"
printf 'LFQCOW42' | dd of="$root/denied/base.raw" conv=notrunc status=none
qemu-img create -f qcow2 -F raw \
  -b "$root/denied/base.raw" \
  "$root/allowed/overlay.qcow2" 1M
qemu-img info --backing-chain "$root/allowed/overlay.qcow2"
```

`qemu-img info --backing-chain` reported:

```text
image: .../allowed/overlay.qcow2
file format: qcow2
virtual size: 1 MiB
backing file: .../denied/base.raw
backing file format: raw

image: .../denied/base.raw
file format: raw
virtual size: 1 MiB
```

No guest, KVM VM, external target, or persistent runner state was used.

## Focused test

The ignored Fieldwork-only test is:

```text
test_qcow_backing_open_respects_landlock_order
```

Environment variables point it at the external fixture:

```text
FIELDWORK_QCOW_OVERLAY
FIELDWORK_QCOW_ALLOWED_DIR
FIELDWORK_QCOW_DENIED_BACKING
```

### Branch A — restriction before QCOW construction

Inside a child thread:

1. create Cloud Hypervisor's `Landlock` ruleset;
2. grant `rw` only to the overlay directory;
3. call `restrict_self()`;
4. open the overlay file successfully;
5. call `QcowDisk::new(... backing_files = true ...)`;
6. require `BlockErrorKind::Io`;
7. require the source to be `QcowError::BackingFileIo` for the exact denied raw backing path;
8. require its `io::ErrorKind` to be `PermissionDenied`.

This branch proves the block backend cannot newly acquire the unlisted backing path after the ruleset is active.

### Branch B — QCOW construction before restriction

The unrestricted parent:

1. opens the same overlay;
2. constructs `QcowDisk` with backing support, causing the backing chain to open;
3. moves that disk object into a child thread.

The child then:

1. grants `rw` only to the same overlay directory;
2. calls `restrict_self()`;
3. creates the disk's async I/O engine;
4. reads offset zero;
5. requires the returned bytes to equal `LFQCOW42`.

Those marker bytes exist only in the raw backing file. Their successful read after restriction proves the already-constructed backing chain retained usable authority outside the active allowlist.

## Runtime receipt

Disposable runtime branch:

```text
teamleaderleo/cloud-hypervisor:linux-fieldwork/landlock-qcow-runtime
```

Workflow-only head:

```text
4c8232ffee5eaa9988b0981d643146efb3d6a321
```

Command:

```text
cargo test -p vmm --lib --no-default-features --features kvm \
  test_qcow_backing_open_respects_landlock_order -- --ignored --nocapture
```

Run/job:

```text
31548103949 / 93964786948
```

Hosted environment:

```text
Ubuntu 24.04.4 LTS
runner image ubuntu-24.04
rustc 1.97.1 (8bab26f4f 2026-07-14)
qemu-img 8.2.2 package family
```

Observed test output:

```text
running 1 test
test landlock::test_qcow_backing_open_respects_landlock_order ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 104 filtered out
```

## What this establishes

Demonstrated on the tested environment:

1. the configured overlay path can remain allowed while its transitive raw backing path is denied;
2. with Landlock active before QCOW construction, Cloud Hypervisor's real QCOW parser receives `PermissionDenied` opening that backing path;
3. constructing the same QCOW chain before Landlock captures a usable backing descriptor;
4. after restriction, reads through that QCOW object can still return data from the now-unlisted backing file;
5. the difference is caused by operation ordering, not by a different fixture or ruleset.

Together with source review, this makes the current snapshot restore ordering technically consequential rather than merely suspicious.

## Connection to VM lifecycle paths

Exact current source places the same block-device construction on different sides of Landlock:

```text
fresh create
  apply Landlock
  -> later VM/device construction opens disk/backing chain

snapshot restore
  Vm::new(...)
  -> disk/backing chain opens
  apply Landlock

receive migration
  pre-create console resources
  apply Landlock
  -> memory/device reconstruction
```

The QCOW probe proves the operation moved across that boundary has different authority depending on which side it runs.

## Evidence boundary

Established:

- generic pre-open descriptor behavior under Cloud Hypervisor's Landlock helper;
- exact QCOW backing open source owner;
- a passing QCOW block-layer differential using the real `QcowDisk` constructor and backing reader;
- exact fixture, environment, workflow, run, job, and test command;
- ordinary PR packaging checks for the carrier had already passed DCO, rustfmt, REUSE, package consistency, and gitlint at the time of this result.

Still pending:

- an end-to-end fresh-create versus `vm.restore` reproduction through the VMM API;
- the exact minimum snapshot payload path that must remain reachable if restore Landlock moves earlier;
- a product candidate and its full CI/integration evidence;
- maintainer/upstream decision or contact.

## Next action

Before writing product code, enumerate every filesystem open that still occurs from the snapshot source after `config.json` and `state.json` have already been read.

If only `memory-ranges` remains, prefer an exact read rule for that file over granting the whole snapshot directory. Then construct a minimal internal candidate that keeps console pre-creation before restriction, adds the required snapshot payload rule, applies Landlock, and only then calls `Vm::new()`.

Run the QCOW fixture as the candidate negative control: the denied backing path must stay denied while the snapshot payload remains readable.
