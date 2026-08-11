# PCI BAR reuse resource map

Updated: 2026-08-11

Parent: `README.md`
Canonical Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Public design reference: `yamahata/cloud-hypervisor:202607/pci-bus-eagar-unmap`

## Purpose

A BAR's allocator interval is only one ownership record. This map names the old-address resources that must be retired before the allocator may publish an address for reuse.

The exact release transaction depends on the BAR/device family. A generic `allocator.free(old)` at the top of relocation is therefore too early unless every downstream old-address operation is known to be side-effect-free or already complete.

## Common resources

Every normal relocated BAR can involve:

1. guest-visible PCI BAR register state;
2. `PciConfiguration` live/pending mapping state;
3. PCI segment address allocator reservation;
4. PIO or MMIO bus routing entry;
5. `DeviceTree` `Resource::PciBar` metadata;
6. device-local BAR bookkeeping.

Some families add KVM and host-IOMMU state below.

## Virtio PCI config BAR

Current `AddressManager::move_bar()` adds:

- KVM ioeventfd registrations derived from the config BAR base.

Current ordering:

```text
allocator old free/new allocate
MMIO bus update
DeviceTree base update
old ioeventfd unregister
new ioeventfd register
VirtioPciDevice local BAR update
```

Reuse hazard:

- old allocator address becomes available before old ioeventfd unregister;
- a concurrent hotplug can receive the address and collide in KVM with `EEXIST`.

Public target-native evidence for this sequence exists in upstream issue 8572.

Safe publication condition:

```text
old ioeventfds absent
old bus route absent
other old device effects absent
THEN allocator old may become free
```

## Virtio PCI shared-memory BAR

`AddressManager::move_bar()` handles the virtio shared-memory BAR separately from the config BAR.

Old/new address state includes:

- PCI allocator range;
- MMIO bus range;
- KVM userspace-memory region / memslot for the shared mapping;
- `VirtioDevice` shared-memory region address;
- local BAR bookkeeping / DeviceTree metadata.

A reuse publication point before `remove_user_memory_region()` completes can hand the GPA to another device while KVM still owns the old userspace mapping.

The public eager-release PoC performs allocator free first and KVM memslot removal in a later release step, so the same early-publication concern applies.

## VFIO PCI BAR

Current/pass-through MMIO BAR handling can include `UserMemoryRegion` entries associated with sparse or directly mmap-able VFIO BAR portions.

The public eager-release PoC's `VfioPciDevice::move_bar_prepare(bar_idx)` does, for every user-memory region of the BAR:

1. optional host-IOMMU `vfio_dma_unmap()` when P2P DMA is enabled and the device is outside the virtual IOMMU;
2. KVM `remove_user_memory_region()` for the BAR mmap.

These operations happen **after** `AddressManager::move_bar_prepare()` has already freed the PCI allocator range and removed the bus route.

### Important failure edge

In the reviewed PoC, failure of the optional P2P `vfio_dma_unmap()` is logged and release continues.

That creates a stronger publication requirement:

> A stale host-IOMMU mapping is an old-address consumer too. The allocator must not advertise the GPA as reusable while a failed DMA unmap leaves that mapping live.

The candidate should decide whether DMA-unmap failure is fatal to release, retriable, or safely recoverable. Logging and continuing cannot establish the reuse invariant by itself.

The KVM `remove_user_memory_region()` error is propagated in the PoC, but because allocator free occurs earlier, a failure can still leave the old address publicly free unless release rolls allocator ownership back.

## VFIO-user PCI BAR

The public PoC's `VfioUserPciDevice::move_bar_prepare(bar_idx)` removes each KVM userspace-memory region attached to that BAR.

Old-address state includes:

- PCI allocator range;
- MMIO bus route;
- KVM userspace-memory regions;
- VFIO-user local region bookkeeping.

Again, AddressManager allocator free precedes device-side KVM memslot removal in the PoC.

A KVM removal failure must therefore keep/recover the allocator lease before another device can receive the old address.

## ivshmem BAR

Current ivshmem BAR2 relocation replaces a userspace mapping through `IvshmemOps` and updates local BAR addresses.

The public eager-release PoC splits this:

