# Clean BAR reuse composition

Updated: 2026-08-15

Fieldwork issue: `teamleaderleo/linux-fieldwork#599`
Exact Cloud Hypervisor upstream base: `69d4c0a82ef15b2660906013bd87ae32668e7998`
External-contact state: false

## Result

The generic `vm-device::Bus` repairs, MMIO reserve-NEW-first ordering, and transactional virtio config-BAR ioevent move compose cleanly on one exact-current tree.

The combined lifecycle is:

```text
Bus range map
  validate/commit under one map owner

MMIO allocator
  OLD remains reserved
  -> reserve NEW

AddressManager relocation
  -> update bus / metadata / BAR-specific external state

virtio config-BAR ioevents
  unregister OLD transactionally
  -> register NEW transactionally
  -> primary failure restores OLD registrations

complete move success
  -> update device-local BAR
  -> free OLD allocator reservation last
```

Late overall relocation failure remains conservative: OLD and NEW stay allocator-reserved. That prevents unrelated reuse while the separate late-relocation rollback contract tracked in Fieldwork #680 remains unresolved.

## Clean prerequisite: generic Bus stack

Clean review commit:

`2edcf22f0bd35beff06ab2b4e132cf240e54d2f9`

Parent:

`69d4c0a82ef15b2660906013bd87ae32668e7998`

Product path:

`vm-device/src/bus.rs`

This is the clean composition of Fieldwork #677, #678, and #679:

- failed `update_range()` preserves OLD;
- concurrent `insert()` validates and commits under one write lock;
- high-address overlap arithmetic uses widened endpoint calculations.

Its independent authoritative receipt is retained in `../cloud-hypervisor-bus-stack/README.md`.

## Authoritative #599 composition execution

Owned-fork research branch:

`teamleaderleo/cloud-hypervisor:research/ch-pci-bar-r599-compose`

Workflow run/job:

`31898915572` / `95046394050`

Starting workflow head:

`3e6373521471eb3ef40ecd98738cde9ab0a99dba`

The workflow verified that:

- the branch descended from exact upstream `69d4c0...`;
- the `vm-device/src/bus.rs` blob exactly matched the clean Bus review commit;
- `vmm/src/device_manager.rs` was pristine against exact upstream before materialization;
- the NEW-first and ioevent source candidates were reconstructed from their independently validated materializers rather than rewritten manually.

Tested research commit produced after all gates:

`edd80ddca871f82e1b4e6a70385310305912a3d0`

Tested `vmm/src/device_manager.rs` blob:

`3bd07c6e65c5c487bda28298e1a6aa6c251a27d7`

VMM candidate diff SHA-256:

`8d16a06f76294b3225743f5d35f242e0d44286d74ad1f3ff20e172f5a540c782`

Artifact:

`9250587225`

Artifact digest:

`sha256:717824744f5040aa23941df19df8dff6c64d6c743c7fc88fa4234a55af1ff3ec`

## Combined gates

All composition gates passed:

```text
exact base / Bus blob identity                           PASS
generic vm-device suite                                 PASS
MMIO NEW-first lifecycle tests                          PASS
transactional ioevent failure/success tests             PASS
all device_manager unit tests                           PASS
complete KVM-flavoured vmm test compile --no-run        PASS
stable project-shaped KVM workspace Clippy -D warnings PASS
nightly rustfmt                                          PASS
git diff --check                                         PASS
```

The workflow then created a DCO-signed VMM research commit only after those gates succeeded.

## Clean review carrier

A clean two-commit review branch was minted directly from the tested Git blobs:

`teamleaderleo/cloud-hypervisor:review/ch-pci-bar-r599-clean`

Head:

`cae581234681a45d2d7abe13c97ee3ae5d1d431e`

History:

```text
69d4c0a82ef15b2660906013bd87ae32668e7998  upstream exact base
|
2edcf22f0bd35beff06ab2b4e132cf240e54d2f9  vm-device: make Bus range updates atomic
|
cae581234681a45d2d7abe13c97ee3ae5d1d431e  vmm: Delay MMIO BAR reuse until relocation completes
```

The VMM clean commit uses the exact tested blob `3bd07c6e65c5c487bda28298e1a6aa6c251a27d7` and the same DCO/AI-disclosure commit message as the tested research commit.

Compared directly with upstream `69d4c0...`, the clean head is exactly two commits ahead and changes only:

```text
vm-device/src/bus.rs
vmm/src/device_manager.rs
```

No workflow or Fieldwork trigger files are present in the clean review history.

## What this proves

Inside the executed scope:

1. generic bus range updates no longer introduce the known local partial/concurrent states;
2. MMIO replacement addresses can be reserved while OLD stays allocator-owned;
3. successful relocation releases OLD only after the rest of `AddressManager::move_bar()` succeeds;
4. ordinary config-BAR ioevent register/unregister failures can restore the exact OLD registration set;
5. a late overall relocation failure does not expose either OLD or NEW to unrelated allocator clients;
6. these three layers coexist on one source tree under project-shaped quality gates.

This closes the original **allocator reuse publication** mechanism at the source/candidate level without requiring a long-held allocator mutex or a new allocator reservation type.

## What this does not prove

The clean stack is not a claim that `AddressManager::move_bar()` is fully failure-atomic.

Fieldwork #680 proves the existing caller contract is too strong: a `DeviceRelocation` may publish NEW-side mapping state and then return `Err`, while `PciConfigIo` / `PciConfigMmio` restore the config BAR to OLD as though OLD were still intact.

Therefore:

- allocator quarantine on late error is deliberate and safety-preserving;
- rollback/retry cleanup of NEW remains a separate #680 problem;
- shared-memory memslot and VFIO-specific rollback need their own failure controls;
- PIO is excluded because its allocator alignment contract does not support the MMIO disjoint-range proof;
- a KVM-backed rerun of the public hotplug `EEXIST` scenario remains the strongest end-to-end confirmation before any upstream publication decision.

## Current disposition

**#599 source candidate: coherent and ready for deeper internal review / target-native KVM confirmation.**

Keep #680 separate. Do not widen the #599 clean branch to repair the caller's late-error semantics merely to make allocator quarantine prettier.

The next high-value #599 gate is the real virtio-pmem/hotplug scenario with a synchronization point around the old-address release boundary, verifying that another device cannot obtain OLD until the move has completed successfully.
