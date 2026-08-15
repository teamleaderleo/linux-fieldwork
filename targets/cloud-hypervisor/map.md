# Cloud Hypervisor target map

## In simple words

Cloud Hypervisor has become a productive recurring Fieldwork target because several high-consequence subsystems expose comparatively compact ownership and lifecycle loops. QCOW metadata, device-bus routing, BAR relocation, VM lifecycle reporting, migration state, ACPI construction, and host-policy boundaries can often be reduced to explicit state transitions with a small deterministic discriminator.

The useful target characteristic is the ratio:

```text
bounded local reasoning
+ executable failure or schedule injection
+ consequential integrity/lifecycle effect
= high-value investigation
```

This does not make every Cloud Hypervisor subsystem simple. Migration protocols, architecture-specific firmware/device behavior, KVM/MSHV integration, and externally visible compatibility can have a much wider proof radius.

## Current source identity

- Canonical project: `cloud-hypervisor/cloud-hypervisor`
- Canonical repository: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor
- Canonical branch: `main`
- Current upstream `main` during the 2026-08-15 target refresh: `69d4c0a82ef15b2660906013bd87ae32668e7998`
- Owned fork: `teamleaderleo/cloud-hypervisor`
- Public submitted QCOW PR 8721 head during this refresh: `284a2d42b98c514f57d3e89240861196d94fc6cb`

There is no imported `upstream/cloud-hypervisor` tree in Linux Fieldwork. Exact source work currently uses the owned fork and canonical upstream repository directly. Refresh upstream, fork, active PR, and branch identities before any new candidate or publication decision.

## Relevant programmes

- `filesystems-images` — QCOW ownership, refcounts, cache publication, disk-image recovery
- `services-resources` — VM lifecycle, migration, cleanup, state publication
- `boot-kernel` — PCI/device hotplug, BAR routing, KVM-backed device transitions
- `security-networking` — Landlock and host-resource access boundaries
- `ecosystem-contributions` — bounded source candidates and upstream review after explicit authorization

## Current high-value clusters

### QCOW metadata and allocator lifecycle

The strongest recurring pattern is explicit ownership/publication/reuse ordering:

```text
allocate
-> establish ownership/refcount
-> populate metadata/data dependency
-> publish pointer
-> retire predecessor
-> flush durable metadata
-> publish predecessor for allocator reuse
```

Useful current carriers:

- Fieldwork #609 / upstream PR 8721 — fresh and relocated L2 ownership before L1 publication; review removed the remaining deferred old-L2 release path.
- Fieldwork #611 — final shutdown can clear QCOW DIRTY after metadata synchronization failure.
- Fieldwork #634 — recursive refcount-block ownership can fail after a replacement top-level pointer has already moved.
- Fieldwork #645 — dirty cache eviction can discard retryable metadata; the candidate composes cleanly with PR 8721 using `allocate -> refcount=1 -> successful cache insertion -> publish L1`.

The important stop boundary from #645/#634 is that L2 publication ordering and recursive refcount rollback have different failure owners. A local L2 repair should not silently absorb the recursive refcount transaction.

### Generic bus routing and PCI BAR lifecycle

Current-main source also exposes compact range-map invariants:

```text
validate route
-> publish route
-> relocate route
-> reject conflict without losing old route
```

Current carriers:

- Fieldwork #599 — wider PCI BAR allocator address reuse becomes visible before old ioeventfd/memslot teardown finishes.
- Fieldwork #677 — `Bus::update_range()` removes OLD before a fallible NEW insert; current-main baseline loses OLD on `Overlap`, while one-lock preflight keeps the map unchanged.
- Fieldwork #678 — `Bus::insert()` validates overlap under a read lock and commits later under a write lock; a deterministic barrier proves two overlapping concurrent inserts can both succeed.

These findings are intentionally split. Same file or same helper family does not imply one invariant. Keep failure-atomic relocation, concurrent insertion, and BAR lease publication independently executable even if a later review stacks their source changes.

### Lifecycle and API state

Cloud Hypervisor has repeatedly produced useful work where external lifecycle state is reported before or after the real VM transition. Favor exact state-machine assertions around create/boot/shutdown/delete, migration receive/send, retries, and event publication. Preserve the actual VMM-owned completion event rather than using indirect symptoms such as SSH loss.

### Architecture and firmware boundaries

