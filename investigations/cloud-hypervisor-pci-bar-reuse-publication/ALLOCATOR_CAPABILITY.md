# Cloud Hypervisor PCI BAR relocation — allocator capability boundary

## In simple words

The current address allocator can reserve two disjoint BAR ranges at once. It cannot reserve an overlapping relocation target while the old BAR range remains allocated.

That means the idealized sequence

```text
reserve NEW
-> retire OLD side effects
-> publish OLD free
```

is directly expressible with current allocator calls only when NEW and OLD are disjoint.

For an overlapping relocation, current calls force a choice:

```text
keep OLD leased  -> overlapping NEW allocation fails
free OLD         -> overlapping NEW becomes possible, but OLD is immediately visible to competitors
```

This is an allocator capability boundary, not yet a proposed product change.

## Exact source

Cloud Hypervisor upstream `main` was rechecked at:

`69d4c0a82ef15b2660906013bd87ae32668e7998`

Relevant implementation:

`vm-allocator/src/address.rs::AddressAllocator`

Current state representation is an ordinary non-overlapping `BTreeMap<GuestAddress, GuestUsize>`.

`allocate(Some(address), size, alignment)` validates the requested interval against every currently allocated interval. `free(address, size)` removes an exact allocation immediately.

There is no relocation token, provisional overlapping reservation, owner identity, or delayed-publication state in the allocator API.

## Executed capability discriminator

Owned-fork branch:

`teamleaderleo/cloud-hypervisor:research/ch-pci-bar-r599-allocator-capability`

Authoritative run/job:

`31896803156` / `95041249536`

Artifact:

`9250017518`

Artifact digest:

`sha256:0d9f96c4a627ed784534986fecc6155fe3bf0c9b23e6026f91649eb0f8572490`

The workflow compared `vm-allocator/src/address.rs` byte-for-byte with exact upstream before injecting one test-only discriminator.

Fixture:

```text
allocator region = [0x1000, 0x11000)
OLD              = [0x4000, 0x5000)
disjoint NEW     = [0x8000, 0x9000)
overlapping NEW  = [0x4800, 0x5800)
```

Executed observations:

1. allocate OLD -> succeeds;
2. allocate disjoint NEW while OLD remains allocated -> succeeds;
3. allocate overlapping NEW while OLD remains allocated -> returns `None`;
4. free OLD;
5. a simulated competing client can immediately allocate OLD -> succeeds;
6. while that competitor owns OLD, the intended overlapping NEW remains blocked;
7. after competitor releases OLD, overlapping NEW becomes allocatable.

The focused discriminator passed, and the full allocator suite passed:

```text
vm-allocator unit tests: 21 passed, 0 failed
vm-allocator doc tests:   2 passed, 0 failed
```

No product source was retained from this probe; the only source modification was the temporary test.

## What this proves

Existing `allocate` / `free` ordering alone cannot express a universal BAR relocation transaction with both of these properties:

```text
A. OLD remains unavailable to unrelated allocator clients until old-side teardown completes
B. an overlapping NEW target is reserved before OLD becomes publicly reusable
```

For disjoint OLD/NEW ranges, the current allocator can satisfy both by reserving NEW while OLD remains allocated.

For overlapping OLD/NEW ranges, an additional coordination mechanism is required.

## The next local question

Before adding allocator reservation state, test the simpler existing coordination surface: the allocator mutex.

Current `AddressManager::move_bar()` holds the selected allocator lock only across:

```text
free OLD
-> allocate NEW
```

and releases it before bus/KVM/device teardown.

If the same lock can safely remain held until every conflicting OLD-address side effect is retired, then competitors remain blocked during the otherwise dangerous interval even though OLD has been removed from the allocator map. That could support overlapping relocation without changing allocator representation.

The next source/runtime audit therefore asks:

```text
Can the selected PCI allocator mutex span old bus/ioevent/memslot/device teardown
without re-entrant allocation, lock inversion, or long-lived policy problems?
```

If yes, test lock-extension as the minimum #599 candidate.
If no, the evidence justifies allocator-visible relocation reservation state or another explicit serialization owner.

## Boundary

This note does not claim that holding the allocator lock longer is already safe. KVM operations, device callbacks, VFIO paths, and lock ordering must be audited before execution.

It also does not alter #598's guest-visible BAR release/install semantics. This lane continues to own only address reuse publication.

External-contact state: false. Cloud Hypervisor upstream remained read-only.
