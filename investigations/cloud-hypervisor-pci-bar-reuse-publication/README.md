# Cloud Hypervisor PCI BAR address reuse publication

Updated: 2026-08-11

Fieldwork issue: `teamleaderleo/linux-fieldwork#599`
Parent investigation: `investigations/cloud-hypervisor-pci-bar-release-ordering/README.md`
Upstream umbrella: https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8572
Canonical source: `cloud-hypervisor/cloud-hypervisor` `main` @ `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Public eager-release PoC reviewed: `yamahata/cloud-hypervisor:202607/pci-bus-eagar-unmap`
Current state: **runtime sequence already reported upstream; current and PoC source preserve the early-publication order**
Upstream-contact state: **disabled / no contact performed**

## TL;DR

A PCI BAR address is more than an allocator interval. A live virtio BAR can also own an MMIO bus range and one or more KVM ioeventfd registrations; a shared-memory BAR can own a KVM userspace-memory region; VFIO paths can carry their own mappings and DMA state.

Current `AddressManager::move_bar()` publishes the old range as allocator-free before those old-address side effects are gone. The public issue discussion contains a target-native concurrent hotplug reproduction where a new device reuses that address and its ioeventfd registration hits `EEXIST` because the old ioeventfd is still registered.

The public eager-unmap PoC for the parent rebalance issue keeps the same problematic release order:

```text
1. allocator_free(old)
2. bus.remove(old)
3. unregister old ioeventfds / remove old KVM memslot
4. device-side release
```

So it fixes the stale-BAR rebalance collision while leaving—and potentially lengthening—the interval in which `old` is advertised as reusable too early.

The strongest candidate rule is:

> **Allocator ownership is the last old-address reservation released.** Keep the old allocator range reserved as a reuse lease while bus/KVM/device teardown runs. Free it only after every old-address resource that can conflict with another device has been retired.

On install, invert the logic: reserve the new allocator range first, then install bus/KVM/device side effects; publish full installation only after all succeed. On failure, unwind side effects while retaining the relevant allocator reservation until rollback is complete.

## Explain like I'm five

A parking space has a sign saying who owns it, plus a gate and a charging cable.

Cloud Hypervisor currently removes the ownership sign first. Another car sees the empty sign and drives in while the old charging cable is still attached. The new car cannot attach its own cable because the old one still occupies the socket.

The ownership sign should stay until the old gate and cable are gone.

## Why care

The visible upstream failure is hotplug failing with `KVM_IOEVENTFD` `EEXIST`. The deeper issue is publication order across independent registries.

A fix for BAR rebalance that creates a longer released interval increases the importance of this rule. Eager release is useful only if `released` means the old address is truly safe for another device to claim.

## Public runtime evidence

The issue discussion reports this sequence during concurrent virtio-pmem hotplug while a boot-time virtio BAR relocates:

```text
register old address                    -> success
register hotplug device at old address -> EEXIST
deassign old address                    -> success
register relocated address              -> success
```

The report identifies the source mechanism: the old allocator interval becomes available before the old ioeventfd is deassigned.

This Fieldwork pass did not rerun that KVM workload. The public report is target-native evidence; current source review below independently matches its ordering.

## Current-main release order

For memory BARs, current `AddressManager::move_bar()`:

1. locks the selected PCI MMIO allocator;
2. `free(old_base)`;
3. `allocate(new_base)`;
4. releases the allocator lock;
5. updates the MMIO bus old→new;
6. updates device-tree resource metadata;
7. for a virtio config BAR, unregisters ioeventfds at `old_base`;
8. registers ioeventfds at `new_base`;
9. for a virtio shared-memory BAR, removes/creates KVM userspace-memory regions in the later device-specific branch;
10. calls `pci_dev.move_bar(old_base, new_base)`.

The hotplug race window begins when step 2 makes `old_base` free and persists at least until step 7 retires old ioeventfds.

The allocator mutex serializes individual allocator operations. It does not span the cross-registry teardown. A concurrent DeviceManager/hotplug allocation can therefore acquire the allocator after `move_bar()` releases that lock and before old KVM state is gone.

## Why current same-call allocation does not save `old_base`

`move_bar()` frees old and immediately allocates the **new** target while holding the allocator lock. That protects the new address from another allocator user during this operation.

It intentionally leaves the old address free after the lock is released. That is correct only if every side effect attached to the old address has already been retired. Current ordering does the opposite.

So the transaction has two different publication points:

- `new_base` becomes allocator-owned early, before all new-side setup is complete;
- `old_base` becomes allocator-free early, before all old-side teardown is complete.

Both need explicit failure semantics.

## Public eager-release PoC result

The parent issue's public PoC splits move into `move_bar_prepare()` and `move_bar_commit()`.

The inspected release order is:

```text
move_bar_prepare:
1. allocator_free(old)
2. remove old PIO/MMIO bus range
3. virtio teardown:
   - config BAR: unregister old ioeventfds
   - SHM BAR: remove old KVM memslot
