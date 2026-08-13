# Thirteenth pass: exact FEX-2608 reproduces and repairs the dynamic-PFN lifetime defect

Status: internal Fieldwork evidence for issue #672. FEX upstream remains read-only.

Exact source under test: FEX-2608 `e869aa644a16e4332cdc15c1ea0b4d13d482385d`.

Owned carrier: `teamleaderleo/FEX:ci/thunk-rebind-diagnostic-v2-20260814`.

Run: `31744672239`.

Artifact: `thunk-exact-rebind-fex2608-31744672239`.

Artifact digest: `sha256:bf2b8e088630e5b118f16d4f5c478c5494df977351e0b0175ff29871fd57d365`.

## Result

This repeats the real-FEX forced-different reload discriminator on the **exact source revision used by the original Apple-M5 Vulkan investigation**.

Generation 1:

```text
native host H                    0x7ffff7d80860
guest CallHost invoker T1       0x7ffff7da21b0
pre-unload H call               rv=1023
pre-unload callback             rv=10053
```

After final guest DSO unload, the first-generation invoker/target/unpacker are unmapped. The old DSO span is reserved with `PROT_NONE`, forcing generation 2 elsewhere:

```text
old T1                           0x7ffff7da21b0
new T2                           0x7ffff7d781b0
native H                         unchanged 0x7ffff7d80860
```

Before re-registration:

```text
child retained Link after reload  signal=11
child retained callback reload    signal=11
fresh guest direct host call      rv=1001031
fresh/current callback             rv=10010053
```

The generation-2 duplicate native address then produces:

```text
DIAG_CUSTOM_ADD H=0x7ffff7d80860 inserted=0 data=0x7ffff7d781b0
DIAG_DUP H=0x7ffff7d80860 OLD=0x7ffff7da21b0 NEW=0x7ffff7d781b0
DIAG_EXACT_SHARED H=0x7ffff7d80860 erased=1
DIAG_EXACT_LOCAL H=0x7ffff7d80860 thread=0xff9a90c01000
DIAG_CUSTOM_REMOVE H=0x7ffff7d80860 handler=1
DIAG_CUSTOM_ADD H=0x7ffff7d80860 inserted=1 data=0x7ffff7d781b0
```

After exact retirement and re-registration:

```text
child Link after re-register      rv=1001035
child Link after re-register      exit=0
```

The old first-generation callback remains independently stale while a current generation callback works:

```text
child first callback after new    signal=11
child current callback after new  rv=10010093
child current callback after new  exit=0
```

## Conclusion

The generic dynamic host-function-pointer lifetime defect and its exact-cache repair are not merely current-main behavior. They reproduce on FEX-2608, the exact source revision used in the original M5 `vulkaninfo` teardown investigation.

Combined with the registry-only negative control:

- keeping the first H -> T1 mapping across a moved guest generation faults;
- stock CustomIR removal/re-add without exact synthetic-key cache eviction still faults;
- exact shared L3 + per-thread L1/L2 eviction of H, followed by H -> T2 registration, succeeds;
- the callback trampoline lifetime defect remains separate.

This closes the revision-compatibility question for the reduced mechanism.

It still does not substitute for the one missing original-workload receipt: the immediate caller into the retired Vulkan `CallHostFunction` target in the M5 core. Guest R11 and the guest return stack remain the shortest way to identify whether that particular terminal transfer used the dynamic-PFN bridge.
