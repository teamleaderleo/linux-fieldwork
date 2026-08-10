# Cloud Hypervisor lifecycle scout — 2026-08-11

## TL;DR

A current-main source pass found one strong defect candidate, one small test-portability candidate, and one stale-status/revalidation item:

1. **Promote:** virtio-pci snapshot restore still reads a queue's used index even after restoring that queue as `ready = false`. An inactive queue can therefore turn zero ring addresses into a guest-memory read at address `0x2` and panic. The later activation path already skips non-ready queues, giving a clean ownership mismatch and a compact discriminator.
2. **Keep warm:** the vDPA integration test still requests `size=512M,hugepages=on` without an explicit hugepage size. On a host whose default hugepage size is 1 GiB, the test's memory size is misaligned. This looks like a harness portability fix, not a product defect.
3. **Reconcile before further use:** the ACPI error-propagation work recorded in Fieldwork as approved/merge-pending has now merged upstream. Any successor stack that treated the old internal ACPI carrier as its prerequisite should refresh against current upstream main.

A second lifecycle thread, vDPA hot-unplug, has changed enough since its original crash report that it should be revalidated before anyone carries the old panic claim forward. Current `remove_device()` code returns typed lookup errors in places that previously used unchecked access, and it applies a device-type removal allowlist.

## Exact source boundary

- Upstream repository: `cloud-hypervisor/cloud-hypervisor`
- Upstream branch inspected: `main`
- Exact upstream head inspected: `a18a2b3f66f7a3cec7f62d07605945beda8eb5d3`
- Fieldwork baseline observed before this round: `bcb922d8934abb91a498b8b48115d58ae585cb6b`
- Research date: 2026-08-11
- Execution: source/issue/PR review only; no target-native VM run in this round
- External-contact state: **none**. No upstream comment, issue, review, or PR action was performed.

## Strongest result: inactive/non-ready virtio-pci queue restore

Upstream issue:
https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8693

Closed fix attempt:
https://github.com/cloud-hypervisor/cloud-hypervisor/pull/8702

### Technical result owner

`virtio-devices/src/transport/pci_device.rs`, `VirtioPciDevice::new()` restore path.

### First distinguishing observation

On current main, restore performs this sequence for every saved queue:

```text
restore size
restore ready
restore desc/avail/used ring addresses
read used_idx from guest memory
set next_avail / next_used
```

The `used_idx` read is unconditional.

Later, device activation walks the same queues and explicitly skips any queue for which `queue.ready()` is false.

That gives a direct mismatch:

```text
queue is saved as non-ready
        ↓
restore still dereferences its used ring
        ↓
activation would ignore the queue
```

For the reported inactive virtio-rng state, the saved ring addresses are zero. `used_idx()` reads the `idx` field at `used_ring + 2`, yielding guest address `0x2`; the read fails and the existing `.unwrap()` panics.

### Why the old fix attempt is useful evidence but not the selected carrier

PR 8702 changed one source file and proposed guarding the index restore plus adding regression tests. A maintainer explicitly confirmed that the bug is genuine and that the fix should be small, while rejecting the submitted patch package as overgrown.

The useful retained lesson is therefore narrower than the closed PR:

- keep the product delta tiny;
- derive the guard from queue/device lifecycle semantics;
- keep the regression proof compact;
- avoid commentary that restates removed behavior.

### Next discriminator

Use a 2×2 state matrix around the two lifecycle signals already present in the saved state:

| device activated | queue ready | expected restore-index behavior |
|---|---|---|
| false | false | skip |
| false | true | establish expected handling explicitly |
| true | false | skip this queue |
| true | true | read and restore used index |

The most important fixture is **an activated multiqueue device with one ready queue and one non-ready queue**. That case makes a device-level-only guard lose immediately.

Compare at least these candidate rules:

1. `state.device_activated && queue.ready()` — lifecycle-driven.
2. `state.device_activated && used_ring != 0` — address-sentinel-driven, as in the closed PR.
3. unconditional read with error propagation — removes the panic but still touches a queue activation will skip.

