# PCI BAR reuse publication — live status

Updated: 2026-08-15

Canonical Fieldwork issue: `teamleaderleo/linux-fieldwork#599`
Exact upstream source generation: `69d4c0a82ef15b2660906013bd87ae32668e7998`
External-contact state: **false**

## Current answer

The original MMIO BAR address-reuse publication bug has a corrected clean two-commit candidate stack.

The lifecycle is:

```text
Bus range update is locally failure/concurrency safe
-> OLD remains allocator-owned
-> reserve NEW
-> move Bus / metadata / BAR-specific external state
-> config-BAR ioevent primary failure restores OLD registrations
-> move device-local BAR state
-> success: free OLD last
```

Late overall relocation failure deliberately leaves OLD and NEW allocator-reserved. That is conservative quarantine: another device cannot receive an address that may still have live external state.

## Canonical internal review carrier

Owned-fork draft review PR:

`teamleaderleo/cloud-hypervisor#61`

Pinned base:

`review/base-69d4c0a8` -> `69d4c0a82ef15b2660906013bd87ae32668e7998`

Clean head:

`review/ch-pci-bar-r599-clean-v2`

Clean history:

```text
69d4c0a82ef15b2660906013bd87ae32668e7998  exact upstream base
|
d0ed124cc80e9d22c60cdc19adb3f935517fb9e3  vm-device: make Bus range updates atomic
|
11bc53a67a29773d59001a5eea9238f1c380210e  vmm: Delay MMIO BAR reuse until relocation completes
```

Compared with exact upstream, the clean head is exactly two commits ahead and changes only:

```text
vm-device/src/bus.rs
vmm/src/device_manager.rs
```

Internal PR #60 is closed and explicitly superseded.

## Corrected Bus prerequisite

Fresh self-review found that the first clean Bus carrier no longer preserved baseline `update_range()`'s in-flight strong device lifetime: it carried the stored `Weak` after only a temporary upgrade check.

Bus v2 holds a strong `Arc` through the complete move and downgrades only when publishing the replacement map entry.

Authoritative v2:

- run/job `31899954631` / `95049007724`
- artifact `9250804219`
- digest `sha256:80b27e72b4e1eccf21d91483ccd625eac833cf77ff9ab13628103d61b751fc64`
- tested product commit `49f424649836a39e10f9e835e71f32cf18674ea3`
- tested/clean Bus blob `4e127584f680cde2af56f8d7f1c531368c1c2f4b`
- corrected clean commit `d0ed124cc80e9d22c60cdc19adb3f935517fb9e3`

A workflow-only barrier proves the device remains strongly alive if the caller drops its final external `Arc` while `update_range()` is paused, and becomes droppable after the move returns.

Full `vm-device`, stable Clippy, nightly rustfmt, product-diff identity, and diff checks pass.

See `../cloud-hypervisor-bus-stack/V2_LIFETIME_REVIEW.md`.

## Authoritative #599 v2 recomposition

The VMM BAR-reuse product file is byte-identical to the earlier independently green candidate:

`vmm/src/device_manager.rs` blob `3bd07c6e65c5c487bda28298e1a6aa6c251a27d7`

It was rerun on corrected Bus v2 rather than assumed to commute.

Authoritative v2 composition:

- run/job `31900130070` / `95049459937`
- workflow starting head `61875ac992ae23f7f6156665432f74e8a98d2f35`
- tested research commit `d28e368d9b39c0c77147685cd5ff35eb5b0532b8`
- artifact `9250885398`
- artifact digest `sha256:1d2c3c25ea35a37f813b7078a78a0f57ee7722bcbc513055b047e69b50fc1446`

Combined gates:

```text
corrected vm-device suite                             PASS
MMIO NEW-first lifecycle controls                    PASS
transactional config-BAR ioevent controls            PASS
all device_manager unit tests                        PASS
complete KVM-flavoured vmm test compile --no-run     PASS
stable project-shaped KVM workspace Clippy           PASS
nightly rustfmt                                       PASS
git diff --check                                      PASS
```

The clean VMM commit `11bc53...` uses the exact tested VMM blob.

## Important sibling: #680

Fieldwork #680 remains separate:

> late BAR relocation errors can restore config to OLD after mapping moved to NEW

A deterministic baseline proves the current config caller can restore OLD after a relocation has already published NEW mapping state.

The first explicit-outcome protocol experiment is green:

```text
rejected / old-Bus-intact error -> config may restore OLD
new Bus mapping already published -> retain config at NEW
```

Authoritative semantic run/job:

`31900036797` / `95049222035`

Artifact:

`9250860912`

Digest:

`sha256:703571b6c51c053b35ac79a69d3e0b3d9382fadc77391b9d90b6643259a8abd0`

Before a clean #680 carrier:

- rebase onto corrected #599 v2;
- narrow outcome names/docs to the **Bus mapping** guarantee;
- add `PciConfigIo` sibling-mode controls;
- rerun the full successor gates.

See `../cloud-hypervisor-pci-bar-relocation-outcome/README.md`.

## PIO boundary

The MMIO NEW-first proof does not apply to PIO.

PIO allocation defaults to byte alignment, so equal-size PIO ranges can partially overlap. Preserve current PIO sequencing until that path has its own discriminator.

See `PIO_SCOPE_BOUNDARY.md`.

## Next #599 gate

The strongest remaining #599 confirmation is target-native KVM execution of the public virtio-pmem / concurrent hotplug `KVM_IOEVENTFD EEXIST` scenario.

Preferred proof:

1. synchronize relocation before OLD is released;
2. attempt competing hotplug allocation;
3. prove the competitor cannot receive OLD while the move is incomplete;
4. complete relocation and release OLD;
5. prove OLD then becomes allocatable and ioevent registration succeeds;
6. run ordinary repeated relocation/hotplug afterward without the synchronization hook.

Generic GitHub-hosted runners do not provide usable `/dev/kvm`; keep this as a target-native/privileged execution gate rather than weakening the claim.

## Detailed records

- `ALLOCATOR_CAPABILITY.md`
- `LOCK_SCOPE_AUDIT.md`
- `MMIO_LEASE_GUARD_EXPERIMENT.md`
- `MMIO_NEW_FIRST.md`
- `IOEVENT_ROLLBACK.md`
- `PIO_SCOPE_BOUNDARY.md`
- `COMPOSITION.md`
- `../cloud-hypervisor-bus-stack/V2_LIFETIME_REVIEW.md`
- `../cloud-hypervisor-pci-bar-relocation-outcome/README.md`
