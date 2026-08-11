# BAR relocation snapshot compatibility review

Updated: 2026-08-11

Parent: `README.md`
Canonical current source: `cloud-hypervisor/cloud-hypervisor` @ `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Public eager-release design reviewed: `yamahata/cloud-hypervisor:202607/pci-bus-eagar-unmap`

## TL;DR

The public eager-release design changes runtime BAR bookkeeping substantially but deliberately preserves the existing serialized `pending_bar_reprogram` field and its `old_base -> new_base` meaning.

Cloud Hypervisor serializes component snapshot state as **JSON strings** through `vm-migration::SnapshotData`. That makes the proposed additive `bar_idx` field wire-friendly in both directions:

- new code marks `bar_idx` with `#[serde(default)]`, so old JSON lacking the field deserializes with zero and then falls back to target-based slot resolution;
- old code's serde struct has no `bar_idx` field and, absent `deny_unknown_fields`, ignores the extra key emitted by new code.

The harder semantic direction—snapshot while a BAR is eagerly RELEASED on a new binary, then restore on an old binary—also has a plausible preserved contract:

1. guest-visible config registers already contain the new target;
2. `pending_bar_reprogram` serializes the released-from OLD base and current NEW target;
3. device-tree BAR resource metadata remains at OLD until an install commits;
4. restore materializes the device resources at OLD;
5. old code receives the legacy pending move OLD→NEW and replays it when the relevant decode bit is enabled.

The reverse direction is explicitly represented by the PoC's `RESTORED_INFLIGHT` state: old snapshots restore as physically mapped at OLD with the move still pending, then the next MSE/IOSE edge re-releases OLD and installs the current config target.

This source review supports the compatibility design. A real N↔N+1 live-migration/snapshot matrix is still required before the candidate can claim cross-version compatibility.

## Snapshot format is self-describing JSON

Current `vm-migration/src/lib.rs` stores each leaf state as:

```rust
#[derive(Clone, Default, Deserialize, Serialize)]
pub struct SnapshotData {
    state: String,
}
```

Creation uses:

```rust
serde_json::to_string(state)
```

Restore uses:

```rust
serde_json::from_str(&self.state)
```

So this is not a positional bincode-style struct encoding. Additive fields can be ignored by older serde structs, and new fields can use serde defaults when reading older JSON.

That is an important prerequisite for the PoC's compatibility approach.

## Existing current-main wire state

Current `PciConfigurationState` already serializes:

- config registers;
- writable bits;
- BAR descriptors;
- ROM BAR state;
- capability metadata;
- `pending_bar_reprogram: Vec<BarReprogrammingParams>`.

Current `BarReprogrammingParams` carries:

```text
old_base
new_base
len
region_type
```

Current code restores this vector verbatim and keeps it pending until the guest enables the relevant decode space.

That field predates the eager-release proposal and therefore provides an existing migration wire concept for an in-flight BAR move.

## PoC wire preservation

The PoC keeps `PciConfigurationState.pending_bar_reprogram` rather than serializing its new runtime arrays directly.

Its wire struct adds:

```rust
#[serde(default)]
bar_idx: usize
```

while preserving:

```text
old_base
new_base
len
region_type
```

`state()` converts runtime `pending_relocation[slot]` into the legacy-style record:

```text
bar_idx  = slot
old_base = released_from
new_base = current config-space target
len      = BAR length
region_type = BAR type
```

`mapped_addr`, `rom_mapped_addr`, and the fixed-size `pending_relocation` arrays remain runtime bookkeeping rather than new serialized state fields.

This is a good compatibility boundary: change the internal state machine while keeping the established migration concept on the wire.

## Old snapshot -> new binary

The PoC covers this direction explicitly.

### Additive field handling

An old snapshot has no `bar_idx`. New code gets the default value zero.

`resolve_pending_slot()` first trusts `bar_idx` only when that slot's type and current target match the pending record. Otherwise it scans all declared BAR slots for one whose config-space target and region type match.

The public branch includes a unit test moving BAR 3, forcing the deserialized `bar_idx` to the legacy default zero, then confirming restore resolves the pending move to BAR 3 instead of BAR 0.

### Physical state reconstruction

Old/current behavior has not eagerly torn the old mapping down while MSE is off. Its snapshot therefore represents:

```text
config register target = NEW
physical/device resource = OLD
pending move = OLD -> NEW
```

New restore code seeds the declared BAR as mapped, overlays the pending record, and explicitly records:

```text
mapped_addr = OLD
pending_relocation = OLD
config target = NEW
```

The PoC names this `RESTORED_INFLIGHT`.

On the next decode-enable edge it emits a release of OLD plus install of NEW. This preserves old-snapshot semantics while moving into the new release/install model.

