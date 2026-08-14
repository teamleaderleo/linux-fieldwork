# Pre-unmap target-cell retirement runtime proof

## Scope

This checkpoint extends the generation-neutral H→T target-cell result with an explicit lifecycle state transition at guest unmap.

The question is whether FEX can keep one compiled H entrypoint stable across guest thunk generations, retire only its current target before the outgoing guest mapping disappears, preserve current same-generation alias behavior, and later publish generation 2 without handler removal or lookup-cache invalidation.

## Diagnostic

Owned-FEX branch `ci/agent-l-arm64-20260814`.

Hosted ARM64 run `31771367805`, job `94677832465`, artifact `9208308655`. The executed FEX checkout was commit `491db78d0fd1dd6fae251936e250e1233e0afaf2`.

The diagnostic keeps one target cell per native H:

- first registration allocates the cell, stores generation-1 T, and installs one CustomIR H block;
- the compiled H block loads `cell->Target` each invocation and uses the original tail-exit semantics;
- before physical `munmap`, every cell whose live T lies in the outgoing guest range is changed from T to zero;
- a later registration for the same H may publish a new T only when the cell is zero;
- when one live H is presented with another different live T, the diagnostic keeps the first target, matching current FEX alias behavior;
- no CustomIR handler removal and no L1/L2/L3 cache invalidation participate in the generation handoff.

## Trace

The complete transition appears in one run:

```text
DIAG_CELL_NEW H=0x7ffff7d80860 T=0x7ffff7da21b0 slot=0xffa23c228000
DIAG_CELL_RETIRE H=0x7ffff7d80860 oldT=0x7ffff7da21b0 range=0x7ffff7da1000+0x5000 slot=0xffa23c228000
DIAG_CELL_REBIND H=0x7ffff7d80860 oldT=0 newT=0x7ffff7d781b0 slot=0xffa23c228000
DIAG_CELL_RETIRE H=0x7ffff7d80860 oldT=0x7ffff7d781b0 range=0x7ffff7d77000+0x5000 slot=0xffa23c228000
```

Generation 1 really disappears and generation 2 moves:

```text
old invoker after dlclose          0x00007ffff7da21b0 -> unmapped
old target after dlclose           0x00007ffff7da2170 -> unmapped
old unpacker after dlclose         0x00007ffff7da2190 -> unmapped
reload invoker                    old=0x00007ffff7da21b0 new=0x00007ffff7d781b0 DIFFERENT
native host stable                old=0x00007ffff7d80860 new=0x00007ffff7d80860
```

Before generation 2 republishes the empty cell, a retained H call still faults, as expected for a retired bridge:

```text
child retained Link after reload  signal=11 (Segmentation fault)
```

After generation 2 explicitly publishes its new target into the empty cell, the same stable H and same compiled H block recover:

```text
child Link after re-register      rv=1001035
child Link after re-register      exit=0
```

Fresh current-generation calls also succeed. The generation-1 host→guest callback remains stale while the generation-2 callback succeeds, keeping the callback lifetime class independent:

```text
child retained callback reload    signal=11 (Segmentation fault)
fresh/current callback            rv=10010053 want=10010053
child first callback after new    signal=11 (Segmentation fault)
child current callback after new  rv=10010093
child current callback after new  exit=0
```

## Result

The H→T generation handoff can be expressed as lifecycle publication rather than compiled-code retirement:

```text
live H -> T(gen1)
    |
pre-unmap retirement
    v
live H -> empty
    |
generation-2 registration
    v
live H -> T(gen2)
```

One generation-neutral compiled H block survives the entire sequence. Normal reload no longer requires CustomIR handler replacement, exact shared-map erasure, or per-thread lookup-cache invalidation.

This also preserves the existing live-alias rule: a second different T does not displace an already-live target. Generation replacement becomes valid only after the old target has first entered the explicit retired state.

## Remaining correctness work

The diagnostic is single-threaded. Publishing `Target=0` before `munmap` closes future selections but does not yet protect an emulation thread that loaded old T immediately before retirement and crosses into it after the guest text has been unmapped. A product unload-preserving implementation still needs an execution quiescence mechanism such as a return-aware lease or per-thread hazard/grace-period protocol.

The retirement transaction also needs rollback on failed `munmap`: if the physical unmap fails after a target was cleared, the old live target must be republished or the ownership update must otherwise be made transactional.

The host→guest callback path remains separate. It needs stable callback state plus retirement keyed by both guest target and guest unpacker, because the unpacker itself can live in the unloadable guest thunk wrapper.

For a near-term containment that avoids both in-flight reclamation races, keeping generated guest thunk DSOs resident remains a distinct candidate under test.

All source edits described here are diagnostic work on owned surfaces. No upstream FEX interaction occurred.