4. pci_dev.move_bar_prepare(bar_idx)
```

The PoC therefore preserves the exact allocator-before-ioevent publication order responsible for the reported hotplug race.

Because BAR install may remain deferred until MSE/IOSE is enabled, the period after `allocator_free(old)` can be much longer than current single-call `move_bar()`. This makes reuse eligibility a first-class part of the eager-release design.

## Candidate lifecycle

Use allocator reservation as the address-reuse lease.

### Old-side release

Conceptual order:

```text
Mapped(old)
  |
  | mark BAR release-in-progress; keep allocator old reserved
  v
remove/disable old-address external effects
  - ioeventfds
  - KVM userspace-memory region where applicable
  - device-side mappings/DMA where applicable
  - PIO/MMIO bus range
  - metadata that advertises live decode, as required
  |
  | all conflicting old-address teardown succeeded
  v
allocator.free(old)   <-- old address becomes reusable here
  |
  v
Released(target=new)
```

The exact bus/device ordering can vary by BAR type. The invariant is that allocator-free publication occurs after conflicting old-address resources are retired.

### New-side install

Conceptual order:

```text
Released(target=new)
  |
  | allocator.allocate(new)  <-- new address reserved from competitors
  v
install new bus/device/KVM effects
  |
  | all succeeded
  v
