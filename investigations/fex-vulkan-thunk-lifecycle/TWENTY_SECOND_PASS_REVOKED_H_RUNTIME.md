# Twenty-second pass — revoked synthetic-H runtime proof

## Scope

This checkpoint extends the lock-clean integrated lifetime candidate with an explicit synthetic-H state machine:

```text
ACTIVE(H -> T)
  -> REVOKED(H)
  -> ACTIVE(H -> T2)
```

The goal is to prevent a stale guest function pointer containing native host address `H` from falling through to ordinary x86 frontend decoding after its final guest-thunk owner retires.

Source under test: FEX `71afe476751deac24adabd1adb575fd2337b6e0a`.

Owned-FEX branch: `ci/thunk-revoked-h-20260814`.
Carrier commit: `eb6714ce37e82d5562c0c8b0826b4df726fdc906`.
Workflow run: `31771144316`.
Artifact: `9208238549`, `thunk-revoked-h-31771144316`.

## State transitions

Activation is now thread-aware and uses the same global exact-invalidation transaction as retirement. It removes any prior active/revoked definition, exact-erases compiled H state from shared and every live thread cache, and then installs the current H -> T CustomIR definition.

Final owner retirement performs the inverse transition: remove the active definition, exact-erase all compiled H state, then install a revoked CustomIR definition for H before releasing the global retirement transaction.

The revoked CustomIR handler logs at IR-generation time and exits toward guest address zero. Its purpose is diagnostic but its semantic property is the important one: `H` remains a synthetic FEX-controlled entrypoint after its owner disappears.

## Result matrix

The existing integrated regression matrix remains green:

```text
force.exit=0
aba.exit=0
thread.exit=0
multi.exit=0
```

## Forced-different stale-H discriminator

Generation 1 activation:

```text
DIAG_LOCKED_DEFINITION H=0x7ffff7d80860 handler=0
DIAG_REVOKED_H_ACTIVATE H=0x7ffff7d80860 T=0x7ffff7da21b0 ...
DIAG_MULTI_ACTIVE H=0x7ffff7d80860 T=0x7ffff7da21b0
```

When generation 1 retires:

```text
DIAG_MULTI_RETIRE H=0x7ffff7d80860 OLD=0x7ffff7da21b0 NEW=0
DIAG_LOCKED_DEFINITION H=0x7ffff7d80860 handler=1
DIAG_REVOKED_H_INSTALL H=0x7ffff7d80860
DIAG_LOCKED_RETIRE H=0x7ffff7d80860 ...
```

Before generation 2 registers H again, the fixture deliberately calls the stale H pointer in a child. The runtime trace proves the revoked synthetic handler is selected and compiled:

```text
DIAG_REVOKED_H_COMPILE H=0x7ffff7d80860
child retained Link after reload  signal=11 (Segmentation fault)
```

This is the decisive discriminator. The stale call still fails, as it should, but it fails after FEX recognizes H through the revoked CustomIR definition. It is not ordinary frontend decoding of the native host address.

Generation 2 activation then replaces the revoked definition transactionally:

```text
DIAG_LOCKED_DEFINITION H=0x7ffff7d80860 handler=1
DIAG_REVOKED_H_ACTIVATE H=0x7ffff7d80860 T=0x7ffff7d781b0 ...
DIAG_MULTI_ACTIVE H=0x7ffff7d80860 T=0x7ffff7d781b0
```

The reactivated H path works:

```text
child Link after re-register      rv=1001035
child Link after re-register      exit=0
```

The independent callback direction remains correct:

```text
child retained callback reload    exit=113
child current callback after new  rv=10010093
child current callback after new  exit=0
```

## Multi-owner promotion

The same state machine remains compatible with alternate live claims.

A is active and B standby. On A retirement, H first passes through the revoked state, then the compatible B claim is activated using the exact transition:

```text
DIAG_MULTI_RETIRE H=0x7ffff7d80860 OLD=0x7ffff7da21b0 NEW=0x7ffff7d7c1b0
DIAG_REVOKED_H_INSTALL H=0x7ffff7d80860
DIAG_REVOKED_H_ACTIVATE H=0x7ffff7d80860 T=0x7ffff7d7c1b0 ...
DIAG_MULTI_PROMOTE H=0x7ffff7d80860 T=0x7ffff7d7c1b0
multi-owner promoted B          rv=2001035 want=2001035
```

When B later becomes the final retiring owner, H returns to REVOKED.

## Conclusion

A deterministic revoked synthetic-H state is mechanically viable on top of the already-proven exact all-thread retirement model.

This closes the previous semantic gap where complete erasure of H could expose native host bytes to ordinary guest x86 decoding.

The research direction is now stronger than simple deletion:

```text
active owner retires
  -> exact invalidate every compiled H copy
  -> H remains synthetic/revoked
  -> stale call gets controlled guest fault path
  -> later compatible owner can reactivate H transactionally
```

## Product refinement

The diagnostic revoked handler exits toward guest address zero, producing guest SIGSEGV. A final implementation should choose an explicit documented revoked-pointer fault policy rather than relying on address zero as the mechanism.

The important invariant is not the exact signal encoding; it is that a revoked H never becomes ordinary guest code and never reaches retired guest T.

A production API should expose activation/retirement as thread-aware state transitions rather than independent Add/Remove calls, because revoked handlers themselves can be compiled and cached and therefore require exact invalidation on reactivation.

## Evidence boundary

- Current reviewed FEX source is tested here; exact FEX-2608 revoked-H repeat is the next revision check.
- The stale H call runs in a forked child, so this proves synthetic revoked selection and fault behavior but not a parent-process tombstone cache surviving into reactivation. Reactivation uses the already-proven exact all-thread invalidation transaction.
- Multi-owner promotion remains safe here only because fixture claims deliberately share a function signature.
- This does not resolve in-flight execution that selected the old active block before retirement began.

No upstream FEX interaction was performed.