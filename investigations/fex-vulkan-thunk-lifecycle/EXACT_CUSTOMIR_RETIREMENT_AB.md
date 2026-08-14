# Exact CustomIR retirement A/B — hosted ARM64

Date: 2026-08-14

## Result

A same-run hosted ARM64 A/B test now gives direct causal evidence for the LinkAddress/CustomIR lifetime hypothesis.

The baseline and patched runs use the same retained x86-64 guest fixture, the same Ubuntu 24.04 amd64 rootfs construction, the same hosted ARM64 job, and the same stable synthetic native address:

```text
H = 0x0000700000010000
```

The fixture deliberately forces the guest DSO to reload at a different guest address while keeping `H` stable. Its intended discriminator is documented in [`synthetic-reproducer/README.md`](./synthetic-reproducer/README.md): current FEX keeps the first `H -> T1` CustomIR registration because `AddCustomIREntrypoint()` uses `emplace`; a valid cleanup policy must retire generation 1 so the same stable native pointer can bind generation 2 cleanly.

### Baseline

Observed on the unmodified product build in the A/B job:

```text
stable native identity          0x0000700000010000
stable native identity map      0x0000700000010000 -> unmapped
proof: old guest invoker executable mappings disappeared
reserved old DSO span           0x7ffff7da1000 len=0x5000 PROT_NONE
reload invoker A                old=0x00007ffff7da2150 new=0x00007ffff7d9d150 DIFFERENT
child linked entry after reload signal=11 (Segmentation fault)
fresh direct guest invoker      rv=100100071 want=100100071
```

This reproduces the retained-generation failure in real FEX. The stable synthetic entry survives while its generation-1 guest invoker is gone; a direct call to the fresh generation-2 invoker remains healthy.

### Exact-retirement v2

The same checkout was then modified in-place by the internal exact-retirement v2 diagnostic and rebuilt incrementally. The patch:

1. retires thunk-owned CustomIR registrations whose captured `Data` target lies inside the successfully unmapped guest range;
2. collects their synthetic/native-PFN keys `H`;
3. erases each `H` directly from the shared `GuestToHostMap` rather than relying on `CodePages` range indexing;
4. invalidates each `H` directly from every thread's L1/L2 lookup cache;
5. flushes the call/return prediction stack for the exact-entry diagnostic;
6. performs this lifecycle retirement independently of the ordinary SMC range-invalidation policy.

Observed after the patched rebuild:

```text
stable native identity          0x0000700000010000
stable native identity map      0x0000700000010000 -> unmapped
proof: old guest invoker executable mappings disappeared
reserved old DSO span           0x7ffff7da1000 len=0x5000 PROT_NONE
reload invoker A                old=0x00007ffff7da2150 new=0x00007ffff7d9d150 DIFFERENT
old invoker after reload        0x00007ffff7da2150 -> 00007ffff7da1000-00007ffff7da6000 ---p
new invoker after reload        0x00007ffff7d9d150 -> 00007ffff7d9d000-00007ffff7d9e000 r-xp .../libguest_link_lifetime.so
child linked entry after reload rv=100100071
child linked entry after reload exit=0
fresh direct guest invoker      rv=100100071 want=100100071
```

The same stable `H` therefore reaches generation 2 successfully after exact retirement while the entire old DSO span is still `PROT_NONE`. This is the useful A/B split: baseline routes the retained key into dead generation-1 state and faults; exact retirement permits clean generation-2 ownership and returns the generation-2 value.

## Actions provenance

Owned-fork branch:

```text
teamleaderleo/FEX: diagnostic/thunk-range-retirement-2608
```

Authoritative repaired A/B carrier commit:

```text
384bf4a52a465802afa2b6403ea157e4385ade9b
```

Hosted run:

