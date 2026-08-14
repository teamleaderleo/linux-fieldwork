# Generation-neutral thunk target-cell runtime proof

## Scope

This checkpoint tests whether a compiled `LinkAddressToFunction` / CustomIR entrypoint must itself be retired and recompiled when a stable native host address `H` is rebound to a guest invoker `T` from a later guest thunk generation.

The earlier exact-retirement run proved that handler removal plus exact L1/L2/L3 eviction can recover generation-2 rebinding. This experiment asks a narrower question: can the compiled H block remain stable and resolve its current guest target indirectly at runtime?

## Diagnostic

Owned-FEX branch `ci/agent-j-arm64-20260814`, commit `a604537901db30fd5557c41814f23f399529fe51`.

Hosted ARM64 run `31770443240`, job `94675069380`, artifact `9207986364`.

The diagnostic replaces the captured immediate guest target with a stable target cell keyed by H:

- the first H registration allocates a target cell, stores generation-1 T, and installs one CustomIR H block;
- that H block loads `cell->Target` on every invocation and tail-exits to the loaded T using the original thunk control-flow semantics;
- a later registration of the same H only exchanges `cell->Target`; it performs no CustomIR handler removal and no lookup-cache invalidation.

The run deliberately omits unload retirement. Its purpose is generation-handoff/cache isolation only.

## Trace

```text
DIAG_CELL_NEW H=0x7ffff7d80860 T=0x7ffff7da21b0 slot=0xff8946428000
DIAG_CELL_REBIND H=0x7ffff7d80860 oldT=0x7ffff7da21b0 newT=0x7ffff7d781b0 slot=0xff8946428000
```

The guest thunk generation moved from `0x7ffff7da...` to `0x7ffff7d78...` while the native host address remained stable:

```text
reload invoker                    old=0x00007ffff7da21b0 new=0x00007ffff7d781b0 DIFFERENT
native host stable                old=0x00007ffff7d80860 new=0x00007ffff7d80860
```

After generation 2 explicitly publishes its new target into the existing cell:

```text
child Link after re-register      rv=1001035
child Link after re-register      exit=0
```

The retained callback remains independently stale and the current-generation callback succeeds, preserving the callback class as an orthogonal control.

## Result

A compiled H block does not need to capture T as an immediate. Loading T from a stable cell makes the compiled H entry generation-neutral: generation 2 can replace T and immediately reuse the same compiled H block without handler removal, shared-map erasure, or L1/L2 invalidation.

This directly eliminates the cache invalidation mismatch from ordinary H generation handoff. The earlier exact-eviction primitive remains useful as a cleanup/fallback operation for existing baked-target blocks, but it is unnecessary for rebinding once H code is target-cell based.

## Remaining lifetime problem

This experiment intentionally leaves the unload gap unchanged. Before generation 2 publishes its target, the cell still contains generation-1 T, so a retained H call after generation-1 text disappears still faults. A complete unload-capable design needs a retirement transaction that publishes an empty/retired cell before unmap and prevents an in-flight call that already selected old T from crossing into unmapped guest text.

A first lease prototype used a shared active counter and a generated call/return epilogue. It compiled but timed out on the first H invocation, so target-cell publication and execution quiescence are kept as separate mechanisms for further work.

Same-generation alias semantics also need to remain compatible with current FEX behavior: when one live H resolves to two different live guest invokers, keep the first mapping as FEX does today. A later generation should only repopulate a cell that has first entered the explicit retired/empty state.

All source edits here are diagnostic work on owned surfaces. No upstream FEX interaction occurred.
