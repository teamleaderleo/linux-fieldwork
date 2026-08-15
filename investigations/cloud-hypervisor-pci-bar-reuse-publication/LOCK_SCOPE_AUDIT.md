# Cloud Hypervisor PCI BAR relocation — allocator lock-scope audit

## Result

Holding the selected address-allocator mutex longer remains a plausible **serialization ingredient**, but it is insufficient as a complete #599 repair.

The attractive idea is:

```text
lock selected allocator
-> free OLD
-> allocate overlapping NEW
-> retire OLD external effects while competitors remain blocked
-> finish transition
-> unlock allocator
```

This can bridge the capability gap recorded in `ALLOCATOR_CAPABILITY.md`: an overlapping NEW cannot coexist with OLD as two ordinary allocator entries, but the mutex can prevent unrelated clients from observing the temporary map state while one relocation owns the guard.

The source audit found no immediate reason to reject that ingredient. The stopping point is failure recovery: many fallible operations happen after allocator mutation. Releasing the guard after one of those failures would publish a partial transaction unless the other registries are rolled back or retained under explicit pending state.

## Exact source

Cloud Hypervisor upstream `main`:

`69d4c0a82ef15b2660906013bd87ae32668e7998`

Relevant paths:

- `pci/src/bus.rs`
- `vmm/src/device_manager.rs`
- `virtio-devices/src/transport/pci_device.rs`
- `pci/src/vfio.rs`
- `vm-allocator/src/address.rs`

## Lock order observed

Guest BAR reprogramming enters relocation while the `PciBus` mutex and target PCI-device mutex are held. The relocation callback then acquires the selected address allocator.

Conceptually:

```text
PCI bus
-> PCI device
-> selected address allocator
-> current allocator free/allocate
```

Normal device creation allocates BARs by locking the PCI device and the system/MMIO allocators for the `allocate_bars()` call. Those allocator guards are expression-local; later BAR registration and `pci_bus.add_device()` occur after the allocation call returns.

So the inspected creation path does not show the dangerous opposite critical section:

```text
allocator held
-> later acquire PCI bus
```

This does not prove every path in the VMM is free of inversion, but it removes the first obvious deadlock objection to extending the selected allocator guard.

## Why lock extension would help

Current memory-BAR relocation effectively does:

```text
lock allocator
free OLD
allocate NEW
unlock allocator

update MMIO bus
update DeviceTree
unregister/register virtio ioevents
or remove/create shared-memory KVM regions
final device move hook
```

The public #599 race lives after `unlock allocator`: a concurrent hotplug allocation can receive OLD while an OLD-address ioevent or mapping still survives.

Keeping the allocator guard through OLD-address teardown would stop unrelated allocator clients from entering that interval.

For overlapping OLD/NEW relocation, this is especially useful because the allocator representation cannot hold both leases simultaneously.

## Why lock extension alone fails

After allocator mutation, current `move_bar()` has multiple fallible edges:

```text
Bus::update_range()
DeviceTree resource lookup/update
old ioevent unregister
new ioevent register
old KVM memory-region removal
new KVM memory-region creation
shared-memory metadata update
pci_dev.move_bar()
```

The #677 candidate removes one partial-state class from `Bus::update_range()`, but the remaining edges still matter.

Suppose the allocator guard is simply kept alive longer and old ioevent unregister fails:

```text
allocator map: OLD removed, NEW allocated
old ioevent: still live or partially retired
function: returns Err
allocator guard: drops
```

A competitor can now enter the allocator even though the relocation has no truthful fully-old or fully-new state.

Allocator-only rollback also fails as a universal answer. For an overlapping move, restoring OLD requires freeing NEW first. If the bus, DeviceTree, new ioevents, KVM mapping, or device-local state has already advanced toward NEW, freeing NEW publishes an address that may still carry live NEW-side effects.

Therefore the mutex can serialize the transaction while it executes, but an error path still needs one of:

1. complete rollback of every already-mutated external registry before unlocking;
2. explicit retained relocation state whose allocator ownership remains unavailable until recovery finishes;
3. a narrower ordering that makes every post-publication step infallible or prevalidated, which current code does not provide.

## Device callback note

The inspected virtio PCI `move_bar()` hook only updates the device's remembered BAR region address; the heavy virtio ioevent/shared-memory work is performed earlier in `AddressManager`.

VFIO relocation has device-specific MMIO/memory/DMA work and therefore widens the external failure surface. This strengthens the case for keeping BAR-family rollback evidence separate even if one generic serialization rule is eventually shared.

## Current design conclusion

The smallest plausible #599 endpoint is now clearer:

```text
allocator mutex = serialization against competing allocation
+
BAR-family transaction = rollback / pending-state owner for external registries
```

The mutex may eliminate the need for a new allocator representation purely to hide the temporary overlapping OLD/NEW map state. It does not eliminate transaction semantics in `AddressManager`.

That is a useful reduction: investigate transaction ownership in the VMM before modifying `AddressAllocator` itself.

## Next executable discriminator

Target the narrowest BAR family first: virtio config BAR ioevent relocation.

The desired deterministic test needs to force failure during old ioevent unregister and assert, before any allocator guard becomes available to a competitor, that the operation either:

```text
A. restores a complete OLD state and OLD allocator lease
```

or

```text
B. retains an explicit unavailable/pending state that prevents both OLD and unsafe NEW reuse
```

Current source has no small `hypervisor::Vm` failure mock in this owner, so a test seam must be introduced deliberately. That seam should be narrower than mocking the complete VM trait—prefer a local ioevent relocation helper or closure-backed operation boundary whose rollback can be unit-tested, then connect it to `AddressManager::move_bar()`.

## Boundary

This audit is source/ownership evidence. It does not claim an allocator-lock extension candidate has been executed in the VMM.

External-contact state: false. Cloud Hypervisor upstream remained read-only.
