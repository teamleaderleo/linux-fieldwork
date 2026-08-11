# BAR reuse publication model result

Updated: 2026-08-11

Model: `reuse_publication_model.py`
Execution environment: Linux container, Python 3.13.5
External systems touched: none

## Command

```bash
python3 reuse_publication_model.py
```

The executable model used the same logic retained in the tracked file. The first attempt through the notebook-style Python tool was blocked by the execution environment before running; that was a tool failure. The model was then run directly with the container Python interpreter.

## Result

```text
virtio_config current= ['allocator_free', 'bus_remove'] candidate= []
virtio_shm current= ['allocator_free', 'bus_remove'] candidate= []
vfio_p2p current= ['allocator_free', 'bus_remove', 'memslot_remove'] candidate= []
candidate failure-injection invariant passed
```

The tracked model calls the two designs `early_publication_release` and `allocator_last_release`; the executed scratch command used the shorter labels `current` and `candidate`. Their transition logic is the same.

## Interpretation

For every modeled BAR family, freeing the old allocator reservation first creates at least one state in which a simulated hotplug allocator may claim the old GPA while another old-address resource still exists.

### Virtio config BAR

Unsafe publication begins immediately after allocator free and continues after bus removal until the old ioeventfd is removed.

### Virtio shared-memory BAR

Unsafe publication begins immediately after allocator free and continues after bus removal until the old KVM userspace-memory mapping is removed.

### VFIO P2P BAR

Unsafe publication begins after allocator free and survives bus removal. It also survives KVM memslot removal while the old host-IOMMU DMA mapping remains live.

This last state is particularly relevant to the reviewed public eager-release PoC: that VFIO release path logs a P2P `dma_unmap` failure and continues. Under allocator-first publication, such a failure can leave the old DMA mapping live after the GPA has become allocator-visible to another device.

The allocator-last model exposes zero claimable-old-with-conflict states in all three families.

## Failure injection

The model injects release failure at each represented teardown owner:

- old bus removal;
- old ioeventfd removal;
- old KVM memslot removal;
- old DMA mapping removal.

For allocator-last publication, every injected failure leaves the old allocator reservation in place. Therefore the simulated hotplug client cannot acquire the GPA while a conflicting old-address resource survives.

This proves the publication invariant for the model. It does not prove a Cloud Hypervisor patch or rollback implementation.

## Evidence boundary

Demonstrated here:

- the ordering property itself;
- why allocator-first release admits an unsafe reuse state;
- why allocator-last release prevents that state under the modeled failure owners.

Still requires product work:

- mapping these transitions into Cloud Hypervisor's real release/install implementation;
- rollback when a teardown step has already succeeded and a later step fails;
- new-side installation failure ordering;
- real KVM ioeventfd/memslot behavior under a candidate;
- VFIO host-IOMMU behavior under real P2P DMA;
- parent #598 rebalance behavior with the same candidate.

## Next step

Use this oracle when reviewing or prototyping the release transaction. A candidate loses immediately if any test checkpoint can satisfy both:

```text
allocator says OLD is free
AND
an old-address conflicting resource still exists
```

After the source-level transaction passes this invariant with injected failures, rerun the public KVM hotplug scenario and the parent two-device rebalance case.
