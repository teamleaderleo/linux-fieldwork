# Sixteenth pass: callback tombstone survives same-address guest-generation reuse

Status: internal Fieldwork evidence for issue #672. FEX upstream remains read-only.

Source under test: FEX `71afe476751deac24adabd1adb575fd2337b6e0a`.

Owned carrier: `teamleaderleo/FEX:ci/callback-tombstone-diagnostic-20260814`.

Run: `31745628556`.

Artifact: `thunk-callback-tombstone-aba-31745628556`.

Artifact digest: `sha256:0ae00597edafa911218c2e4b1a1304bcf0ba7cb703bf4a6394a7f18236e4070c`.

## Question

The callback tombstone experiment from the fifteenth pass erases the old cache key `{GuestUnpacker, GuestTarget}` after revoking an escaped host trampoline.

Is that key erasure actually necessary when a later guest DSO generation is loaded at the **same guest virtual addresses**?

Without key erasure, same-address reuse creates an ABA hazard: the new generation can present the same `{GuestUnpacker, GuestTarget}` pair, causing `MakeHostTrampolineForGuestFunction()` to find and return the old tombstoned trampoline instead of allocating a live trampoline for the new generation.

## Runtime receipt

Generation 1:

```text
guest CallHost invoker A         0x7ffff7da21b0
GuestTarget                      0x7ffff7da2170
GuestUnpacker                    0x7ffff7da2190
pre-unload callback              rv=10053 want=10053
```

Before final unmap, FEX tombstones the first host trampoline:

```text
DIAG_CALLBACK_TOMBSTONE trampoline=0x7ffff7d7c000 \
  unpacker=0x7ffff7da2190 target=0x7ffff7da2170 \
  range=0x7ffff7da1000+0x5000
```

Generation 1 guest addresses then disappear.

Unlike the forced-different test, this run does **not** reserve the old mapping. The loader reuses exactly the same guest addresses for generation 2:

```text
reload invoker                  old=0x7ffff7da21b0 new=0x7ffff7da21b0 SAME
native host stable              old=0x7ffff7d80860 new=0x7ffff7d80860
```

The old escaped host callback remains revoked even though the guest address pair is live again:

```text
DIAG_CALLBACK_REVOKED invoked
child retained callback reload  exit=113
```

Generation 2 creates a current callback using the same guest target/unpacker addresses and it works:

```text
fresh/current callback          rv=10010053 want=10010053
child current callback after new rv=10010093
child current callback after new exit=0
```

The original first-generation callback remains revoked after the current callback exists:

```text
DIAG_CALLBACK_REVOKED invoked
child first callback after new  exit=113
```

At the second generation's own unload, FEX tombstones a **different host trampoline allocation**:

```text
DIAG_CALLBACK_TOMBSTONE trampoline=0x7ffff7d7c030 \
  unpacker=0x7ffff7da2190 target=0x7ffff7da2170 \
  range=0x7ffff7da1000+0x5000
```

The first generation used host trampoline:

```text
0x7ffff7d7c000
```

The second generation, despite identical guest target/unpacker values, used:

```text
0x7ffff7d7c030
```

That proves cache-key erasure prevented the same-address generation from retrieving the old tombstoned trampoline.

## Dynamic-PFN control

This run also demonstrates why same-address reload can hide the separate dynamic-PFN lifetime defect.

Because T2 equals T1 by address, the retained old H route happens to execute valid generation-2 guest code:

```text
child retained Link after reload rv=1001032
child retained Link after reload exit=0
```

This does **not** establish correct dynamic-PFN ownership. The forced-different runs prove that the same retained H route faults as soon as the new guest generation moves.

Therefore a regression suite must include forced-different-address reload; same-address reload alone is an insufficient negative control for dynamic PFNs.

## Conclusion

The callback-side ABA prediction is confirmed.

A correct callback revocation design must distinguish guest **generation identity** from raw guest address identity.

For the current FEX cache, one mechanically valid rule is:

```text
on owner generation retirement:
  tombstone the existing escaped host trampoline in place
  erase its {GuestUnpacker, GuestTarget} cache key

on a future generation:
  even if the same guest addresses reappear,
  allocate a fresh host trampoline / binding for that generation
```

The escaped first-generation host pointer stays deterministically revoked; it is not resurrected merely because the same virtual addresses become executable again.

This is strong runtime evidence for explicit load-generation ownership or an equivalent stable binding identity on callback trampolines.

## Product implication

Raw address pairs are not sufficient cache identity across unload/reload.

A production callback binding should have a stable FEX-owned identity/state separate from guest VAs, for example:

```text
ACTIVE(generation N, unpacker, target)
  -> REVOKING
  -> REVOKED
```

A newly loaded generation receives a new binding even if its guest VAs equal those of generation N.

The production revocation action does not have to be process exit `113`; that was only the diagnostic marker. The important invariant is that the old escaped host pointer cannot enter guest code belonging to a later generation solely because addresses were reused.
