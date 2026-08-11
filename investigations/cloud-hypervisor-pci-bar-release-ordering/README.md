# Cloud Hypervisor PCI BAR release/install ordering

Updated: 2026-08-11

Fieldwork issue: `teamleaderleo/linux-fieldwork#598`
Upstream issue: https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8572
Canonical source: `cloud-hypervisor/cloud-hypervisor` `main` @ `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Public design branch reviewed: `yamahata/cloud-hypervisor:202607/pci-bus-eagar-unmap`
Current state: **current-source defect mechanism confirmed; two execution discriminators pending**
Upstream-contact state: **disabled / no contact performed**

## TL;DR

Cloud Hypervisor currently treats a BAR address write while PCI memory decoding is disabled as a deferred **move**. The guest-visible BAR register is updated immediately, but the old allocator reservation and MMIO bus mapping remain in place until MSE is enabled. That defeats a normal rebalance sequence where one device is assigned the old address of another device before either device is re-enabled.

Upstream issue 8572 gives the minimal sequence:

```text
F0 disabled, BAR0=A0
F1 disabled, BAR0=A1

write F1 BAR0=A2
write F0 BAR0=A1
enable F0
-enable F1
```

Current code reaches `enable F0` while F1 still owns A1 in the allocator/MMIO mapping, so F0's deferred A0→A1 move collides.

A public PoC splits relocation into **release** and **install**: release the old BAR resources as soon as the guest reprograms the BAR while decode is disabled, then install the new mapping on the decode-enable edge. That directly addresses the rebalance ordering.

There is a second ordering rule that must stay separate: an address must become reusable only after all old consumers are gone. Current `AddressManager::move_bar()` frees the allocator range before the old virtio ioeventfd is unregistered. The issue discussion contains a reproduced concurrent hotplug failure where a new device reused the released address and its `KVM_IOEVENTFD` registration hit `EEXIST` because the old ioeventfd was still registered.

The repair therefore needs two explicit transitions:

```text
MAPPED -> RELEASED -> INSTALLED(new)
```

and one publication rule:

> A released BAR address becomes allocatable to another device only after bus mappings, ioeventfds, guest-memory mappings, and other old-address side effects that conflict with reuse have been removed.

## Explain like I'm five

Two devices are parked in spaces A0 and A1.

The guest turns both devices off, tells device 1 to move from A1 to A2, then tells device 0 to move from A0 to A1.

Cloud Hypervisor writes the new parking-space numbers on the devices but leaves both old spaces occupied until each device is turned back on.

When device 0 is turned on first, it asks for A1 and gets told A1 is still occupied by device 1.

The clean model is:

```text
device turned off + BAR changed -> vacate old space
later device turned on           -> occupy new space
```

There is one catch: "vacate" must include every old reservation, including kernel ioeventfds. Publishing the space as free before those are gone lets a new device arrive too early.

## Why care

Firmware and operating systems legitimately rebalance PCI resources while memory or I/O decoding is disabled. The current deferred-move model can reject an ordering that worked before the move_bar logic and that requires no final overlap.

The same lifecycle also participates in hotplug, KVM ioeventfd registration, shared-memory BAR mappings, snapshot/migration state, allocator bookkeeping, and the device tree. A partial release can create a different failure even when the headline rebalance succeeds.

## Exact current-source result

### 1. BAR writes are queued while MSE is off

`PciConfiguration::write_config_register()`:

1. writes the guest-visible config register;
2. calls `detect_bar_reprogramming()`;
3. that function updates the internal `bars[].addr` shadow and returns `BarReprogrammingParams { old_base, new_base, len, region_type }`;
4. the params are pushed onto `pending_bar_reprogram`;
5. pending params are returned to the bus only if `COMMAND_REG_MEMORY_SPACE_MASK` is currently enabled.

With MSE disabled, the function returns no relocation action and keeps the params queued.

That is the exact source mechanism described by issue 8572 on current main.

### 2. The old allocator and bus range stay live during the deferred window

No relocation reaches `AddressManager` until the queued params are returned. Therefore a BAR changed while MSE is off still owns its original allocator reservation and MMIO bus range.

For the two-device sequence:

```text
initial live ranges: F0=A0, F1=A1
F1 register says A2, live range still A1
F0 register says A1, live range still A0
```

Enabling F0 returns A0→A1. `AddressManager::move_bar()` frees A0 and tries to allocate A1. F1 still owns A1, so allocation fails.

### 3. April rollback protects consistency after that failure

Commit `e38c5c434038776a7c2cc01d9dbe72d3c057d493` added rollback when `move_bar()` fails.

Current bus code logs the failed move and calls `device.restore_bar_addr(params)`, restoring the config-space address to the old live mapping. `AddressManager::move_bar()` also attempts to restore the allocator's old range if allocation of the new range fails.

This is valuable recovery. It changes the failure from "new config address + old MMIO mapping" to a consistent old state.

It does not let the two-device rebalance complete. F0 still loses the requested A1 assignment because F1 retained its stale A1 reservation throughout the disabled interval.

## Adjacent invariant: MSE-off mapping visibility

The bus range remains installed while MSE is disabled. Device `read_bar()` / `write_bar()` implementations such as virtio-pci operate on the bus callback and do not perform a local MSE check in the read/write path reviewed here.

This suggests a separate observable discriminator:

> After the guest clears MSE, does an MMIO access to the old BAR still reach the device until the BAR is later relocated?

Do not promote this as a second defect from source reading alone. Run a tiny bus/device fixture. If the bus or another layer suppresses the access, retain a negative result. If the callback fires, the eager-release design also restores decode-disable behavior, not only rebalance ordering.

## Public PoC design evidence

The public branch `202607/pci-bus-eagar-unmap` changes the model from a list of deferred moves to explicit release/install plans.

Important concepts in the inspected source:

- per-BAR `mapped_addr` tracks the live mapping separately from guest-visible BAR registers;
- when a BAR write changes an address and the BAR is currently mapped, the plan emits a `release` immediately and records the slot pending;
- if decode is already enabled, an `install` can accompany the release;
- if decode is disabled, install waits for the IOSE/MSE 0→1 edge;
- a failed install leaves the BAR pending and unmapped so a later decode-enable edge can retry;
- install targets are read from the live BAR registers when drained;
- pending state is indexed by BAR slot rather than inferred by matching addresses.

This is a stronger state model than current `old_base/new_base` pending moves. Treat it as design evidence, not as a selected implementation.

## Second defect sequence: reuse before old ioeventfd teardown

The issue discussion records a separate reproduced sequence during concurrent virtio-pmem hotplug:

```text
old ioeventfd registration exists
old BAR allocator range becomes free
hotplug allocates the old address
new ioeventfd registration at that address -> EEXIST
old ioeventfd is later deassigned
relocated ioeventfd registers at new address
```

Current `AddressManager::move_bar()` ordering supports that explanation.

For an MMIO BAR it:

1. frees `old_base` from the address allocator;
2. allocates `new_base`;
3. updates the MMIO bus range;
4. updates device-tree resources;
5. for a virtio config BAR, unregisters ioeventfds at `old_base`;
6. registers ioeventfds at `new_base`;
7. finally calls the device's `move_bar()` hook.

The allocator therefore advertises the old address as reusable before step 5 removes the old KVM ioeventfd.

An eager-release implementation makes this ordering decision more important because it intentionally creates a released interval between BAR write and BAR enable.

## Two state machines to preserve

### BAR mapping state

```text
Mapped(old)
  |
  | guest changes BAR while decode disabled
  v
