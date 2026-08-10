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

This separates two questions cleanly:

1. the closed attempt compiled and passed the canonical CI matrix;
2. maintainer review rejected the oversized/comment-heavy presentation and asked for a small conditional plus one `used_idx` read.

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

## Retained minimal candidate

Tracked patch:
`candidate.patch`

Fieldwork commit adding it:
`e1fe9111325b87e25f592dccb900baddf85184b3`

The retained candidate does four things:

1. restores ring indexes only when `queue.ready()` is true;
2. reads `used_idx()` once;
3. propagates a ready queue's invalid used-ring read through `CreateVirtioPciDevice` instead of panicking;
4. adds four compact regressions: inactive queue, partially enabled multi-queue device, ready valid queue, and ready queue with an unmapped used ring.

The partial multi-queue test is the negative control that distinguishes this candidate from a device-level guard.

## Execution state

The retained patch has not yet been applied to the current-base source branch and has not received a fresh Fieldwork execution receipt. The connector environment used for this continuation could read and write exact Git objects but could not perform a network clone for local Cargo execution.

Do not promote the retained patch from candidate design to proven product until all of these occur on the current-base source carrier:

1. patch application and exact one-file diff review;
2. focused restore unit tests, including the partial multi-queue discriminator;
3. immediate clean rerun;
4. nightly rustfmt;
5. focused `virtio-devices` Clippy/build gate;
6. broader backend/build coverage appropriate to the touched crate.

## External-contact state

`false; none occurred during this Fieldwork continuation.`