The source currently gives `ready` semantic weight in activation, so candidate 1 is the leading hypothesis. It remains a hypothesis until the four-state fixture is executed against the exact current head.

### Stop rule

Stop widening this lane once the four-state fixture establishes which saved-state predicate matches successful restore and no adjacent queue-reset/multiqueue case contradicts it. Keep any candidate to the restore loop plus the smallest regression proof unless execution exposes another owner.

### Reopening trigger

Reopen broader design work only if a valid snapshot can contain a queue state where the chosen predicate disagrees with the queue that activation actually consumes, or if current main changes the saved queue lifecycle contract.

## Side finding: hugepage-sensitive vDPA test

Upstream issue:
https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8620

Current source still contains:

```text
_test_vdpa_block
  --memory size=512M,hugepages=on
```

with no explicit `hugepage_size` in that test invocation.

The issue reports that Cloud Hypervisor uses the host default hugepage size when none is specified, and a 1 GiB default makes a 512 MiB guest fail alignment validation. The existing upstream CI uses a smaller default and therefore misses that host-dependent case.

Classification for this round: **harness portability candidate**. The smallest useful proof is configuration-level: show that the same test command succeeds with an explicit supported hugepage size and that the product's default-size behavior remains unchanged outside tests.

Evidence limit: source presence plus upstream issue report. No 1 GiB-default host was executed here.

## Side finding: vDPA hot-unplug needs fresh reproduction

Upstream issue:
https://github.com/cloud-hypervisor/cloud-hypervisor/issues/7785

The historical issue reports a panic during vDPA hot-unplug. Current `DeviceManager::remove_device()` now resolves missing parent/BDF/device-handle cases through typed errors and applies a `VirtioDeviceType` removal allowlist. That is enough source movement to expire the old panic description as current evidence.

This does **not** establish that vDPA hot-unplug now works. It establishes that the old crash path should be reproduced on current main before product work starts.

Useful discriminator:

- vDPA-net removal should reveal whether the current allowlist rejects it cleanly;
- vDPA-block removal should reveal whether the generic virtio removal path can complete for a vDPA backend;
- ordinary hot-removable virtio block is the negative/control neighbor.

Stop if current main returns a documented/intentional rejection cleanly and leaves the VM usable. Promote only if a current-main reproduction still panics, corrupts device bookkeeping, or claims successful removal while leaving backend state behind.

## Fieldwork reconciliation: ACPI lane landed

Upstream PR:
https://github.com/cloud-hypervisor/cloud-hypervisor/pull/8709

The ACPI error-propagation PR is merged. Upstream records merge commit:

`735d44f54e222475b2737ed9ca814f1769107cd9`

The existing Fieldwork investigation still says `UPSTREAM APPROVED — CI / MERGE PENDING.` Its technical record remains useful, but that disposition is stale as of this round.

Successor work that depended on the earlier internal ACPI carrier should use current upstream main as the dependency boundary and revalidate any stacked candidate whose evidence predates the landed version.

## Promotion decision

Promote the virtio-pci restore finding into a focused investigation because exact source review has begun and the next discriminator is clear.

Keep the hugepage item in this research round until a 1 GiB-default host or equivalent controlled configuration executes it.

Keep vDPA hot-unplug at revalidation status until a current-main reproduction chooses between clean rejection, clean removal, and failure.

## Next safe actions

1. Execute the four-state virtio-pci restore fixture on exact current main, including the partial-multiqueue case.
2. If candidate selection holds, prepare a tiny candidate branch with one product guard and the minimum regression test; keep upstream contact disabled.
3. Reproduce the hugepage test under a 1 GiB default hugepage environment or a faithful equivalent.
4. Reproduce vDPA-net and vDPA-block removal on current main before trusting the historical crash description.
5. Refresh Fieldwork pointers that still present the ACPI PR as merge-pending when those files are next touched.