- `move_bar_prepare(IVSHMEM_BAR2_IDX)` removes the old RAM mapping;
- `move_bar_commit(...)` maps the backend at the new GPA and updates BAR state.

Because generic `AddressManager::move_bar_prepare()` frees the allocator before invoking the device release hook, old-address reuse can become visible before ivshmem's old RAM mapping is removed.

The allocator lease should therefore cover the ivshmem unmap too.

## Simple emulated BARs

Devices whose `move_bar()` only updates internal BAR bookkeeping and have no old-address KVM/host-IOMMU registrations have a smaller release set.

Examples need individual confirmation before using a generic shortcut. `pvpanic` and other tiny emulated devices are useful negative controls for the transaction framework because they can prove the generic release/install machinery does not require heavyweight rollback when no external old-address resource exists.

## Resource publication table

| BAR family | allocator | bus | KVM ioeventfd | KVM memslot | host-IOMMU/P2P DMA | device mapping |
|---|---|---|---|---|---|---|
| virtio config | yes | yes | yes | no | normally no | BAR bookkeeping |
| virtio SHM | yes | yes | no config-event role | yes | device-dependent | shared-memory address |
| VFIO mmap BAR | yes | yes | device-specific IRQ path separate | yes for mmap areas | possible | VFIO MMIO + DMA state |
| VFIO-user mmap BAR | yes | yes | device-specific | yes | backend-specific guest DMA separate | VFIO-user MMIO state |
| ivshmem data BAR | yes | yes | no | through ivshmem mapping owner | no | RAM/backend mapping |
| simple emulated | yes | yes | usually no | usually no | no | local BAR state |

This table names expected categories, not proof that every instance uses every category. Candidate tests should exercise one representative of each non-empty external-resource class.

## Release rule by resource class

A practical candidate can treat allocator ownership as the last shared reuse lease while resource-specific hooks perform old-side teardown.

Conceptually:

```text
begin release
  allocator OLD remains reserved
  remove external old resources
  remove bus route
  commit device/local old-side release state
  if every required teardown succeeded:
      allocator.free(OLD)
      state = Released
  else:
      restore removed pieces or keep an explicit non-reusable Releasing state
```

The exact ordering among bus/device/KVM teardown should minimize rollback complexity, but no path may call the release complete while a conflicting old-address resource is live and the allocator says free.

## Install rule by resource class

Install starts by reserving the target GPA so no competitor receives it during setup:

```text
allocator.allocate(NEW)
install bus route
install device/KVM/DMA resources
commit local/DeviceTree state
state = Mapped(NEW)
```

If a later step fails, keep NEW allocator-owned until every partial NEW-side effect is removed. Then free NEW and return to Released/pending, or complete a full rollback to OLD.

## Failure cases that deserve explicit tests

### Virtio config

- old ioevent unregister failure;
- new ioevent register failure;
- bus removal/insertion failure.

### Virtio SHM

- old KVM memslot removal failure;
- new KVM memslot creation failure;
- local shared-memory address update failure.

### VFIO

- P2P `vfio_dma_unmap` failure;
- old KVM region removal failure;
- new KVM region creation failure;
- new P2P `vfio_dma_map` failure.

### VFIO-user

- old KVM region removal failure;
- new KVM region creation failure.

### ivshmem

- old backend/RAM mapping removal failure;
- new mapping creation failure.

## Strong new observation from the public PoC

The eager-release design has a good BAR-state split, but its generic release starts with allocator publication before resource-specific teardown. The VFIO hook also treats P2P DMA-unmap failure as log-and-continue.

So there are two independent design questions:

1. **When is a BAR logically released from the guest decode point of view?**
2. **When is its old GPA safe to publish to unrelated allocator clients?**

They may occur close together, but the second requires successful teardown of every conflicting old-address resource.

## Next discriminator

Add a synthetic release transaction with injectable hooks representing:

```text
old ioevent
old KVM memslot
old DMA mapping
old bus route
```

For every injected failure, assert:

```text
if any conflicting OLD resource survives:
    allocator OLD remains unavailable to a simulated hotplug client
```

Then map those hooks onto one real virtio config BAR and one VFIO/SHM-style memslot BAR before KVM-backed stress testing.
