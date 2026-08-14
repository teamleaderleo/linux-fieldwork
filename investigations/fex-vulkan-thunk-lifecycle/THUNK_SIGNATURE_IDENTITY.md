# Existing thunk signature identity for same-H owner claims

## Why this note exists

The multi-owner runtime proof shows that FEX benefits from retaining more than one live claim for a native host function pointer `H`, but automatic promotion must not treat arbitrary guest wrapper addresses as ABI-compatible.

The guest registration path currently sends only:

```text
native H
guest wrapper T
```

A full claim registry needs a third identity describing the call contract.

## FEX already generates that identity

Current `ThunkLibs/include/common/Guest.h` already ties `CallHostFunction` to the generated callback thunk for the exact C++ function signature.

Conceptually:

```text
Result(Args...)
  -> fexthunks_invoke_callback<Result(Args...)>
  -> generated MAKE_CALLBACK_THUNK marker
  -> SHA-256 thunk identity
```

`GetCallerForHostFunction(Result (*)(Args...))` returns:

```text
&CallHostFunction<
    fexthunks_invoke_callback<Result(Args...)>,
    Result,
    Args...>
```

So the guest wrapper `T` is already instantiated from a signature-specific thunk identity, and the generated callback thunk marker carries the existing SHA-256 value FEX uses for thunk lookup.

## Preferred ownership extension

A future `LinkAddressToFunction` ownership API should reuse that generated thunk/signature identity rather than inventing an unrelated compatibility scheme.

A claim can conceptually become:

```text
H
T
SignatureThunkHash
Owner
State = active | standby | retired
```

Then active-owner retirement may promote a standby claim only when its signature identity matches the active call contract.

The exact transport can be chosen later. Options include passing the stable hash directly or passing enough live guest thunk metadata for FEX to resolve the existing marker while the owner is still mapped.

## What this avoids

Do not use any of these as generic compatibility identity:

```text
native H equality
numeric guest T equality
same DSO filename
same symbol spelling
first remaining claim
last registered claim
```

The same native implementation can be exposed through multiple API names, libraries, or wrappers, while guest wrapper addresses can differ by load generation.

## Scope

This is a source-level design refinement informed by the already-executed same-H promotion fixture. The fixture's two live claims intentionally use the same signature, so it proves that compatible standby promotion works but does not test mismatched-signature rejection.

No upstream FEX interaction was performed.