ACPI, AArch64 cache discovery/topology, TDX/TDVF, and firmware handoff are productive when the fixture can keep the policy boundary explicit. These areas have a wider compatibility surface than the QCOW and generic-map examples, so require stronger architecture/backend controls before broadening a candidate.

### Host-access policy

Landlock and backing-file restore/open paths are useful when the operation owner and host path contract are explicit. Compare direct open, restore, migration, and backing-file paths instead of assuming one policy hook covers all entry points.

## Review heuristics specific to Cloud Hypervisor

1. Write the state transition before reading the implementation details: ownership, publication, cleanup, durability, reuse, or route replacement.
2. Mark every fallible arrow and inspect what survives after failure.
3. Prefer deterministic allocator budgets, barriers, synthetic devices, and reopen/rerun controls over scheduler luck or host-wide exhaustion when they exercise the real product owner.
4. When metadata or routing is protected by one lock domain, challenge split validation/commit or caller-deferred bookkeeping that creates states the owner could eliminate locally.
5. After the smallest repair exists, challenge one nearby intermediate state. Broaden only while the same owner and invariant remain in charge.
6. Stop when rollback or cleanup enters another transaction owner, backend, architecture, policy, or independently testable invariant.
7. Pair failure regressions with successful lifecycle controls when ownership/release changes.
8. Recheck current upstream `main` before executing an old Fieldwork “next action”; Cloud Hypervisor changes quickly and older issue bodies may retain valid historical receipts while their routing text becomes stale.
9. Keep KVM-required proof separate from generic helper proof. A local map/cache bug can be proven without KVM while the end-to-end VMM consequence remains a later integration gate.
10. Review exact current head after every semantic revision; PR review and CI from an older head do not certify a later cleanup.

## Useful source areas

### Block / QCOW

Start in:

- `block/src/formats/qcow/metadata.rs`
- `block/src/formats/qcow/refcount.rs`
- `block/src/formats/qcow/vec_cache.rs`
- parser/reopen/free-list construction around dirty-refcount recovery

Ask who owns each pointer/refcount/free-list transition and which metadata must be durable before reuse.

### Generic device bus

Start in:

- `vm-device/src/bus.rs`

Useful invariants include non-overlap, failure-atomic relocation, check/commit atomicity under concurrent insertion, high-address range arithmetic, weak-reference lifetime, and lookup behavior after device destruction.

### PCI / device manager

Start in:

- PCI BAR/configuration relocation code
- `vmm/src/device_manager.rs::AddressManager`

Track allocator ownership, MMIO/PIO bus mappings, ioeventfds, KVM user-memory regions, device tree resources, and device-local BAR state as separate resources. An address should become reusable only after the old side effects that conflict with a new owner are retired.

### Migration / VM lifecycle

Trace state ownership through API entry points, VM state changes, migration protocol messages, retry/error paths, and lifecycle events. Distinguish local state mutation from peer-visible or API-visible completion.

## Current stop / promotion rules

Promote a Cloud Hypervisor source candidate when it has:

- refreshed exact upstream source identity;
- one bounded invariant and repair owner;
- a losing baseline or deterministic source-level discriminator;
- a passing control;
- relevant history/review checked;
- exact-head execution of focused and nearby tests;
- required Clippy/rustfmt/diff gates;
- KVM/backend/architecture execution when the claim depends on it;
- a written evidence boundary separating generic-helper proof from end-to-end VMM consequence;
- refreshed overlap search and current upstream review state.

A local helper fix may be fully proven while a wider production consequence remains a successor. Preserve that distinction instead of inflating the claim.

## Reusable process lesson

[`../../notes/processes/reasoning-radius-can-justify-local-simplification.md`](../../notes/processes/reasoning-radius-can-justify-local-simplification.md) records the scope lesson that has now repeated across QCOW and bus-map work:

```text
prove smallest invariant
-> challenge one nearby intermediate state
-> keep broader variant if it deletes failure-bearing state inside the same owner
-> stop and split when the next step changes failure owner or invariant
```

[`../../FIELD_GUIDE.md`](../../FIELD_GUIDE.md) now carries the compact general form.

## Authority

This target map grants no permission to contact Cloud Hypervisor maintainers or mutate the canonical upstream repository. Owned-fork research, test branches, and internal records remain separate from upstream issues, comments, reviews, and pull requests. External interaction requires an explicit human decision, except for already-authorized interactions in the surrounding conversation.
