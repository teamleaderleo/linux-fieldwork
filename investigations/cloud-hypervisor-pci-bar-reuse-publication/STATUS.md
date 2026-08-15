# PCI BAR reuse publication — live status

Updated: 2026-08-15

Canonical Fieldwork issue: `teamleaderleo/linux-fieldwork#599`
Exact upstream source generation: `69d4c0a82ef15b2660906013bd87ae32668e7998`
External-contact state: **false**

## Current answer

The original address-reuse publication bug has a clean, exact-source candidate stack.

For MMIO BAR relocation, OLD does not need to be freed before NEW can be reserved. Accepted BAR targets are BAR-size aligned, so distinct equal-size MMIO BAR ranges are disjoint.

The preferred lifecycle is therefore:

```text
OLD remains allocator-owned
-> reserve NEW
-> move Bus / metadata / BAR-specific external state
-> move device-local BAR state
-> success: free OLD last
```

For virtio config BARs, ioevent registration changes are also now transactional:

```text
remove OLD registrations
-> add NEW registrations

primary failure:
  remove any NEW already added
  restore every OLD already removed
```

If the wider relocation still fails late, OLD and NEW remain allocator-reserved. This is conservative quarantine rather than unsafe reuse.

## Clean review carrier

Owned fork draft review PR:

`teamleaderleo/cloud-hypervisor#60`

Pinned base branch:

`review/base-69d4c0a8`

Clean head branch:

`review/ch-pci-bar-r599-clean`

Clean history:

```text
69d4c0a82ef15b2660906013bd87ae32668e7998  exact upstream base
|
2edcf22f0bd35beff06ab2b4e132cf240e54d2f9  vm-device: make Bus range updates atomic
|
cae581234681a45d2d7abe13c97ee3ae5d1d431e  vmm: Delay MMIO BAR reuse until relocation completes
```

The clean head is exactly two commits ahead of the pinned upstream base and changes only:

```text
vm-device/src/bus.rs
vmm/src/device_manager.rs
```

## Authoritative composition receipt

Run/job:

`31898915572` / `95046394050`

Artifact:

`9250587225`

Artifact digest:

`sha256:717824744f5040aa23941df19df8dff6c64d6c743c7fc88fa4234a55af1ff3ec`

Tested VMM research commit:

`edd80ddca871f82e1b4e6a70385310305912a3d0`

Tested / clean VMM blob:

`3bd07c6e65c5c487bda28298e1a6aa6c251a27d7`

Combined gates:

```text
vm-device suite                                      PASS
MMIO NEW-first lifecycle controls                    PASS
transactional config-BAR ioevent controls            PASS
all device_manager unit tests                        PASS
complete KVM-flavoured vmm test compile --no-run     PASS
stable project-shaped KVM workspace Clippy           PASS
nightly rustfmt                                       PASS
git diff --check                                      PASS
```

See `COMPOSITION.md` for the full receipt and proof boundary.

## Important sibling: #680

Fieldwork #680 is separate:

> late BAR relocation errors can restore config to OLD after mapping moved to NEW

Current `PciConfigIo` / `PciConfigMmio` assume every `DeviceRelocation::move_bar()` error means OLD mapping stayed intact and blindly restore the BAR config register to OLD.

A deterministic current-main discriminator proves that assumption is unsafe for a relocation implementation that publishes NEW mapping state and then returns an error.

The real `AddressManager::move_bar()` has that source shape: the Bus update can succeed before later DeviceTree, ioevent, memslot, or device-local operations fail.

#680 is currently testing an explicit result protocol that distinguishes:

```text
OldMappingIntact(error)     -> caller may restore config to OLD
NewMappingPublished(error)  -> caller must retain config at NEW
```

Keep #680 out of the #599 clean stack until its independent evidence stabilizes.

## PIO boundary

The MMIO NEW-first proof does not apply to PIO.

PIO allocation defaults to byte alignment, so equal-size PIO ranges can partially overlap. Preserve current PIO sequencing until that path has its own discriminator.

See `PIO_SCOPE_BOUNDARY.md`.

## Next #599 gate

Run the target-native KVM virtio-pmem / concurrent hotplug reproducer corresponding to the public upstream `KVM_IOEVENTFD` `EEXIST` sequence.

Preferred proof:

1. synchronize relocation before OLD is released;
2. attempt competing hotplug allocation;
3. prove the competitor cannot obtain OLD while the move is incomplete;
4. allow successful relocation to finish and release OLD;
5. prove OLD then becomes allocatable and ioevent registration succeeds;
6. run ordinary repeated relocation/hotplug afterward without the synchronization hook.

Hosted generic GitHub runners do not provide `/dev/kvm`; treat this as a target-native / privileged execution gate rather than weakening the claim to fit hosted CI.

## Detailed records

- `ALLOCATOR_CAPABILITY.md` — what the current allocator can represent.
- `LOCK_SCOPE_AUDIT.md` — why simply stretching the allocator mutex is incomplete.
- `MMIO_LEASE_GUARD_EXPERIMENT.md` — superseded long-held-mutex experiment.
- `MMIO_NEW_FIRST.md` — authoritative reserve-NEW-first proof and history.
- `IOEVENT_ROLLBACK.md` — transactional config-BAR ioevent failure matrix.
- `PIO_SCOPE_BOUNDARY.md` — why PIO stays separate.
- `COMPOSITION.md` — exact clean stack and authoritative combined execution.