- `teamleaderleo/FEX` Actions run `31775159912`
- workflow: `Exact CustomIR retirement A/B`
- runner: `ubuntu-24.04-arm`
- conclusion: success
- uploaded artifact: `exact-customir-retirement-ab-31775159912`
- artifact SHA-256: `2ff99414a090de96535b15e051272a6ac1947faaf67021e5ed4a863be5a9a916`

The job uploaded baseline stdout/stderr, patched stdout/stderr, both exit receipts, the exact generated source diff, configure/build logs, rootfs receipt, identity receipt, and the summary.

## Compile repair found by the experiment

The first A/B run reached the baseline reproduction but failed while rebuilding v2. That failure was a diagnostic implementation bug rather than a FEX product result:

```text
Core.cpp: error: no member named 'InvalidateSharedEntry' in 'FEXCore::GuestToHostMap'
```

`CodeBuffer::LookupCache` is a `GuestToHostMap*`. The first v2 applicator had accidentally placed `InvalidateSharedEntry()` on the per-thread `LookupCache` class. The repaired diagnostic performs shared/L3 removal directly:

```cpp
auto SharedLock = Strong->LookupCache->AcquireWriteLock();
Strong->LookupCache->Erase(Address, SharedLock);
```

Per-thread exact L1/L2 invalidation remains on `LookupCache`.

The repair helper is retained in the owned FEX fork as:

```text
diagnostics/thunk-range-retirement-2608/repair_exact_customir_retirement_v2_compile.py
```

The successful run proves the repaired source compiles and executes on hosted ARM64.

## Why exact eviction is required

This experiment also tightens the implementation requirement beyond the earlier range-cleanup sketch.

CustomIR blocks intentionally skip ordinary guest-code-page ownership tracking. Their compiled mappings can therefore have no `CodePages` reverse-index entries tying synthetic `H` to guest target `T`. Ordinary `InvalidateGuestCodeRange(H, 1)` / range invalidation cannot be relied on to find and evict a pretranslated CustomIR entry.

Retirement must remove both layers:

```text
CustomIRHandlers[H]                    registry ownership
GuestToHostMap / per-thread caches H   translated ownership
```

Removing only the registry can leave translated stale code alive. Removing only translated state lets the surviving registry regenerate stale code. Exact `H` retirement handles both.

## Interpretation

The A/B result moves the lifetime issue from source-level suspicion plus model proof to a real-FEX causal repair experiment:

```text
baseline current behavior
    unload T1
    H ownership survives
    reload T2 at a different address
    H call -> stale generation -> SIGSEGV

exact retirement diagnostic
    unload T1
    retire H -> T1 registry state
    evict translated/cache state for H exactly
    reload T2 at a different address
    fresh H ownership is accepted
    H call -> generation 2 value
```

The old executable mapping is explicitly absent in both variants, and the patched successful call occurs while the old DSO span is protected `PROT_NONE`. The result therefore does not depend on same-address ABA reuse.

## Remaining engineering work

The v2 diagnostic establishes causality but is still research code. Production design still needs deliberate treatment of:

- peer-thread quiescence when another thread may already be executing or have selected translated code for `H`;
- ordering around the actual kernel `munmap()` versus retirement, to avoid a post-unmap race window;
- efficient reverse ownership bookkeeping if an O(CustomIR entries) scan per guest unmap is considered too expensive;
- other guest mapping-destruction paths such as replacement mappings / `mremap` / shared-memory detach as applicable;
- the separate host-to-guest `GuestcallToHostTrampoline` lifetime surface;
- an in-tree regression that pretranslates `H`, unloads the owner DSO, reloads at a forced-different address, and verifies generation-2 rebinding.

The next Vulkan integration test should use the same ownership cleanup semantics and retain the existing llvmpipe / pin / bogus-preload controls.

## External-contact state

No third-party/upstream issue, pull request, comment, reaction, review, branch write, or other upstream interaction was performed by this experiment. All writes and Actions execution were confined to repositories owned by `teamleaderleo`.