Mapped(new)
```

If new-side setup fails, retain the new allocator reservation while unwinding any new-address effects already installed. Free it only after rollback has removed those effects. Then the BAR can remain released/pending for retry or perform a complete old-state rollback according to the chosen higher-level policy.

## Why the allocator is a useful lease

Every competing hotplug/BAR allocation already consults the address allocator. Keeping `old` reserved during teardown uses an existing shared arbitration point instead of inventing another global lock.

This does not make the whole relocation atomic by itself. It gives one crisp guarantee:

> no unrelated allocator client can receive the old address until teardown has reached the explicit publication point.

The release code still needs rollback for failures before that point.

## Failure matrix for old-side release

| failure | allocator old | old bus | old ioevent/memslot | disposition |
|---|---|---|---|---|
| before teardown | reserved | live | live | still mapped |
| old ioevent removal fails | reserved | chosen order dependent | partially/live | restore removed pieces; remain mapped/retry release |
| old memslot/device release fails | reserved | chosen order dependent | partial | restore or retain explicit releasing state; do not expose address |
| bus removal fails | reserved | live/partial | chosen order dependent | restore earlier teardown; address remains unavailable |
| allocator free fails/has no effect | reserved/unknown | gone | gone | error; never claim released until allocator confirms state |
| success | free | gone | gone | released and reusable |

The candidate needs concrete rollback actions for each BAR family. A simple reordering without failure recovery only moves the ambiguity.

## Failure matrix for new-side install

| failure | allocator new | new bus | new ioevent/memslot | disposition |
|---|---|---|---|---|
| allocate new fails | absent | absent | absent | stay released/pending |
| bus insert fails | reserved until unwind | absent/partial | absent | unwind bus, then free new; stay released |
| device/KVM setup fails | reserved until unwind | live | partial | remove new effects/bus, then free; stay released |
| metadata/local commit fails | reserved until unwind | live | live | choose rollback or keep explicit installing state; do not expose inconsistent completion |
| success | reserved by BAR | live | live | mapped new |

## Deterministic first fixture

The public KVM reproduction already proves the race can happen. The first Fieldwork fixture should make the publication rule deterministic without thread timing.

Use three synthetic registries:

```text
allocator: owned/free intervals
bus:       old/new mappings
ioevents:  addresses currently registered
```

Initial state:

```text
allocator owns OLD for moving device
bus contains OLD
ioevents contains OLD
```

### Current/PoC release ordering control

1. free OLD in allocator;
2. pause release before bus/ioevent teardown;
3. simulate hotplug allocation of OLD -> succeeds;
4. simulate hotplug ioevent registration at OLD -> fails EEXIST because old ioevent remains.

This mirrors the upstream runtime sequence with no scheduler dependency.

### Candidate ordering

1. keep allocator OLD reserved;
2. remove old ioevent and bus/device side effects;
3. at each intermediate checkpoint simulate hotplug allocation OLD -> must fail;
4. after teardown, free OLD;
5. hotplug allocation OLD -> succeeds;
6. hotplug ioevent registration OLD -> succeeds.

Add injected failures at each teardown step and assert OLD never becomes allocatable while a conflicting old registry entry survives.

## Real KVM follow-up

After a source-level candidate passes the synthetic ordering fixture:

1. reproduce the public virtio-pmem hotplug scenario on KVM;
2. amplify with an explicit synchronization hook or test barrier around old-side release rather than probabilistic sleeps;
3. prove the hotplug device cannot receive OLD until old ioevent teardown completed;
4. remove the hook and run repeated normal hotplug + BAR relocation;
5. inspect surviving ioeventfds indirectly through registration success/failure and device function.

Avoid declaring the race fixed from a stress loop alone; retain the deterministic ordering proof.

## Relationship to parent #598

Parent #598 asks when a disabled BAR should release its old mapping and when its new mapping should install.

This lane asks when the **old address may be given to somebody else**.

A candidate can satisfy one and fail the other:

- current main keeps old resources too long for rebalance, yet publishes allocator old too early inside `move_bar()` relative to ioevent teardown;
- public eager-release PoC fixes the rebalance lifetime, yet still publishes allocator old before ioevent/memslot teardown.

That is why the lanes remain separate.

## Evidence boundary

Established:

- public target-native EEXIST sequence is recorded under upstream issue 8572;
- current source frees old allocator state before old virtio ioevent teardown;
- allocator lock does not span later bus/KVM teardown;
- public eager-release PoC also calls allocator free before bus/KVM/device teardown;
- the race mechanism therefore survives that PoC's high-level rebalance fix.

Pending:

- Fieldwork-owned deterministic synthetic fixture;
- candidate rollback behavior for every old-side failure point;
- KVM rerun of the hotplug reproducer;
- VFIO/SHM BAR-specific ordering review beyond the source paths already mapped;
- migration/snapshot interaction with a release that is in progress.

## Stop condition

Select an address-reuse publication rule only when:

1. every old-address conflicting registry is named for each supported BAR family;
2. synthetic hotplug cannot acquire old before those registries are retired;
3. failure injection before publication keeps old unavailable and restores/retains truthful state;
4. new-side failure unwinds before releasing the new allocator reservation;
5. a KVM-backed reproducer loses its EEXIST sequence under the candidate;
6. parent rebalance still succeeds with the new release ordering.

## Next safe action

Implement the deterministic three-registry fixture as a Fieldwork baseline/candidate oracle. In parallel, map VFIO and shared-memory BAR old-side resources so the publication point is defined across BAR families rather than only virtio config BAR ioeventfds.
