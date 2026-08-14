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

## Planned controls

- stock FEX;
- current integrated lifetime candidate;
- same-address replacement sentinel values;
- execute-permission removal/restoration if the first test is stable;
- later generalized owner-token candidate based on VMA/`MappedResource` generation identity.

The desired production behavior after the original owner is destroyed is revoked/tombstoned H until a legitimate new claim explicitly reactivates it. Same-address replacement alone must not reactivate a thunk bridge.

## Related design

See [MAPPED_RESOURCE_OWNERSHIP.md](./MAPPED_RESOURCE_OWNERSHIP.md) for the proposed non-reusable mapping-owner token and reverse dependency index.

## External-contact state

No third-party/upstream interaction. All experiments remain in repositories owned by `teamleaderleo`.