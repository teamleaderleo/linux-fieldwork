# Current BAR move partial-failure states

Updated: 2026-08-11

Parent: `README.md`
Canonical Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Primary source: `vmm/src/device_manager.rs::AddressManager::move_bar()` and `vm-device/src/bus.rs::Bus::update_range()`

## TL;DR

Current BAR relocation is a sequence of fallible updates across independent owners. The April allocator rollback protects one early failure: allocation of the requested new range. Later failures can leave allocator, bus, metadata, KVM registrations, and device-local state describing different addresses.

A transaction-oriented successor should define rollback or explicit pending state for every later failure, not only for new-range allocation.

## Current memory-BAR sequence

For a normal MMIO BAR, current `AddressManager::move_bar()` performs these broad steps:

```text
1. allocator.free(OLD)
2. allocator.allocate(NEW)
3. mmio_bus.update_range(OLD -> NEW)
4. DeviceTree resource OLD -> NEW
5. device-specific external effects
   a. virtio config BAR: unregister OLD ioevents, register NEW ioevents
   b. virtio SHM: remove OLD KVM memslot, create NEW KVM memslot, update SHM metadata
   c. other PCI device hook work later
6. pci_dev.move_bar(OLD, NEW)
```

PIO follows the same allocator-first pattern with the PIO bus.

## Protected early edge: allocator target unavailable

Current code frees OLD, tries to allocate NEW, and attempts to allocate OLD again if NEW allocation fails.

On successful rollback:

```text
allocator = OLD
bus       = OLD
metadata  = OLD
external  = OLD
local     = OLD
```

This is the failure class repaired by the current rollback work.

It does not cover failures after NEW allocation succeeds.

## Bus update failure

After allocator NEW is reserved, `Bus::update_range()` does:

```text
resolve OLD device
remove(OLD)
insert(NEW)
```

If `insert(NEW)` fails, `update_range()` returns the error and does not restore OLD.

Possible resulting state:

```text
allocator = NEW
bus       = no OLD route; NEW insert failed
metadata  = OLD
external  = OLD
local     = OLD
```

This is stronger than a simple allocator/bus disagreement: the old decoded route can disappear entirely on a failed bus insertion.

No transaction-wide rollback in `AddressManager::move_bar()` repairs the allocator or bus after this return.

### Why insertion can fail even after allocator success

The allocator and bus are separate registries. Under ordinary healthy state they should agree, so an overlap here points at stale bus state, concurrent publication, or an earlier inconsistency. Those are exactly the cases where recovery needs to preserve a truthful state instead of compounding it.

A fault-injection unit test can exercise this deterministically even if production occurrence is rare.

## DeviceTree update failure

After allocator and bus have moved to NEW, the code searches the device node for a `Resource::PciBar` matching OLD.

If the device node is absent or the matching resource is absent, the function returns an error.

State at return can be:

```text
allocator = NEW
bus       = NEW
metadata  = OLD / missing
external  = OLD
local     = OLD
```

No rollback restores allocator/bus to OLD.

This is likely an internal bookkeeping failure rather than a guest-driven ordinary case, but it is a transaction edge and should be injected in a candidate test.

## Virtio config BAR: old ioevent unregister failure

After allocator, bus, and DeviceTree already name NEW, the code walks ioeventfds derived from OLD and unregisters them.

If one unregister fails:

```text
allocator = NEW
bus       = NEW
metadata  = NEW
OLD ioevent(s) = some/live
NEW ioevents   = absent
local BAR hook = not committed
```

The old allocator address may already be visible to another device despite surviving KVM ioevent state; this is the publication race modeled in the parent investigation.

## Virtio config BAR: new ioevent register failure

The old ioevents are removed before new ioevents are registered.

If NEW registration fails:

```text
allocator = NEW
bus       = NEW
metadata  = NEW
OLD ioevents = removed
NEW ioevents = partial/absent
local BAR hook = not committed
```

The MMIO route exists at NEW while device notification plumbing can be incomplete.

If several ioeventfds exist, a later registration failure can also leave a partial set at NEW.

A candidate needs an explicit unwind list for already-registered NEW ioevents.

## Virtio shared-memory BAR: old KVM memslot removal failure

The shared-memory path runs after allocator, bus, and DeviceTree have moved to NEW.

If `remove_user_memory_region(OLD)` fails:

```text
allocator = NEW
bus       = NEW
metadata  = NEW
OLD KVM memslot = live/unknown
NEW KVM memslot = absent
SHM local addr   = OLD
```

Again, OLD can be allocator-free while a KVM mapping survives.

## Virtio shared-memory BAR: new KVM memslot creation failure

If OLD removal succeeds and NEW creation fails:

```text
allocator = NEW
bus       = NEW
metadata  = NEW
OLD KVM memslot = gone
NEW KVM memslot = absent
SHM local addr   = OLD
```

The guest-visible route has moved while the shared backing is unmapped from KVM.

No current rollback recreates OLD before returning.

## Virtio shared-memory BAR: local SHM metadata update failure

After NEW KVM mapping succeeds, `set_shm_regions()` can still fail.

Possible state:

```text
allocator = NEW
bus       = NEW
metadata  = NEW
NEW KVM memslot = live
SHM local addr   = OLD / rejected update
```

The KVM mapping and local virtio metadata disagree.

## Final device `move_bar()` failure

After generic allocator/bus/DeviceTree and relevant virtio external work, `pci_dev.move_bar(OLD, NEW)` is still fallible.

A failure here arrives after most generic state is already committed.

The exact local partial state depends on the device family. The generic caller has no rollback transaction to reverse prior steps.

This edge is the strongest reason to give device-specific release/install hooks explicit preparation/commit/rollback semantics instead of treating `move_bar()` as one final best-effort callback.

## PIO has the same early transaction weakness

PIO BAR relocation:

```text
free_io_addresses(OLD)
allocate_io_addresses(NEW)
io_bus.update_range(OLD -> NEW)
```

The current allocator target-unavailable case tries to restore OLD, but a later PIO bus update failure can leave allocator NEW while the bus has already removed OLD or otherwise failed its move.

So this is a generic address-move transaction issue, not MMIO-only.

## Candidate invariant

At every externally observable return:

```text
all owners agree on the live mapping
OR
an explicit Released/Pending state says no mapping is live and keeps address reuse publication truthful
```

An error return must not mean “some owners say OLD, some say NEW, and the allocator may have published one of the addresses.”

## Suggested candidate phases

### Release OLD

Keep OLD allocator-reserved as a reuse lease while removing conflicting old resources.

```text
prepare old-side teardown
remove external OLD resources
remove OLD bus route
commit device old-side release state
allocator.free(OLD) only after successful teardown
state = Released(target=NEW)
```

If any step fails, restore earlier teardown or retain an explicit non-reusable releasing state. OLD remains allocator-owned until recovery is complete.

### Install NEW

Reserve NEW before publishing new effects:

```text
allocator.allocate(NEW)
install bus route
install KVM/ioevent/DMA/device effects
update metadata/local state
state = Mapped(NEW)
```

If a later step fails, keep NEW reserved while removing any partial NEW effects. Free NEW only after unwind has completed, returning to Released(target=NEW) or a fully restored OLD state.

## Failure-injection matrix to add

A candidate test harness should fail each operation exactly once:

1. OLD bus removal;
2. OLD ioevent unregister;
3. OLD KVM memslot removal;
4. OLD VFIO P2P DMA unmap;
5. OLD device-side release hook;
6. allocator OLD free at publication;
7. allocator NEW reserve;
8. NEW bus insert;
9. NEW ioevent registration at first and later event;
10. NEW KVM memslot creation;
11. NEW VFIO DMA map;
12. metadata commit;
13. device-local install/commit hook.

After every injected error, assert:

- allocator availability matches the selected safe state;
- no address is reusable while a conflicting resource survives;
- bus routes match the live mapping claim;
- KVM/ioevent/DMA registries have no partial NEW set or leaked OLD set unless the explicit state says recovery is still in progress;
- a retry has one deterministic action.

## Evidence boundary

Established from exact current source:

- only initial NEW-allocation failure has explicit allocator restoration;
- bus update removes OLD before inserting NEW and has no internal restoration on insert failure;
- later DeviceTree, ioevent, memslot, SHM metadata, and device hooks all return errors after earlier owners have already moved;
- generic `move_bar()` has no transaction-wide rollback for those later errors.

This file does not claim every later failure is reachable under ordinary healthy deployment. It maps the state each fallible boundary can produce and defines the fault-injection work needed before a transactional candidate is trusted.
