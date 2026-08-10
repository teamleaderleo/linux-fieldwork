# Selection — Cloud Hypervisor lifecycle scout

## Selection rule

Prefer findings where the current source owner is clear, a compact fixture can distinguish competing explanations, and the next action can change a concrete decision.

## Ranked findings

### 1. Virtio-pci restore touches non-ready queues — PROMOTE

**Why selected**

- current-main source still carries the risky read;
- the upstream report has a concrete reproducer and exact panic;
- a maintainer independently confirmed the defect;
- source already exposes the lifecycle predicate (`queue.ready()`) used by activation;
- a partial-multiqueue fixture can make a device-only guard lose;
- likely product delta is tiny.

**Bounded question**

Which saved-state predicate should gate restoration of virtqueue runtime indexes so restore touches exactly the queues that can participate in resumed device activation?

**Alternatives alive**

- `device_activated && queue.ready()`
- `device_activated && used_ring != 0`
- another predicate exposed by an adjacent reset/restore contract

**Alternative already weakened**

A device-level-only condition is insufficient for an activated device with only a subset of queues configured.

**First execution needed**

A four-state device/queue fixture, with special emphasis on an activated device containing one ready and one non-ready queue.

### 2. 512 MiB vDPA hugepage test inherits host default — KEEP WARM

**Why retained**

- current source still contains the host-sensitive command;
- issue gives a precise environment discriminator: default hugepage size 2 MiB vs 1 GiB;
- likely fix belongs in tests and can stay narrow.

**Why not promoted yet**

This round did not execute a 1 GiB-default host. The current evidence is source corroboration plus an upstream report.

**First execution needed**

Run the same test command under both default hugepage environments, then compare with an explicit `hugepage_size` test argument.

### 3. vDPA hot-unplug historical panic — REVALIDATE

**Why retained**

The report is lifecycle-sensitive and could still expose cleanup/bookkeeping defects.

**Why selection is deferred**

Current removal code has materially changed around the historical crash boundary. Missing lookup state now has typed errors and virtio removal goes through an explicit device-type allowlist. A current-main reproduction must choose the state before any patch design is justified.

**First execution needed**

Compare vDPA-net, vDPA-block, and ordinary hot-removable virtio-block removal on current main.

### 4. ACPI error propagation — STATUS RECONCILIATION

The technical lane already completed its product work. Upstream PR 8709 merged as `735d44f54e222475b2737ed9ca814f1769107cd9`. The useful action is refreshing stale Fieldwork disposition and rebuilding successor assumptions on the landed source, not reopening ACPI design.

## Rejected expansion directions

### Differential snapshots / external userfaultfd designs

Interesting active feature work exists around differential snapshots and external userfaultfd ownership. Those threads are broader design discussions with explicit lifecycle questions around migration, hotplug, and memory ownership. They remain useful context, but this round found a smaller current defect with a stronger discriminator. Expanding into those designs would dilute the selected lane before the restore bug's simple state matrix is tested.

### General unwrap audit

Cloud Hypervisor contains many intentional internal `unwrap()` / `assert!()` sites. The ACPI lane already demonstrated why a repository-wide panic-removal policy grows quickly into design judgment. The selected restore defect has a concrete recoverable state mismatch; keep the claim local to that owner.

## Stop condition for this round

The round is complete when:

- one finding has a clear promoted investigation and next discriminator;
- side findings have explicit evidence ceilings and reopening conditions;
- no upstream interaction has occurred;
- exact source heads and links are durable in the repository.

Those conditions are met by the companion README, sources file, and promoted investigation record.
