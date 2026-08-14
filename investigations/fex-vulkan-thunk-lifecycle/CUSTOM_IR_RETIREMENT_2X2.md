# Real-FEX CustomIR retirement 2×2

Date: 2026-08-14

## Result

A hosted ARM64 four-way ablation confirms that **both** retained ownership layers must be retired for a stable synthetic/native LinkAddress key to bind a new guest-DSO generation cleanly.

All four jobs used the same FEX fork commit, retained x86-64 LinkAddress fixture, Ubuntu 24.04 amd64 guest rootfs recipe, forced-different DSO reload, and stable synthetic/native identity:

```text
H = 0x0000700000010000
T1 = 0x00007ffff7da2150
T2 = 0x00007ffff7d9d150
```

After generation 1 was unloaded, the old DSO span was reserved `PROT_NONE`:

```text
0x7ffff7da1000 .. 0x7ffff7da6000
```

Generation 2 therefore loaded at a different address. In every variant, direct execution of the fresh generation-2 guest invoker returned the expected value:

```text
100100071
```

The only changing variable was which FEX-owned stale layer was retired.

## Matrix

| Mode | CustomIR registry `H -> T1` | translated/cache state for `H` | linked `H` after reload |
|---|---|---|---|
| baseline | retained | retained | **SIGSEGV** |
| registry-only | retired | retained | **SIGSEGV** |
| cache-only | retained | exact-evicted | **SIGSEGV** |
| full | retired | exact-evicted | **returns generation-2 value, exit 0** |

This is the real-FEX counterpart of the earlier model result: either surviving layer is sufficient to preserve or reconstruct stale generation-1 routing. Only removing both permits clean generation-2 ownership.

## Exact observed outputs

### baseline

```text
stable native identity          0x0000700000010000
stable native identity map      0x0000700000010000 -> unmapped
proof: old guest invoker executable mappings disappeared
reserved old DSO span           0x7ffff7da1000 len=0x5000 PROT_NONE
reload invoker A                old=0x00007ffff7da2150 new=0x00007ffff7d9d150 DIFFERENT
old invoker after reload        0x00007ffff7da2150 -> 00007ffff7da1000-00007ffff7da6000 ---p
new invoker after reload        0x00007ffff7d9d150 -> ... r-xp .../libguest_link_lifetime.so
child linked entry after reload signal=11 (Segmentation fault)
fresh direct guest invoker      rv=100100071 want=100100071
```

### registry-only

The CustomIR registry entry is erased, while already translated/shared/per-thread state for `H` is deliberately left intact.

```text
stable native identity          0x0000700000010000
stable native identity map      0x0000700000010000 -> unmapped
proof: old guest invoker executable mappings disappeared
reserved old DSO span           0x7ffff7da1000 len=0x5000 PROT_NONE
reload invoker A                old=0x00007ffff7da2150 new=0x00007ffff7d9d150 DIFFERENT
old invoker after reload        0x00007ffff7da2150 -> 00007ffff7da1000-00007ffff7da6000 ---p
new invoker after reload        0x00007ffff7d9d150 -> ... r-xp .../libguest_link_lifetime.so
child linked entry after reload signal=11 (Segmentation fault)
fresh direct guest invoker      rv=100100071 want=100100071
```

This directly demonstrates that registry erasure alone is insufficient once `H` has already been translated.

### cache-only

The exact shared/L3 and per-thread cache state for `H` is evicted, while the generation-1 CustomIR registry owner `H -> T1` is deliberately retained.

```text
stable native identity          0x0000700000010000
stable native identity map      0x0000700000010000 -> unmapped
proof: old guest invoker executable mappings disappeared
reserved old DSO span           0x7ffff7da1000 len=0x5000 PROT_NONE
reload invoker A                old=0x00007ffff7da2150 new=0x00007ffff7d9d150 DIFFERENT
old invoker after reload        0x00007ffff7da2150 -> 00007ffff7da1000-00007ffff7da6000 ---p
new invoker after reload        0x00007ffff7d9d150 -> ... r-xp .../libguest_link_lifetime.so
child linked entry after reload signal=11 (Segmentation fault)
fresh direct guest invoker      rv=100100071 want=100100071
```

This directly demonstrates that exact cache eviction alone is insufficient: the retained CustomIR registry state can recreate stale generation-1 routing when the stable key is used again.

### full

The generation-1 registry owner is erased and the returned synthetic/native key is exact-evicted from shared/L3 and every thread-local lookup cache.

