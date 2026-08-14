# FEX thunk lifetime: callback ABA and in-flight boundary — 2026-08-14

## Same-address callback ABA already has a strong tombstone result

Carrier: `teamleaderleo/FEX` branch `ci/callback-tombstone-diagnostic-20260814`

Run: `31745628556`

Artifact: `thunk-callback-tombstone-aba-31745628556`

Generation 1 registers a host-to-guest callback trampoline whose embedded guest executable dependencies are:

- `GuestTarget = 0x7ffff7da2170`
- `GuestUnpacker = 0x7ffff7da2190`

After `dlclose`, both guest addresses are unmapped. Reload then places the new guest DSO at the same addresses. The native host function also stays at the same host address.

Observed:

```text
reload invoker                    old=0x00007ffff7da21b0 new=0x00007ffff7da21b0 SAME
native host stable                old=0x00007ffff7d80860 new=0x00007ffff7d80860
child retained Link after reload  rv=1001032
child retained Link after reload  exit=0
child retained callback reload    exit=113
fresh/current callback            rv=10010053 want=10010053
child first callback after new    exit=113
child current callback after new  rv=10010093
child current callback after new  exit=0
```

Diagnostics:

```text
DIAG_CALLBACK_TOMBSTONE trampoline=0x7ffff7d7c000 unpacker=0x7ffff7da2190 target=0x7ffff7da2170 ...
DIAG_CALLBACK_REVOKED invoked
DIAG_CALLBACK_REVOKED invoked
DIAG_CALLBACK_TOMBSTONE trampoline=0x7ffff7d7c030 unpacker=0x7ffff7da2190 target=0x7ffff7da2170 ...
```

The retained generation-1 callback therefore stays revoked even when generation 2 reuses the same numeric target and unpacker addresses. Fresh registration creates a distinct live trampoline. The older raw `LinkAddressToFunction` path behaved differently and reattached by numeric address until the owner-generation work retired it pre-reuse.

This means callback cache retirement already prevents stale trampoline resurrection after a completed unload. Owner IDs remain useful for precise destructive-operation ownership, rollback, and mixed-owner target/unpacker dependencies; they are not required merely to distinguish the retained old trampoline instance from a freshly registered one after unload.

## Callback descriptor prototype

Carrier family: `ci/thunk-callback-descriptor-20260814` and `ci/thunk-callback-descriptor-drain-20260814`

The descriptor prototype replaces mutable executable trampoline payload with an immutable heap descriptor:

```text
GuestCallbackDescriptor {
  GuestUnpacker
  GuestTarget
  State
}
```

The host trampoline embeds the stable descriptor pointer. Callback invocation reads the descriptor at execution time. Retirement finds callbacks whose target or unpacker belongs to the retiring guest range, marks the descriptor revoked, and erases the cache entry. A retained host trampoline therefore has a stable tombstone object to consult after its guest executable dependencies die.

The current descriptor prototype tracks target/unpacker by numeric address/range. The owner-generation candidate should eventually store owner IDs for both dependencies so a callback can express two independent guest mapping lifetimes and participate in destructive syscall prepare/commit/rollback.

## Execution-drain prototype

The drain extension changes descriptor state to:

```text
Live -> Draining -> Revoked
```

Callback entry calls `TryAcquire()` and increments an active count. Retirement marks matching descriptors Draining, removes cache entries, drops the global thunk-registry lock, then waits for active callbacks to release before marking Revoked.

This is a useful diagnostic upper bound because it guarantees guest callback frames finish before their owner mapping is destroyed. It also introduces lifetime semantics stronger than the native callback-pointer baseline below.

## Native entered-callback baseline

Carrier: `teamleaderleo/FEX` branch `ci/native-entered-callback-dlclose-20260814`

Run: `31785817017`

Artifacts:

- `native-entered-callback-amd64-31785817017`
- `native-entered-callback-arm64-31785817017`

Fixture:

1. `dlopen` a native DSO.
2. Worker calls a DSO callback.
3. Callback writes an `entered` byte, then blocks inside `read()` while its DSO frame is still active.
4. Controller either pins the DSO or `dlclose`s it.
5. Unload case verifies the callback address lost its mapping.
6. Controller writes the release byte.
7. Worker attempts to return from `read()` into the DSO callback frame.

Native x86-64:

```text
arch=amd64
pin=0
unmap=139
```

Native ARM64:

```text
arch=arm64
pin=0
unmap=139
```

Both unload receipts reach:

```text
NATIVE_ENTERED callback-entered target=... mapped=1
NATIVE_ENTERED owner-closed mapped=0
NATIVE_ENTERED callback-released target=...
timeout: the monitored command dumped core
```

Both pin controls reach:

```text
NATIVE_ENTERED owner-pinned mapped=1
NATIVE_ENTERED callback-released target=...
NATIVE_ENTERED worker-return value=1023
NATIVE_ENTERED final value=1023 pin=1
```

## Consequence

Concurrent `dlclose` of a DSO while another native thread is already executing one of its callbacks has the same stale-frame crash as the earlier raw selected-function-pointer control. FEX therefore does not need an execution drain merely to emulate native callback-pointer lifetime.

The callback-specific FEX obligation is narrower:

- a host trampoline retained by native code must stop initiating new guest callbacks once either guest dependency owner dies;
- same-address reuse must not resurrect that retained trampoline;
- fresh explicit callback registration may create a new live descriptor for the new owner generation;
- destructive replacement rollback must restore a descriptor only when the old owner mapping survives;
- target and unpacker may belong to different guest mapping generations, so both dependencies belong in the callback ownership record.

The execution-drain experiment can still tell us whether a stronger lifetime guarantee eliminates a observed FEX crash, but a production patch should justify that guarantee independently from native equivalence. A same-thread callback that initiates teardown also deserves a deadlock test before any drain design is considered shippable.
