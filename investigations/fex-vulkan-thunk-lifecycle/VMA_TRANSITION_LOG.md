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

## Run 2 — real-FEX mapping-generation ABA reproduced

Actions run:

```text
31778138756
carrier: f1c48899c74ef50479fd87347b2210f62b4b6005
FEX product source: 71afe476751deac24adabd1adb575fd2337b6e0a
lifetime helper: 96d3d1aff38f986f6e8e36e5afd10c04cfe67cf2
runner: ubuntu-24.04-arm
job conclusion: success
```

Artifact:

```text
id:      9210754514
name:    vma-owner-transitions-31778138756
sha256:  ab8c90ddcfa74f1de77d40036d47d658d387c5494781f9855ef2b72de95b7517
```

### `MAP_FIXED` result — decisive

Stock FEX:

```text
VMA first H=0x700000020000 T=0x7ffff7ec4000 value=111
VMA replaced-same-address H=0x700000020000 T=0x7ffff7ec4000 generation=2 sentinel=222
VMA after-map-fixed value=222
```

Current integrated lifetime candidate:

```text
DIAG_REVOKED_H_ACTIVATE H=0x700000020000 T=0x7ffff7ec4000 ...
DIAG_MULTI_ACTIVE H=0x700000020000 T=0x7ffff7ec4000
VMA first H=0x700000020000 T=0x7ffff7ec4000 value=111
VMA replaced-same-address H=0x700000020000 T=0x7ffff7ec4000 generation=2 sentinel=222
VMA after-map-fixed value=222
```

Both phases exit 0 because the probe deliberately treats `222` as the expected demonstration of the current behavior.

This proves a **real mapping-generation ABA**:

1. H was explicitly associated with generation-1 mapping owner at numeric address T.
2. H was translated/cached and returned generation-1 sentinel 111.
3. `MAP_FIXED` destroyed that mapping and installed a brand-new anonymous mapping at exactly the same numeric T.
4. no `LinkAddressToFunction(H, T)` registration occurred for the new mapping;
5. H nevertheless returned generation-2 sentinel 222.

The old bridge therefore survived the destruction of its mapping owner and silently adopted replacement code solely because the target virtual address stayed equal.

The current lifetime candidate does not log any owner drop/revocation at the `MAP_FIXED` transition. That is expected from its current design: retirement is attached to the `munmap` path rather than mapping-generation replacement.

This is the strongest evidence so far for a non-reusable mapping-owner token. Numeric target address alone is insufficient even when the target remains mapped and executable.

### `mprotect` result — fixture status is non-evidentiary for the fault half

Both stock and candidate later report:

```text
VMA execute-permission-restored-with-new-code H=0x700000020000 T=0x7ffff7ec4000 sentinel=333
VMA after-mprotect-reuse value=333
```

That post-restoration behavior is compatible with the intended model: the same mapping generation can survive protection changes and H may continue to identify T once it becomes executable again.

However, the attempted child call while `PROT_NONE` is **not a valid result from this run**. The `fork`/`waitpid` fixture behaves unexpectedly under this FEX guest execution:

```text
VMA waitpid failed errno=10 (No child processes)
VMA dead-call-status=-1
...
VMA child-exit=12
VMA dead-call-status=12
```

The duplicated/continued control flow means the child-fault status is not a clean discriminator. Both `mprotect` cases exit 12 due to the fixture's own expectation logic, not a clean product classification.

A replacement control should avoid guest `fork()`: either run the non-executable call as a separate whole FEX process or use an outer host-side harness to classify the guest process signal/exit.

## Source-ordering finding

The FEX syscall implementation makes the production ordering requirement concrete.

For `GuestMmap`, host `mmap()` runs first. Only afterward does `TrackMmap()` / `TrackVMARange()` discover and delete any overlapped old VMA owner, followed by ordinary range invalidation.

Therefore a `MAP_FIXED` lifetime repair that depends on the old mapping owner must identify the overwritten dependencies **before** host `mmap()` destroys that mapping. The VMA tracker transition can be committed after a successful syscall.

For `GuestMprotect`, host `mprotect()` also occurs before tracked protection flags and ordinary range invalidation are updated. This does not require a new owner generation. The important invariant is that execution respects current protection state while the mapping-generation identity survives the flip.

This suggests a prepare/commit hook for mapping-generation-destroying operations, while ordinary protection changes stay within the existing VMA identity.

## Next implementation experiment

Extend the existing revoked-H/multi-owner machinery with a mapping-owner generation for the target T.

The narrow first candidate only needs to demonstrate the missing invariant for `MAP_FIXED`:

1. assign or recover an owner generation for the anonymous mapping containing T when H is registered;
2. before a successful `MAP_FIXED` can replace that mapping, identify dependent H claims;
3. after the host syscall succeeds, drop those old-generation claims and exact-evict/revoke H;
4. do **not** let same-address replacement implicitly reactivate H;
5. require a new explicit `LinkAddressToFunction` claim to reactivate H.

The ideal first runtime matrix is:

```text
old candidate + MAP_FIXED, no re-register    -> 222 (current bug)
owner-token candidate + no re-register       -> revoked/fault, never 222
owner-token candidate + explicit re-register -> 222
```

That separates owner-generation retirement from mere address/cache invalidation.

Destructive `mremap` and `shmdt` should follow after the `MAP_FIXED` owner transition is proven.

## Related design

See [MAPPED_RESOURCE_OWNERSHIP.md](./MAPPED_RESOURCE_OWNERSHIP.md) for the proposed non-reusable mapping-owner token and reverse dependency index.

## External-contact state

No third-party/upstream interaction. All experiments remain in repositories owned by `teamleaderleo`.