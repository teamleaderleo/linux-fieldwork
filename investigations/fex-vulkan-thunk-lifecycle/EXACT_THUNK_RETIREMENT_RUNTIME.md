# Exact thunk retirement runtime proof

## Scope

This checkpoint refines the broad pre-unmap retirement result from run `31744407289`. The question is whether a single-thread H→T lifetime can recover after a moved reload using an exact entrypoint eviction instead of `ClearCodeCache`.

## Diagnostic

Owned-FEX branch `ci/agent-g-arm64-20260814`, commit `f909ea98415d9ff3668b06526440ca1ca7e67bef`.

Hosted ARM64 run `31745095185`, job `94597627028`, artifact `9198765803`.

The diagnostic keeps the pre-unmap `(H,T)` owner index, then retires matching H before physical `munmap` by:

1. erasing the CustomIR handler for H;
2. clearing H from the current thread's L1/L2 lookup cache;
3. erasing H from the shared L3 `GuestToHostMap`.

No broad code-cache flush is used.

## Trace

```text
DIAG_EXACT_OWNER H=0x7ffff7d80860 T=0x7ffff7da21b0
DIAG_EXACT_MATCH H=0x7ffff7d80860 T=0x7ffff7da21b0 range=0x7ffff7da1000+0x5000
DIAG_EXACT_RETIRE H=0x7ffff7d80860 thread=0xffd2d0c01000 shared=1
DIAG_EXACT_OWNER H=0x7ffff7d80860 T=0x7ffff7d781b0
```

The first retirement reports `shared=1`, proving the compiled shared H entry existed and was removed. The current thread's hot-cache entry is cleared in the same exact operation.

## Runtime result

After generation 1 is unloaded and the guest thunk is forced to reload at another VA while native H remains stable:

```text
child retained Link after reload  signal=11 (Segmentation fault)
child retained callback reload    signal=11 (Segmentation fault)
fresh guest direct host call      rv=1001031 want=1001031
fresh/current callback            rv=10010053 want=10010053
child Link after re-register      rv=1001035
child Link after re-register      exit=0
child first callback after new    signal=11 (Segmentation fault)
child current callback after new  rv=10010093
child current callback after new  exit=0
```

This reproduces the broad-retirement recovery with exact H eviction only. In the retained single-thread fixture, handler removal plus exact current-thread L1/L2 eviction plus shared L3 erasure is sufficient for generation 2 to bind the same stable H to its new guest target.

## Product implication

The next product-level primitive should generalize this exact operation across every emulation thread under the existing thread/code-invalidation locking discipline. It should retire the CustomIR definition, shared compiled H/direct links, and H from every thread's L1/L2 before the outgoing guest load generation disappears.

This result does not address the selected-bridge versus unload race. A final design still needs execution lifetime/quiescence so a thread that already selected H→T cannot cross into an unmapped T after retirement begins.

The host→guest callback path remains independently stale and serves as an orthogonal control in this run.

All edits are diagnostic work on owned surfaces. No upstream interaction occurred.
