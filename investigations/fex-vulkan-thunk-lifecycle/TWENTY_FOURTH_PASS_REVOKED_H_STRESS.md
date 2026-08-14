# Twenty-fourth pass — revoked-H five-cycle alias stress

## Scope

This checkpoint stress-tests the current revoked-H integrated candidate across repeated unload/reload cycles while also exercising the historical same-native-H alias case.

Source under test: FEX `71afe476751deac24adabd1adb575fd2337b6e0a`.
Owned-FEX branch: `ci/thunk-revoked-h-20260814`.
Carrier commit: `f58b55b84da536e0aeb229c0f886afb7f5b9ecad`.
Workflow run: `31771500868`.
Artifact: `9208357842`, `thunk-revoked-h-stress-31771500868`.

The retained full-thunk fixture runs:

```text
--force-different --alias --cycles 5
```

Each generation registers two same-signature guest wrappers resolving to the same native host H, forcing one active claim plus a standby alias claim. Each generation is then unloaded and the next generation is forced to a different guest VA.

## Result

`run.exit = 0`.

All five generations completed and all five alias calls returned the active-wrapper result expected by the fixture:

```text
=== generation 1 ===
alias call rv=1023 A=1023 B=1024
reload invoker old=0x00007ffff7da21b0 new=0x00007ffff7d781b0 DIFFERENT

=== generation 2 ===
alias call rv=2023 A=2023 B=2024
reload invoker old=0x00007ffff7da21b0 new=0x00007ffff7d781b0 DIFFERENT

=== generation 3 ===
alias call rv=3023 A=3023 B=3024
reload invoker old=0x00007ffff7da21b0 new=0x00007ffff7d781b0 DIFFERENT

=== generation 4 ===
alias call rv=4023 A=4023 B=4024
reload invoker old=0x00007ffff7da21b0 new=0x00007ffff7d781b0 DIFFERENT

=== generation 5 ===
alias call rv=5023 A=5023 B=5024
reload invoker old=0x00007ffff7da21b0 new=0x00007ffff7d781b0 DIFFERENT
```

The runtime repeatedly exercised the full state cycle:

```text
DIAG_REVOKED_H_ACTIVATE
DIAG_MULTI_ACTIVE
DIAG_MULTI_STANDBY
DIAG_MULTI_DROP active claim
DIAG_MULTI_DROP standby alias claim
DIAG_MULTI_RETIRE ... NEW=0
DIAG_REVOKED_H_INSTALL
DIAG_REVOKED_H_COMPILE
DIAG_REVOKED_H_ACTIVATE next generation
```

Both active and standby claims from each outgoing DSO were removed before the next generation became active. No stale standby claim accumulated across cycles.

## Conclusion

The current research state machine is stable across repeated moved-generation transitions and the same-native-H alias pattern for at least five cycles in the reduced real-FEX fixture.

This adds durability evidence to the one-cycle proofs. It does not expand the generic promotion claim: the alias wrappers deliberately share the same function ABI, and production compatibility identity is still required before promoting arbitrary same-H claims across libraries.

No upstream FEX interaction was performed.