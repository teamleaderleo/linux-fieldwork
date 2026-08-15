# Cloud Hypervisor `vm-device::Bus` exact-current stack

## In simple words

Three independently proven bugs now sit in the same small generic address-routing primitive on Cloud Hypervisor current `main`:

1. failed relocation can delete the old route (#677);
2. concurrent inserts can both admit overlapping routes (#678);
3. high-address overlap arithmetic panics in debug and wraps to a wrong answer in release (#679).

Each has its own discriminator and evidence carrier. This record tracks only their **composition**: whether the three narrow repairs commute cleanly when present in one implementation.

## Exact source

- canonical project: `cloud-hypervisor/cloud-hypervisor`
- exact upstream base rechecked at stack start: `69d4c0a82ef15b2660906013bd87ae32668e7998`
- owned-fork research branch: `teamleaderleo/cloud-hypervisor:research/ch-bus-r677-r678-r679-stack`
- composition workflow run: `31896567927` (in progress when this checkpoint was written)

## Independent evidence entering the stack

### #677 — failed `update_range()` loses OLD

Authoritative run `31894236231`, artifact `9249356643`.

Repair invariant:

```text
validate NEW while OLD still exists
-> on conflict return with map unchanged
-> only then replace OLD with NEW
```

### #678 — concurrent `insert()` splits validation from commit

Authoritative run `31894509011`, artifact `9249424561`.

Repair invariant:

```text
one devices.write() guard
-> validate overlap
-> insert before releasing guard
```

The concurrency discriminator uses a test-only barrier so both threads cross the old validation point before either can commit. That proof stays workflow-only; the product repair adds no test hook.

### #679 — overlap endpoint arithmetic overflows `u64`

Authoritative debug/release run `31894811738`, artifact `9249514376`.

Repair invariant:

```text
keep the existing half-open range relation
-> evaluate endpoint sums in u128
```

No new public range-rejection policy is introduced.

## Combined candidate

The stack intentionally preserves three separate claims:

```text
BusRange::overlaps(): representation-only endpoint widening
Bus::insert():        one-lock validation + commit
Bus::update_range():  one-lock preflight + OLD->NEW mutation
```

Permanent source regressions cover #677 and #679. #678 remains deterministically exercised by temporary barrier instrumentation around both baseline and combined candidate.

## Scope boundary

This record is limited to `vm-device::Bus` and its range map.

It does not absorb #599's wider PCI BAR allocator/ioeventfd/memslot publication transaction. That lifecycle has different owners and remains a successor after the generic map primitive is cleaned up.

## Current checkpoint

The composition run starts from pristine exact-current `vm-device/src/bus.rs`, re-exercises all three losing baselines, materializes the combined candidate, reruns the concurrency discriminator against the combined implementation, runs full `vm-device` tests/Clippy/rustfmt/diff checks, and commits the tested candidate only after those gates succeed.

External-contact state: false. Cloud Hypervisor upstream remains read-only.
