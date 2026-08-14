# Executable VMA transition lifetime log

Date: 2026-08-14

## Purpose

The current integrated thunk-lifetime candidate retires dynamic thunk ownership around guest `munmap`. Source review shows that `MAP_FIXED` replacement, `mremap`, `mprotect`, and `shmdt` all use ordinary guest-range invalidation rather than a mapping-owner transaction.

This log tracks real-FEX behavior across those non-`munmap` transitions and separates **mapping-generation replacement** from ordinary protection changes.

## Leading invariant

A FEX bridge that contains or can regenerate a guest executable target must be tied to the lifetime of the executable **mapping generation**, not merely the numeric guest address.

The strongest first discriminator is same-address `MAP_FIXED` replacement:

```text
create executable target T containing generation-1 code
register synthetic H -> T
call H and force translation/cache population
MAP_FIXED a new anonymous mapping over T
write different generation-2 code at the same numeric T
make T executable
call H again without re-registering H
```

If H executes generation 2, the old bridge survived the destruction of its original mapping owner and silently attached to unrelated replacement code solely because the virtual address was reused.

That is a stronger ABA demonstration than a simple fault: the stale route can look healthy.

### `mprotect` is a compatibility control, not automatically an owner change

A mapping can legitimately transition:

```text
RX -> RW/PROT_NONE -> RX
```

without becoming a new mapping generation. Runtimes/JITs can also patch code while preserving ordinary function-pointer identity at the same address.

Therefore the desired production semantics are:

- while T is non-executable, a call through H must obey ordinary guest execute-permission behavior and fail;
- if the **same mapping generation** later becomes executable again at T, H may legitimately reach the current code there;
- permission flips alone should not permanently tombstone H or allocate a new owner token.

The `mprotect` probe is kept as a control for that distinction. The mapping-replacement bug is specifically about new ownership at the same numeric address, not every change to page permissions/content.

## Probe and workflow

Owned FEX branch:

```text
ci/vma-owner-transitions-20260814
```

Probe:

```text
diagnostics/vma-owner-transitions/vma_linkaddress_probe.cpp
```

Workflow:

```text
.github/workflows/vma-owner-transitions-arm64.yml
```

The probe uses:

```text
H = 0x0000700000020000
```

and initially maps anonymous x86-64 code at T returning sentinel `111`, registers `H -> T`, and calls H once to force real FEX translation/cache population.

Two modes are prepared:

- `map-fixed`: replace T at the same virtual address with a **new mapping generation** containing code returning `222`, without re-registering H, then call H.
- `mprotect`: retain the same mapping, remove access with `PROT_NONE`, call H in a child to observe the invalid state, then restore/rewrite the same T to return `333` and call H again without re-registering. This is a protection/identity control.

## Run 1 — harness failure before guest execution

Actions run:

```text
31777826714
carrier: afc88d5c32ff9f6c18a126c8dffb6cd729f72bfc
```

Stock FEX built successfully. The failure occurred while cross-compiling the guest probe, before either VMA transition ran.

The fixture was built with `-Werror` and includes FEX's shared `ThunkLibs/include/common/Guest.h`. GCC reports an inherited warning in `IsLibLoaded()`:

```text
Guest.h:99:22: error: missing initializer for member ... rv [-Werror=missing-field-initializers]
  } argsrv = {libname};
```

This is unrelated to the VMA probe logic. No stock or candidate runtime result exists from run 1.

Artifact:

```text
id:      9210623051
sha256:  04969a7b1bdbb8162c9e78192d33ce4f2a99990821a602e1c02026f5041303a6
```

### Repair

Keep `-Werror` for the fixture but exempt only the inherited initializer warning:

```text
-Wno-error=missing-field-initializers
```

Repair commit:

```text
f1c48899c74ef50479fd87347b2210f62b4b6005
```

The VMA operations and runtime variables were unchanged by the repair.

Run 2 automatically started as Actions run `31778138756`.

## Source-ordering finding

The FEX syscall implementation makes the production ordering requirement concrete.

For `GuestMmap`, host `mmap()` runs first. Only afterward does `TrackMmap()` / `TrackVMARange()` discover and delete any overlapped old VMA owner, followed by ordinary range invalidation.

Therefore a `MAP_FIXED` lifetime repair that depends on the old mapping owner must identify the overwritten dependencies **before** host `mmap()` destroys that mapping. The VMA tracker transition can be committed after a successful syscall.

For `GuestMprotect`, host `mprotect()` also occurs before tracked protection flags and ordinary range invalidation are updated. This does not require a new owner generation. The important invariant is that execution respects current protection state while the mapping-generation identity survives the flip.

This suggests a prepare/commit hook for mapping-generation-destroying operations, while ordinary protection changes stay within the existing VMA identity.

## Planned interpretation

- stock/current candidate returning `222` after `MAP_FIXED` without a new LinkAddress claim demonstrates mapping-generation ABA;
- a future owner-token candidate should revoke H on that replacement until an explicit legitimate claim reactivates it;
- the `mprotect` control should fault while `PROT_NONE` and may return `333` after the same mapping is executable again;
- destructive `mremap` and `shmdt` should eventually be tested as owner-loss cases.

## Related design

See [MAPPED_RESOURCE_OWNERSHIP.md](./MAPPED_RESOURCE_OWNERSHIP.md) for the proposed non-reusable mapping-owner token and reverse dependency index.

## External-contact state

No third-party/upstream interaction. All experiments remain in repositories owned by `teamleaderleo`.