Released(old, target=new)
  |
  | guest enables decode + target install succeeds
  v
Mapped(new)
```

A failed install should remain `Released(... target=new)` or move to an explicitly chosen rollback state. It should not claim `Mapped(new)`.

### Address reuse state

A physical guest address passes through more than allocator occupancy:

```text
allocator reserved
MMIO/PIO bus range installed
KVM ioeventfds registered (some devices)
KVM user-memory region installed (shared-memory BARs)
device-tree resource names old base
device-local BAR bookkeeping names old base
```

The address is reusable by an unrelated device only when every old-address resource that can collide with that reuse has been retired.

A single `allocator.free(old)` at the beginning of teardown publishes availability too early for that rule.

## First executable discriminator — two-device rebalance

This can be exercised without a real guest.

Use two `PciConfiguration` instances with one equal-sized memory BAR each and a tiny relocation harness that tracks occupied ranges.

Initial state:

```text
occupied = {A0:F0, A1:F1}
F0 MSE=0, BAR=A0
F1 MSE=0, BAR=A1
```

Sequence:

1. write F1 BAR=A2 while MSE=0;
2. assert current baseline returns no relocation and occupied still contains A1;
3. write F0 BAR=A1 while MSE=0;
4. assert current baseline returns no relocation and occupied still contains A0/A1;
5. set F0 MSE=1;
6. current baseline returns A0→A1; relocation harness frees A0 then rejects A1 because F1 owns it;
7. apply current rollback and assert F0 returns to A0;
8. enable F1 as a control and observe A1→A2 can then succeed.

Candidate discriminator:

- after step 1, F1 old A1 must be released;
- after step 2, F0 can target A1 without collision;
- enabling F0 installs A1;
- enabling F1 installs A2;
- final occupied set is `{A1:F0, A2:F1}`.

This directly separates "rollback is correct" from "rebalance succeeds".

## Second executable discriminator — reuse publication

Model one virtio BAR move with an address allocator and a fake KVM ioevent registry.

Track explicit side effects:

```text
old address allocated
old bus range present
old ioevent present
```

Begin release while a competing hotplug attempts to allocate old address at each transition point.

Required rule:

- hotplug cannot observe old address as reusable while old conflicting KVM/bus state remains;
- after all old-address teardown succeeds, hotplug may allocate it;
- teardown failure must leave an accurate retry/rollback state with no double-free or duplicated registration.

A deterministic synthetic registry is preferable to racing real threads for the first proof. A real KVM race can follow once the ordering is selected.

## Failure ownership matrix

| step | failure owner | required state after failure |
|---|---|---|
| remove old ioeventfd | KVM/device teardown | address still unavailable to other devices; old live mapping accurately represented |
| remove old bus range | bus | allocator publication must match actual bus ownership |
| release allocator | allocator | all earlier conflicting users already retired |
| allocate new address | allocator | BAR remains released/pending or chosen rollback is complete |
| install new bus range | bus | allocator/new mapping rollback or pending state explicit |
| register new ioeventfd | KVM | new range must not be published as fully installed until registration succeeds |
| update device tree/local BAR | metadata/device | metadata must describe whichever mapping is actually live |

The exact implementation may order these differently. The table exists to force every error edge to have one truthful state.

## Migration/snapshot boundary

Current `PciConfiguration` snapshots pending BAR reprogramming state. The public PoC changes these data members and notes migration compatibility as a design consideration.

Before selecting a new state representation, test at least:

1. snapshot while BAR is stably mapped;
2. snapshot after guest BAR write while decode is disabled and old mapping has been released;
3. restore then enable MSE;
4. source and restored VM reach the same final BAR/mapping state;
5. current migration-version policy can either default the new fields safely or explicitly gate incompatible state.

Do not let snapshot compatibility force address-based matching if BAR index gives a more truthful identity.

## Candidate design constraints

Any candidate should satisfy all of these:

1. **Decode semantics:** changing a BAR while its decode space is disabled may release the old decoded mapping immediately.
2. **Per-BAR identity:** carry BAR index/slot in state; overlapping or repeated addresses must not be the primary identity.
3. **Atomic reuse publication:** an old range is allocatable to another device only after conflicting old-address side effects are gone.
4. **Deferred install:** new address install may wait for the decode-enable edge.
5. **Retry truth:** failed install leaves explicit pending/unmapped state or completes a full rollback.
6. **64-bit BAR correctness:** low/high writes can arrive in either order; install target comes from the complete live register pair.
7. **IO BAR parity:** IOSE follows the same lifecycle with PIO resources.
8. **ROM BAR policy:** expansion ROM enable/address semantics need their own discriminator.
9. **Hotplug coexistence:** released addresses can eventually feed hotplug, but only after teardown publication is complete.
10. **Migration compatibility:** in-flight release/pending state has an explicit restore contract.

## What the April rollback teaches

The rollback patch is evidence that a BAR move is a transaction across several representations. It restored config/allocator state on one failure class.

The next repair should avoid layering another local patch on top of `move_bar()` without defining the complete transaction. Eager release widens the interval between teardown and install, which makes accurate state and reuse publication more important.

## Evidence boundary

Established on exact current source:

- MSE-off BAR changes update guest-visible/internal BAR address state while keeping relocation pending;
- allocator/MMIO mapping remains at the old address until MSE enable returns the relocation;
- issue 8572's two-device collision mechanism therefore remains present;
- current failed-move rollback restores old config/allocator state after rejection;
- `AddressManager::move_bar()` frees the allocator range before old virtio ioeventfd teardown;
- the public issue discussion contains a reproduced hotplug `KVM_IOEVENTFD` EEXIST sequence matching that ordering;
- public eager-unmap PoC introduces explicit mapped/released/pending/install concepts and BAR-index identity.

Still pending here:

- executable synthetic reproduction on the exact current head;
- MSE-off MMIO callback observation;
- deterministic reuse-publication fixture;
- candidate selection among PoC semantics or a smaller transactional design;
- snapshot/migration fixture for an in-flight released BAR;
- KVM-backed verification after a source-level candidate.

## Stop condition

Select a candidate only when:

1. the two-device baseline collision is executable and deterministic;
2. a candidate reaches final `{F0:A1, F1:A2}` regardless of enabling F0 before F1;
3. old-address reuse stays blocked until all conflicting old side effects are retired;
4. injected teardown/install failures leave one truthful retriable or rolled-back state;
5. 32-bit memory, 64-bit memory, and at least one IO/ROM control establish the intended scope;
6. an in-flight released BAR survives snapshot/restore according to the chosen compatibility rule.

## Next safe action

Build two pure unit fixtures on a controlled fork:

1. the two-device allocator collision/rebalance sequence against current code;
2. the old-address reuse/ioeventfd publication sequence with synthetic registries.

Keep them baseline-only first. After the current failure order is frozen, compare the public PoC state model and one minimal transaction-oriented candidate without touching upstream.
