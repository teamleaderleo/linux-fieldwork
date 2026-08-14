# FEX general `mremap` lifetime matrix plan — 2026-08-14

Planning note derived from the green `MREMAP_FIXED` repair and the `MREMAP_DONTUNMAP` owner-gap discovery. These are hypotheses until the cases run.

## Why a blanket source retirement is wrong

The old target range has different lifetime semantics depending on the remap outcome:

- fixed move: old source content leaves, fixed destination content is overwritten;
- `MREMAP_DONTUNMAP`: old source VMA survives, but its original content leaves;
- non-fixed `MREMAP_MAYMOVE`: kernel may either keep the old address or move to a new address;
- in-place grow: old target content remains at the same address;
- in-place shrink: retained prefix remains valid, truncated tail disappears;
- `old_size == 0` mirror case: existing shared mapping remains and a second mapping is created.

Therefore retiring the complete old range before every `mremap` would break valid pointer identity for in-place results and the mirror case.

## Next discovery matrix

### A. Forced non-fixed move

Create source code page returning `111`, register `H -> source`, and force expansion to move by occupying the immediately following range. Call:

```c
mremap(source, old_size, larger_size, MREMAP_MAYMOVE)
```

Expected current candidate:

- new mapping contains the original function;
- old source is gone;
- old H claim remains active;
- explicit `H -> new` registration becomes standby, likely with the same mapped-resource owner ID;
- H faults through the stale old address.

This should be the non-fixed analogue of the `DONTUNMAP` stale-source-claim result.

### B. In-place grow

Reserve contiguous capacity so growth stays at the same address. Register H into the retained first page and grow in place.

Required behavior:

```text
H remains active
owner identity remains stable
H still returns 111
```

Any whole-source pre-retirement policy that leaves H revoked here is wrong.

### C. In-place shrink with two claims

Create a two-page mapping with executable targets in both pages:

```text
H1 -> page 0
H2 -> page 1
```

Shrink to one page in place.

Required behavior:

```text
H1 remains active
H2 retires/revokes
```

This is the discriminator for prefix-versus-tail retirement.

### D. `old_size == 0` shared mirror

If the host/kernel permits the legacy mirror form, register H into the original shared mapping and clone it with `mremap(old, 0, new_size, MREMAP_MAYMOVE)`.

Required behavior:

```text
original H remains active
new mapping is an additional view
```

No source retirement should occur merely because a new view was created.

## Transaction design to test after discovery

A general transactional algorithm can split the old range according to the known requested size, then decide commit/rollback based on the returned address.

For `old_size > 0`:

### Grow or same size (`new_size >= old_size`)

If movement is possible, prepare retirement for the entire old range before the syscall.

After success:

- `result != old_address` or `MREMAP_DONTUNMAP` -> commit source retirement;
- `result == old_address` -> rollback source retirement because old target content stayed in place.

On failure: rollback.

### Shrink (`new_size < old_size`)

Split the old mapping into:

```text
retained prefix = [old, old + new_size)
truncated tail  = [old + new_size, old + old_size)
```

Prepare separate retirement tokens for prefix and tail if movement is possible.

After success:

- moved result -> commit both prefix and tail retirements;
- in-place result -> rollback prefix, commit tail.

On failure: rollback both.

For a no-`MAYMOVE` in-place shrink, only the tail needs a pre-syscall retirement transaction.

### Fixed destination

Keep the already-proven separate destination retirement transaction and explicit destination code invalidation.

### Mirror case

`old_size == 0` receives no source retirement.

## Concurrency boundary

Pre-syscall prepare remains important. Retiring only after a successful kernel move creates a window where another FEX thread can resolve an obsolete H after the old content has already moved/unmapped.

Commit/rollback after the syscall lets the lifetime model follow the kernel result while retirement is already visible before destructive content movement.

## Interaction with H-generation dispatch

The remap transaction decides **which H claims cease to be current**. The planned H-generation dispatch token protects an already-running old H bridge from carrying a retired claim into a later target state. These are complementary pieces:

- remap retirement updates claim state;
- H generation protects in-flight synthetic bridge metadata;
- ordinary guest code that was already selected follows the native concurrency boundary measured separately.
