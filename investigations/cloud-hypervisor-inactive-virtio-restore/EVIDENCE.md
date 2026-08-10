# Cloud Hypervisor inactive virtio-pci restore — continuation evidence

Updated: 2026-08-11

## Current upstream boundary

Current canonical head inspected:
`a658c9f9fd0c4e0363004361d73ac8733fa24fd0`

Primary source blob remains:
`virtio-devices/src/transport/pci_device.rs` = `0c1593f53f624c0e23845c3b08339f6ab57e6355`

The restore loop is unchanged at this head: after restoring each queue's saved `ready` bit and ring addresses, it calls `used_idx(...).unwrap()` twice for every queue.

## Fieldwork branches

Clean current-base source branch:
`teamleaderleo/cloud-hypervisor:linux-fieldwork/inactive-virtio-restore`

This branch was created directly from canonical head `a658c9f9fd0c4e0363004361d73ac8733fa24fd0` and remains the intended product carrier.

Read-only provenance branch:
`teamleaderleo/cloud-hypervisor:linux-fieldwork/reference-pr8702`

This points exactly at closed upstream attempt head `7a876a01c8bfbe33375fac2f55a29a9b8bf5e477`. It exists only to preserve and inspect those tested bytes; it is not the current candidate base.

## Closed upstream attempt: execution receipt

Canonical workflow run `31233150942` for `7a876a01c8bfbe33375fac2f55a29a9b8bf5e477` completed successfully.

Observed green jobs include:

- preflight, DCO, gitlint, REUSE, typos, package consistency;
- nightly x86_64 and AArch64 formatting;
- fuzz build/check;
- RISC-V builds on stable and Rust 1.89;
- x86_64 builds across stable, beta, nightly, 1.89, KVM, MSHV, and feature combinations;
- x86_64 quality/Clippy across KVM, MSHV, and feature combinations;
- AArch64 quality/Clippy across stable/beta and GNU/musl targets.

Maintainer review explicitly agreed the bug is genuine and described the desired repair as a simple conditional plus hoisting the duplicated `used_idx` read. The oversized test/comment presentation was the rejected part.

## Discriminator against the closed attempt

The closed attempt guarded ring-index restoration with:

```text
state.device_activated && state.queues[i].used_ring != 0
```

Current Cloud Hypervisor activation uses a device-wide `device_activated` flag once **any** queue is ready, while `prepare_activator()` independently skips each unready queue. A coherent saved state can therefore contain:

```text
device_activated = true
queue 0.ready     = true
queue 1.ready     = false
queue 1.used_ring = 0
```

The device-wide flag cannot prove every sibling queue was enabled. The saved per-queue `ready` bit is the direct discriminator.

Virtio 1.3's PCI common configuration describes `queue_enable` per queue and requires the driver to configure the other virtqueue fields before enabling that queue. This aligns with using the saved queue readiness state as the restore guard.

## Retained reduced candidate

Tracked patch:
`candidate.patch`

Latest Fieldwork patch commit:
`723d0f701465213ff700c577f6375eb3655f7c33`

Patch blob:
`f797ca01982c6db198295f1176f198da6d581378`

The retained source change stays intentionally small:

1. restore ring indexes only when `queue.ready()` is true;
2. read `used_idx()` once;
3. propagate a ready queue's invalid used-ring read through `CreateVirtioPciDevice` instead of panicking.

The regression surface is now reduced to two tests:

- an inactive queue with zero ring addresses, reproducing the canonical crash precondition;
- a partially enabled two-queue device, proving that device-wide activation is insufficient and that queue readiness is the correct guard.

The second test also carries the positive control: its ready queue contains a real used index and must restore that index while the unready sibling remains untouched.

## Executable focused receipt

Disposable Fieldwork validation run:
`31440887148`

Job:
`93625162482` — `inactive-virtio-restore` — **success**

The job checked out exact canonical source `a658c9f9fd0c4e0363004361d73ac8733fa24fd0`, applied the exact retained patch, and verified that only `virtio-devices/src/transport/pci_device.rs` changed.

Stable runner toolchain recorded:

```text
rustc 1.97.1
cargo 1.97.1
rustfmt 1.9.0-stable
```

`cargo fmt --all -- --check` passed.

The workflow first listed each exact Rust test name and required it to exist. It then executed each exact test independently:

```text
transport::pci_device::unit_tests::restore_inactive_queue_skips_used_index_read
running 1 test
... ok
1 passed; 0 failed
```

```text
transport::pci_device::unit_tests::restore_partially_enabled_device_skips_unready_queue
running 1 test
... ok
1 passed; 0 failed
```

This supersedes the earlier run whose bare `--exact` filters compiled the crate but selected zero tests.

## Current promotion boundary

The reduced candidate now has:

- exact-current patch application;
- exact one-file scope;
- stable rustfmt success;
- the canonical inactive-queue regression executed and green;
- the partial multi-queue discriminator/positive control executed and green.

The next gate is focused KVM Clippy with warnings denied, followed by a clean rerun and broader backend/build coverage appropriate to `virtio-devices`.

The clean owned-fork source branch remains unchanged while the exact patch identity is validated in disposable carriers.

## External-contact state

`false; none occurred during this Fieldwork continuation.`
