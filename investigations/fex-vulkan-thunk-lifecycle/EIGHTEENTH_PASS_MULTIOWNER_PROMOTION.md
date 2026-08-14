# Eighteenth pass — same-H multi-owner promotion runtime proof

## Scope

This checkpoint tests a compatibility case called out by FEX's historical function-pointer design: more than one live guest thunk owner can claim the same native host function pointer `H` while using distinct guest wrapper addresses.

The narrow question is whether retaining alternate claims is useful at runtime, or whether a one-slot `H -> T` owner record is sufficient.

The fixture deliberately makes both guest wrappers have the same known function signature. This proves promotion mechanics only. It does not authorize generic promotion of arbitrary same-H targets without a signature/ABI identity.

Source under test: FEX `71afe476751deac24adabd1adb575fd2337b6e0a`.

Owned-FEX carrier branch: `ci/thunk-multiowner-promotion-20260814`.

Carrier head: `d80a32e56e8fb51c493e713670a5c804458b4ee0`.

Workflow run: `31769613134`.

## Fixture

The retained full-thunk pair builds two separate unloadable guest DSOs from the same source:

```text
liblifetime-guest-a.so
liblifetime-guest-b.so
```

They are loaded simultaneously and assigned distinct per-DSO generations. Both publish the same native host function address `H`, but their guest `CallHostFunction`-style invokers live at different guest VAs.

Observed identities:

```text
native host A                   0x00007ffff7d80860
native host B                   0x00007ffff7d80860 (SAME)
multi-owner A invoker           0x00007ffff7da21b0
multi-owner B invoker           0x00007ffff7d7c1b0
```

A registers first and is expected to remain the active claim while B is live as an alternate.

## Single-slot negative control

Mode: `single`.

Artifact: `9207685618`, `thunk-multiowner-single-31769613134`.

The exact pre-unmap retirement diagnostic is unchanged from the earlier one-slot H-to-T owner map.

Both registrations occur:

```text
DIAG_MT_OWNER H=0x7ffff7d80860 T=0x7ffff7da21b0
DIAG_MT_OWNER H=0x7ffff7d80860 T=0x7ffff7d7c1b0
```

The one-slot owner map is overwritten by B even though the Core's first-wins CustomIR definition/compiled dispatch still points at A. When A later unloads, the bookkeeping no longer identifies A as the active dependency.

The process exits:

```text
run.exit = 139
```

This demonstrates that a single current owner slot is not sufficient for simultaneous same-H claims.

## Retained-claims positive variant

Mode: `multi`.

Artifact: `9207689927`, `thunk-multiowner-multi-31769613134`.

The diagnostic maintains:

```text
H -> ordered live claims [T1, T2, ...]
H -> current active target
```

The first claim is installed in CustomIR; later compatible claims are retained as standby rather than discarded.

Registration trace:

```text
DIAG_MULTI_ACTIVE H=0x7ffff7d80860 T=0x7ffff7da21b0
DIAG_MULTI_STANDBY H=0x7ffff7d80860 T=0x7ffff7d7c1b0
```

The initial H call reaches A:

```text
multi-owner active A            rv=1023 want=1023
```

When A's executable mapping retires:

```text
DIAG_MULTI_DROP H=0x7ffff7d80860 T=0x7ffff7da21b0 range=0x7ffff7da1000+0x5000
DIAG_MULTI_RETIRE H=0x7ffff7d80860 OLD=0x7ffff7da21b0 NEW=0x7ffff7d7c1b0
DIAG_MT_SHARED H=0x7ffff7d80860 erased=1
DIAG_MT_THREAD H=0x7ffff7d80860 thread=0xff6170c01000
DIAG_MT_REMOVE_ALL H=0x7ffff7d80860 handler=1
DIAG_MT_RETIRE_ALL H=0x7ffff7d80860 thread=0xff6170c01000
DIAG_MULTI_PROMOTE H=0x7ffff7d80860 T=0x7ffff7d7c1b0
```

A is confirmed unmapped while B remains executable:

```text
multi-owner old A after close      0x00007ffff7da21b0 -> unmapped
multi-owner live B                 0x00007ffff7d7c1b0 -> ... r-xp .../liblifetime-guest-b.so
```

The next call through the unchanged native `H` reaches B without B re-registering:

```text
multi-owner promoted B          rv=2001035 want=2001035
```

`run.exit = 0`.

When B later retires, the registry removes its final claim and exact-retires H with no replacement.

## Conclusion

Retaining alternate live claims is mechanically useful and fixes a real class of first-wins lifetime loss.

A full owner model cannot be represented as only:

```text
H -> one T
```

when multiple live guest owners are allowed to publish the same native H.

A more complete state is conceptually:

```text
H
  active claim -> {owner A, T1, ABI identity}
  standby      -> {owner B, T2, ABI identity}
  ...
```

On active-owner retirement, FEX can exact-retire the old compiled H state and promote a compatible live claim.

## Signature/ABI requirement

This fixture intentionally uses two wrappers with the same function signature. Therefore promotion is known-safe by construction.

The existing `fex:link_address_to_function` registration only carries:

```text
native H
guest T
```

Those numeric addresses are not sufficient to prove two claims are ABI-compatible.

The generic implementation should not implement `first remaining T wins` or `last T wins` without additional identity.

A production claim should carry a stable function-signature / callback-thunk ABI token, or another equivalently strong compatibility identity, so promotion is limited to claims that marshal the same call contract.

This can be staged separately from the minimal unload safety repair: exact pre-unmap retirement can ship without automatic alternate-owner promotion, while the claim registry/signature API can extend behavior later.

## Evidence boundary

- Both guest owners are alive simultaneously.
- Their native H is identical.
- Their guest T addresses are distinct.
- Their function signatures are intentionally identical.
- The positive variant uses the already-proven exact retirement mechanism before promoting B.
- This does not test arbitrary cross-library signature collisions, 32-bit guest ABI identity, or promotion while another H execution is in flight.

No upstream FEX interaction was performed. All code and CI work remained on owned repositories.