```text
stable native identity          0x0000700000010000
stable native identity map      0x0000700000010000 -> unmapped
proof: old guest invoker executable mappings disappeared
reserved old DSO span           0x7ffff7da1000 len=0x5000 PROT_NONE
reload invoker A                old=0x00007ffff7da2150 new=0x00007ffff7d9d150 DIFFERENT
old invoker after reload        0x00007ffff7da2150 -> 00007ffff7da1000-00007ffff7da6000 ---p
new invoker after reload        0x00007ffff7d9d150 -> ... r-xp .../libguest_link_lifetime.so
child linked entry after reload rv=100100071
child linked entry after reload exit=0
fresh direct guest invoker      rv=100100071 want=100100071
```

The stable key `H` therefore reaches generation 2 successfully while the old generation-1 mapping remains inaccessible. This rules out same-address ABA reuse as the explanation for the successful result.

## What the ablations modify

The common exact-retirement diagnostic first identifies thunk-owned `CustomIRHandlers` whose captured `Data` guest target lies inside the guest range destroyed by successful `GuestMunmap()`.

The two layers are then independently controlled:

1. **Registry layer**
   - full / registry-only: erase the generation-1 `CustomIRHandlers[H]` record;
   - cache-only: collect `H` but deliberately keep the generation-1 registry record.
2. **Translated/cache layer**
   - full / cache-only: exact-erase `H` from each shared `GuestToHostMap` under its write lock and exact-invalidate every thread's L1/L2 lookup entry;
   - registry-only: deliberately skip exact translated/cache eviction.

The shared exact eviction uses `GuestToHostMap::Erase(H)` rather than range invalidation. The source audit established that CustomIR-generated entries have no ordinary `CodePages` ownership record, so page/range invalidation cannot be trusted to discover an already compiled synthetic `H`.

## Proven invariant

For this real-FEX LinkAddress path, successful guest-code retirement requires the following pair to be retired as one lifecycle operation:

```text
CustomIRHandlers[H]                // can generate H -> T
translated/cache entry for H       // can execute already-generated H -> T
```

The experiment falsifies both one-sided cleanup designs:

```text
registry-only  => stale pretranslated H survives
cache-only     => stale registry can regenerate H -> T1
```

and supports:

```text
registry retirement + exact H eviction => fresh generation-2 rebinding
```

## Actions provenance

Owned fork:

```text
teamleaderleo/FEX
branch: diagnostic/thunk-range-retirement-2608
carrier: 17c6429f9f1058e236358509c486581e221afb4d
```

Hosted Actions run:

```text
31775684761
workflow: CustomIR retirement ownership ablation
runner family: ubuntu-24.04-arm
```

All four matrix jobs completed successfully as harnesses.

Artifacts:

```text
baseline
  id:      9209840007
  sha256:  c14496a0dd2c836e2e33f2a7e96dc1cdcaa64cec1f8b7eea109fbdcc84705007

registry-only
  id:      9209848211
  sha256:  9d6fb916482ec90c6e7e1793ecc5fcf59d54b20f595eb5aa52fe8c8bb543ab5c

cache-only
  id:      9209846410
  sha256:  3d1de0b75ae97902486845a8fcabfbb3eb259de469eb9efc6e6b1d3061dc9ee2

full
  id:      9209854141
  sha256:  aace2648aac8b6d449c5ad1cefc5c2cbb74664a47853e8ca62855f3648809468
```

Each artifact contains the exact applied diff for modified modes, configure/build receipts, stdout/stderr, key lines, rootfs receipt, identity, and exit/summary files.

## Relationship to the earlier A/B

[`EXACT_CUSTOMIR_RETIREMENT_AB.md`](./EXACT_CUSTOMIR_RETIREMENT_AB.md) established that the complete exact-retirement diagnostic changes the real-FEX forced-different reload from stale SIGSEGV to successful generation-2 execution.

This 2×2 experiment goes further by isolating the two ownership layers. The positive full result is therefore not explainable by registry cleanup alone or translated-cache cleanup alone.

## Production implications

The remaining production problem is now dominated by lifetime ordering and concurrency rather than identifying the stale owner.

A production design should make registry retirement and exact synthetic-entry eviction one coherent lifecycle transaction, then address:

- retirement before destructive unmap, rather than after kernel `munmap()`;
- peer threads that may already be executing or have selected a translated `H` block;
- direct-link / dispatch-cache quiescence across threads;
- ownership generation so a reused virtual address cannot authorize stale state;
- every destructive guest mapping path that can remove thunk target text;
- the separate host-to-guest `GuestcallToHostTrampoline` retained-pointer surface.

The next high-value integration experiment is the original Vulkan teardown path with the full retirement semantics enabled, retaining llvmpipe, Venus, pin, and bogus-preload controls. If teardown still fails, capture host PC, `si_addr`, JIT membership, and guest RIP reconstruction so the remaining failure can be assigned to a specific execution path.

## External-contact state

No third-party/upstream issue, pull request, comment, review, reaction, or repository write was performed. All writes and Actions execution remained inside repositories owned by `teamleaderleo`.
