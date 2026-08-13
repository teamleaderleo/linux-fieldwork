# Fourteenth pass: owner-range retirement before guest unmap restores legal re-registration

Status: internal Fieldwork evidence for issue #672. FEX upstream remains read-only.

Owned FEX carrier/source commit: `62be54f1a13f94ba098971503f5a3058ea9b3a42` on `ci/agent-e-arm64-20260814`.

Run: `31744407289`.

Artifact: `agent-e-preunmap-retire-31744407289`.

Artifact digest: `sha256:1074750a37456de9f07237acb2326e38592b6e9baa737835b50b7944ee05cd43`.

## Diagnostic design

This variant adds explicit reverse ownership for dynamic thunk links:

```text
native host entry H -> guest target T
```

When `GuestMunmap` is about to retire a guest range, the thunk handler finds every H whose owned T falls inside that range and retires H before the backing guest code disappears.

For this broad diagnostic, retirement performs:

```text
RemoveCustomIREntrypoint(H)
ClearCodeCache(current_thread, false)
```

The full cache clear is intentionally coarse. The exact-cache experiments in the eleventh through thirteenth passes show how to make H eviction precise.

## Runtime receipt

Generation 1:

```text
native H                          0x7ffff7d80860
guest invoker T1                 0x7ffff7da21b0
pre-unload H call                rv=1023 want=1023
pre-unload callback              rv=10053 want=10053
```

Before the first guest DSO is physically retired, the diagnostic records:

```text
DIAG_LINK_OWNER H=0x7ffff7d80860 T=0x7ffff7da21b0
DIAG_PREUNMAP_MATCH H=0x7ffff7d80860 T=0x7ffff7da21b0 range=0x7ffff7da1000+0x5000
DIAG_RETIRE_H H=0x7ffff7d80860 thread=0xff81f0c01000
```

After unload, T1 and the callback target/unpacker are unmapped. The old span is reserved, forcing generation 2 to another address:

```text
reload invoker                    old=0x7ffff7da21b0 new=0x7ffff7d781b0 DIFFERENT
native host stable                old=0x7ffff7d80860 new=0x7ffff7d80860
```

The old application-visible H is no longer a legal live thunk pointer after its owner has been completely unloaded, and using that retained old value fails:

```text
child retained Link after reload  signal=11
```

That is acceptable lifetime behavior for the old pointer. The important correctness discriminator is the fresh generation.

Generation 2 registers the same native H with its current guest target T2:

```text
DIAG_LINK_OWNER H=0x7ffff7d80860 T=0x7ffff7d781b0
```

The new registration works:

```text
fresh guest direct host call      rv=1001031 want=1001031
child Link after re-register      rv=1001035
child Link after re-register      exit=0
```

The second generation is later retired at its own unmap boundary as well:

```text
DIAG_PREUNMAP_MATCH H=0x7ffff7d80860 T=0x7ffff7d781b0 range=0x7ffff7d77000+0x5000
DIAG_RETIRE_H H=0x7ffff7d80860 thread=0xff81f0c01000
```

The host-to-guest callback remains a separate lifetime problem:

```text
child retained callback reload    signal=11
child first callback after new    signal=11
child current callback after new  rv=10010093
child current callback after new  exit=0
```

## What this establishes

This is positive runtime evidence for an **unload-owner retirement model**, not only a duplicate-registration repair model.

A viable dynamic-PFN lifecycle is:

```text
register H -> T with guest-generation ownership
before T's owning mapping disappears:
    retire H registration
    retire compiled/cache H state
unmap guest generation
old H is no longer valid
later generation registers stable H -> T2
fresh H call works
```

This matches ordinary dynamic-library semantics better than silently keeping the old H usable after its owner is gone.

The broad current-thread cache clear is not the preferred final implementation. The exact-rebind experiments already prove that the narrower required primitive is exact synthetic-key eviction from shared and per-thread lookup caches, with inbound delinking.

## Combined design implication

The dynamic-PFN evidence now supports both sides of the lifecycle:

1. **final unload:** owner-range retirement can revoke H before guest code disappears;
2. **future reload:** exact H cache/registration cleanup permits the same stable native H to bind safely to T2.

The remaining design work is mostly genericity and concurrency:

- load-generation identity rather than raw address ownership alone;
- all-thread exact H invalidation;
- quiescence for a thread already executing an H bridge;
- compatibility/alias policy when several guest owners claim one H;
- independent host-to-guest callback revocation semantics.

This result does not identify the immediate caller in the original M5 `vulkaninfo` teardown. That exact workload still needs the retained core R11/stack receipt to prove which surviving route selected the dead Vulkan `CallHostFunction` address.