## New RELEASED snapshot -> old binary

This is the direction that deserves the strongest explicit runtime test.

While new eager-release code is between BAR write and MSE/IOSE enable:

```text
config register target = NEW
physical mapping = absent
runtime pending released_from = OLD
DeviceTree BAR resource = OLD
```

The PoC's snapshot state emits the legacy pending wire record:

```text
OLD -> NEW
```

and leaves the BAR resource metadata at OLD because DeviceTree resources only advance on a successful install.

An old binary restoring the full device snapshot therefore has enough information to reconstruct its own familiar in-flight representation:

```text
materialized BAR/resource = OLD
config target = NEW
pending move = OLD -> NEW
```

Old code does not know the source was physically RELEASED when snapshotted. It does not need to: restore materializes a valid OLD mapping and the legacy pending record tells it how to reach NEW on the next decode edge.

This deliberately maps the new runtime `RELEASED` state onto an older binary's representable `mapped OLD + pending` state at the restore boundary.

## Extra `bar_idx` on new -> old JSON

Old `BarReprogrammingParams` lacks the `bar_idx` member.

Serde's normal struct JSON deserialization ignores unknown object keys unless the destination opts into `deny_unknown_fields`. Current old/current struct does not opt into that restriction.

Therefore a new JSON object such as:

```json
{
  "bar_idx": 3,
  "old_base": 268435456,
  "new_base": 536870912,
  "len": 4096,
  "region_type": "Memory32BitRegion"
}
```

can be read by the old struct using the four keys it knows.

This is the wire-level reason the additive index is plausible in the N+1→N direction.

## Remaining ambiguity: slot identity on old binary

The new `bar_idx` helps new code disambiguate moves by BAR slot. Old code ignores it and still identifies the pending move through the legacy addresses/type.

That is sufficient only if the pending record remains unambiguous to old code under states a new binary can produce.

A cross-version test should include:

1. two same-type BARs with different targets;
2. a move involving BAR 3 or another non-zero slot;
3. a 64-bit BAR tracked on its low slot;
4. repeated writes while released so the current target changes before snapshot;
5. an address swap where two BARs exchange OLD addresses.

The last case is especially useful because the eager-release feature exists to make swaps/rebalances valid. The old binary must restore the serialized pending vector into a sequence it can replay without losing identity.

## Cross-version execution matrix

Use two binaries:

- OLD = exact current-main-style deferred-move binary before eager release;
- NEW = candidate eager-release binary preserving the legacy wire state.

### OLD -> NEW

For each test:

1. clear MSE/IOSE;
2. rewrite one or more BARs;
3. snapshot/migrate before re-enable;
4. restore on NEW;
5. assert resources materialize at OLD;
6. re-enable decode;
7. assert final mapping reaches requested NEW targets.

Required cases:

- one 32-bit MMIO BAR;
- one 64-bit BAR;
- one IO BAR;
- two-BAR swap;
- repeated target rewrite before snapshot.

### NEW -> OLD

Repeat with NEW as source and OLD as destination.

The key distinguishing point is that NEW has already torn down OLD before snapshot. The destination OLD must still reconstruct OLD from saved device/resource state and then replay OLD→NEW.

Assertions:

- destination boot/restore succeeds;
- old address is materialized exactly once;
- config registers retain NEW target;
- pending move exists;
- enabling decode reaches NEW;
- no double-free, overlap, stale ioeventfd/memslot, or duplicate mapping appears.

## Migration version policy

Upstream issue 8706 is separately discussing narrowing the supported migration-version range. That policy can reduce how many historical versions need to interoperate, but it does not remove the need to prove the currently supported N/N-1 or N/N-2 boundary.

Keep this candidate's wire compatibility evidence scoped to whatever versions the project officially supports when the patch is proposed.

## Result of this source review

Positive evidence:

- snapshot leaf state is JSON;
- additive `bar_idx` has a serde default for old->new;
- old structs can ignore the new JSON key for new->old;
- legacy pending move semantics are preserved;
- PoC has same-binary mid-window restore and old-missing-index unit coverage;
- full resource metadata can reconstruct OLD on an older destination.

Open execution:

- actual new-binary snapshot deserialized by an old binary;
- two-BAR swap across versions;
- real DeviceManager/bar resource reconstruction with ioeventfd/memslot-backed devices;
- migration protocol/version gates.

## Recommendation

Keep the legacy JSON pending record. Avoid serializing `mapped_addr` or new internal state-machine arrays unless a future invariant truly requires it.

Before selecting the PoC for upstream, add an explicit NEW→OLD mid-window migration/snapshot test. It is the one direction where source and destination represent the same logical in-flight move with different runtime mapping states, and therefore the best discriminator for the compatibility design.
