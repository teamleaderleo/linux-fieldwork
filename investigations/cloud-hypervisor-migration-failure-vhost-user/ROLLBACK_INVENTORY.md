# Migration rollback component inventory

Updated: 2026-08-11
Parent investigation: `cloud-hypervisor-migration-failure-vhost-user/`
Owning issue: #584
Exact upstream source: `915d359f97475b1a39d8561f8db514da9e692d19`
External-contact state: false; none occurred

## Purpose

Before proposing a shared `cancel_migration()` / rollback API, classify what current component hooks actually do. A rollback interface should be justified by concrete mutations and failure windows rather than added only for symmetry.

## VM aggregation

`Vm::start_migration()` currently runs:

```text
MemoryManager::start_migration()?
DeviceManager::start_migration()
```

MemoryManager uses the default no-op migration-start hook on current source.

DeviceManager iterates its `DeviceTree` and calls every migratable device sequentially with `?`. The tree is HashMap-backed, so component order is not a stable contract. Aggregate start has no rollback and is tracked separately in #586.

## Component matrix

| component | start hook | start can fail after mutation? | snapshot / later destructive action | ordinary resume restores it? | rollback significance |
|---|---|---|---|---|---|
| MemoryManager | default no-op | no current start mutation | snapshot records memory ranges | n/a | none for start hook |
| regular virtio-net | invalidates announcement generation | start currently returns `Ok` | normal snapshot only serializes state | `resume()` re-notifies announce | light/recoverable |
| vhost-user family | sets `migration_started=true`; vhost-user net also invalidates announce | shared start itself currently infallible | migration snapshot saves state, joins workers, closes backend connection, sets `vu=None` | no; resume only signals existing resume event + interrupts | strong late rollback requirement |
| vDPA | sets `migrating=true`, then may suspend backend | **yes**; flag is set before unsupported/failed suspend errors | migration snapshot drops `vhost` handle for same-host handoff | no generic reconstruction visible | strong early + late rollback requirement |
| VFIO PCI | validates migration support and virtual-IOMMU compatibility | no start mutation in current hook | pause/resume transition VFIO state; snapshot delegates to common migration state | VFIO resume uses transition helper with recovery | start is useful negative control |

## vDPA details

Successful vDPA start suspends the backend before VM pause. A local bug also sets `migrating=true` before the suspend attempt and fails to clear it on error; that narrow defect is #585.

On successful start, `Vdpa::snapshot()` later executes `self.vhost.take()` so a same-host destination can access the device. A migration error after that point needs source-side reconstruction if the source is to resume.

Therefore vDPA supplies both:

1. an **early transactional-start** example (#586), and
2. a **late destructive-handoff rollback** example adjacent to vhost-user (#584).

## vhost-user details

`VhostUserCommon::snapshot()` checks `migration_started` and then:

- optionally saves the dirty log;
- calls `shutdown()`;
- joins vhost-user workers;
- removes server socket path when relevant;
- drops `self.vu`.

This is intentional success-path ownership transfer. Ordinary `resume()` does not recreate the handle/worker.

## VFIO negative control

`VfioPciDevice::start_migration()` currently performs two preflight checks:

```text
migration v2 unsupported -> Err
virtual IOMMU attached    -> Err
```

It does not mutate VFIO migration state in those checks. VFIO pause/resume then use `transition_migration_state_with_recovery()`.

This is useful design evidence for a possible two-phase model: unsupported configurations can be rejected without state mutation before commit. It also shows that a generic rollback hook need not do work for every component.

## regular virtio-net negative/light control

Regular net's start hook only invalidates announcement generation and returns success. Its ordinary `resume()` calls common resume then `announce.notify(true)`.

This state is much lighter than vhost-user/vDPA teardown and may already recover naturally through resume. It should not drive the rollback API by itself.

## Design implications

The inventory favors separating two concepts:

### Preflight / prepare

Non-mutating capability and configuration checks should happen before any component commits migration state where practical. VFIO already behaves this way. vDPA can at least test the suspend feature before setting its flag.

### Rollback / cancel

Some operations remain inherently fallible after mutation, and snapshot can become deliberately destructive. vhost-user and vDPA therefore need a way to return the source to service after a failed handoff.

A future shared API may look like prepare/start/cancel/complete, but the exact interface should wait for executable failure fixtures from #584 and #586.

## Do not overgeneralize

- Dirty logging already has explicit `start_dirty_log` / `stop_dirty_log` pairing and failed-migration recovery attempts stop; keep it separate unless execution shows a shared failure owner.
- VFIO's current start hook should remain a negative control rather than receiving empty complexity solely for API uniformity.
- Regular net announcement state should be tested through existing resume before adding bespoke rollback.

## Next evidence

1. #586: deterministic fake DeviceManager components proving partial aggregate start.
2. #585: vDPA failed start leaves migration flag set.
3. #584: late virtio-fs/vhost-user failure after snapshot shutdown.
4. add vDPA late-failure fixture only if the vhost-user result supports a common cancellation owner.

## Authority

No upstream issue, pull request, comment, review, email, reaction, or other interaction is authorized or performed by this inventory.
