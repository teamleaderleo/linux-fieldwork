# Twelfth pass: registry-only rebind is insufficient

Status: internal Fieldwork evidence for issue #672. FEX upstream remains read-only.

Source under test: FEX `71afe476751deac24adabd1adb575fd2337b6e0a`.

Owned carrier: `teamleaderleo/FEX:ci/thunk-rebind-diagnostic-v2-20260814`.

Run: `31744084038`.

Artifact: `thunk-registry-only-rebind-31744084038`.

Artifact digest: `sha256:49509645fd453b8e9447028090b5d48cc320ff8ff6f8b33f963b7e6f3ce35ea6`.

## Result

This is the negative control for `ELEVENTH_PASS_EXACT_REBIND_RUNTIME.md`.

The fixture forces generation 2 of an unloadable guest thunk DSO to a different guest address while keeping the native host function address stable.

Generation 1:

```text
native H                        0x7ffff7d80860
guest invoker T1               0x7ffff7da21b0
pre-unload H call              rv=1023
```

After `dlclose`, T1 is unmapped. The old DSO span is reserved so generation 2 relocates:

```text
old T1                          0x7ffff7da21b0
new T2                          0x7ffff7d781b0
native H                        unchanged: 0x7ffff7d80860
```

Before re-registration, the retained H route faults while fresh generation-2 guest code works.

The registry-only variant then handles the duplicate H registration by using FEX's existing CustomIR removal operation and adding H -> T2 again. It records:

```text
DIAG_REGISTRY_ONLY_DUP H=0x7ffff7d80860 OLD=0x7ffff7da21b0 NEW=0x7ffff7d781b0
```

The next call through H still fails:

```text
child Link after re-register    signal=11
```

The current generation-2 callback remains healthy, proving the new guest generation itself is valid.

## A/B with exact eviction

Registry-only:

```text
remove old CustomIR registration
add H -> T2
call H
=> signal 11
```

Exact-eviction run `31743358148`:

```text
remove old CustomIR registration
exact erase H from shared lookup map
exact invalidate H from thread lookup cache
add H -> T2
call H
=> rv=1001035, exit 0
```

## Conclusion

This directly demonstrates two independently retained layers for thunk dynamic-PFN routing:

```text
1. CustomIRHandlers[H]
2. already-compiled/cached synthetic entry at H
```

Changing the registration alone does not repair an already-compiled H route. Exact synthetic-key cache retirement is required.

That matches the source-level cache model: thunk CustomIR is compiled without guest `CodePages` dependencies, so ordinary page/range invalidation does not reliably discover H.

A correct retirement transaction therefore needs to remove both the CustomIR registration and the compiled/cache entry keyed by H, including inbound block delinking and per-thread lookup state.

This closes the mechanism-level dynamic-PFN question on real FEX. It still does not identify the immediate caller in the original M5 `vulkaninfo` teardown; the retained core R11/stack receipt remains the shortest discriminator for that workload.

The same fixture continues to show a separate callback lifetime defect: the first-generation host->guest callback faults after relocation while a current generation-2 callback works.
