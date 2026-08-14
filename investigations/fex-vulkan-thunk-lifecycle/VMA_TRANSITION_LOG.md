# Executable VMA transition lifetime log

Date: 2026-08-14

## Purpose

The current integrated thunk-lifetime candidate retires dynamic thunk ownership around guest `munmap`. Source review shows that `MAP_FIXED` replacement, `mremap`, execute-permission removal, and `shmdt` use ordinary guest-range invalidation rather than the synthetic-key owner-retirement transaction.

This log tracks real-FEX tests of those non-`munmap` executable ownership transitions.

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

If H executes generation 2, the old bridge survived the destruction of its original executable owner and silently attached to unrelated replacement code solely because the virtual address was reused.

That is a stronger ABA demonstration than a simple fault: the stale route can look healthy.

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

- `map-fixed`: replace T at the same virtual address with new code returning `222`, without re-registering H, then call H.
- `mprotect`: remove all access with `PROT_NONE`, call H in a child to observe the invalid state, then reuse the same T for code returning `333` and call H again without re-registering.

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

## Source-ordering finding

The FEX syscall implementation makes the production ordering requirement concrete.

For `GuestMmap`, host `mmap()` runs first. Only afterward does `TrackMmap()` / `TrackVMARange()` discover and delete any overlapped old VMA owner, followed by ordinary range invalidation.

Therefore a `MAP_FIXED` lifetime repair that depends on the old mapping owner must inspect/retire the overwritten executable dependencies **before** the host `mmap()` destroys that mapping. After the kernel replacement, the old executable owner is already gone.

For `GuestMprotect`, host `mprotect()` also occurs before FEX changes tracked protection flags and performs ordinary range invalidation. If executable ownership is part of bridge validity, dependencies must be retired or transitioned before removing executable permission, then the VMA state can be committed after syscall success.

This argues for a prepare/commit shape around destructive mapping syscalls rather than adding more post-hoc scans after each operation.

## Planned controls

- stock FEX;
- current integrated lifetime candidate;
- same-address replacement sentinel values;
- execute-permission removal/restoration;
- later generalized owner-token candidate based on VMA/`MappedResource` generation identity.

The desired production behavior after the original owner is destroyed is revoked/tombstoned H until a legitimate new claim explicitly reactivates it. Same-address replacement alone must not reactivate a thunk bridge.

## Related design

See [MAPPED_RESOURCE_OWNERSHIP.md](./MAPPED_RESOURCE_OWNERSHIP.md) for the proposed non-reusable mapping-owner token and reverse dependency index.

## External-contact state

No third-party/upstream interaction. All experiments remain in repositories owned by `teamleaderleo`.