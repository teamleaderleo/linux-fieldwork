# FEX thunk lifetime: callback self-drain discriminator — 2026-08-14

Carrier: `teamleaderleo/FEX` branch `ci/thunk-callback-selfdrain-20260814`

Run: `31786449265`

Artifact: `thunk-callback-selfdrain-31786449265`

## Question

The execution-drain prototype waits for a callback descriptor's `Active` count to reach zero before allowing guest owner teardown to finish. What happens if the callback holding that active lease itself initiates `dlclose` of its own guest owner?

## Fixture

Generation-8 guest DSO callback target is configured with its own `dlopen` handle. The host-to-guest callback is then invoked normally. While the descriptor lease is active, `lifetime_guest_target()` calls `dlclose(self_handle)` on the same emulation thread.

No host blocking thread or scheduler race is required: the callback itself creates the dependency.

## Matrix

```text
baseline=139
drain=124
```

The workflow asserts both outcomes and completed successfully.

## Descriptor-only baseline

Key ordering:

```text
SELF_DRAIN configured handle=0x562fad72f2d0 target=0x7ffff7ebd290 unpacker=0x7ffff7ebd1b0
SELF_DRAIN invoke target=0x7ffff7ebd290 unpacker=0x7ffff7ebd1b0
DIAG_CALLBACK_DESCRIPTOR_CREATE trampoline=0x7ffff7eb8000 descriptor=0xffc78761d000 unpacker=0x7ffff7ebd1b0 target=0x7ffff7ebd290
DIAG_CALLBACK_DESCRIPTOR_LIVE descriptor=0xffc78761d000 unpacker=0x7ffff7ebd1b0 target=0x7ffff7ebd290
DIAG_CALLBACK_DESCRIPTOR_RETIRE trampoline=0x7ffff7eb8000 descriptor=0xffc78761d000 unpacker=0x7ffff7ebd1b0 target=0x7ffff7ebd290 range=0x7ffff7ebc000+0x5000
```

Process exit: `139`.

The descriptor is retired while its guest callback frame is executing. Teardown proceeds and the same-thread stale frame follows the native-style crash path.

## Drain candidate

Key ordering:

```text
SELF_DRAIN configured handle=0x5557f4a1f2d0 target=0x7ffff7ebd290 unpacker=0x7ffff7ebd1b0
SELF_DRAIN invoke target=0x7ffff7ebd290 unpacker=0x7ffff7ebd1b0
DIAG_CALLBACK_DESCRIPTOR_CREATE trampoline=0x7ffff7eb8000 descriptor=0xff0ccaa33000 unpacker=0x7ffff7ebd1b0 target=0x7ffff7ebd290
DIAG_CALLBACK_DESCRIPTOR_ACQUIRE descriptor=0xff0ccaa33000 active=1
DIAG_CALLBACK_DESCRIPTOR_LIVE descriptor=0xff0ccaa33000 unpacker=0x7ffff7ebd1b0 target=0x7ffff7ebd290
DIAG_CALLBACK_DESCRIPTOR_DRAIN_BEGIN trampoline=0x7ffff7eb8000 descriptor=0xff0ccaa33000 unpacker=0x7ffff7ebd1b0 target=0x7ffff7ebd290 active=1 range=0x7ffff7ebc000+0x5000
DIAG_CALLBACK_DESCRIPTOR_DRAIN_WAIT descriptor=0xff0ccaa33000 active=1
```

Process exit: `124` from the 8-second outer timeout.

There is no `DRAIN_COMPLETE`: the thread inside `dlclose` is waiting for `Active == 0`, while that same thread owns the active callback lease and cannot release it until `dlclose` returns. This is a direct self-wait.

## Consequence

The callback execution-drain prototype is unsuitable as a simple unconditional production rule. It both supplies lifetime stronger than the native callback baseline and deadlocks when an active callback tears down its own owner.

Any stronger callback lifetime policy would need an explicit re-entrancy/self-teardown design, for example tracking active leases per emulation thread and defining what final-owner teardown does when the current thread is one of the holders. That design still needs a compatibility justification because native x86-64 and ARM64 already fault when an entered DSO callback is concurrently unloaded.

The narrower production line remains descriptor tombstoning plus owner-generation-aware registration/retirement:

- retained stale host trampolines stop initiating new guest callbacks after target or unpacker owner death;
- same-address reload does not resurrect the old trampoline;
- fresh explicit registration creates a new live callback descriptor;
- target and unpacker owner IDs should participate independently in destructive mapping prepare/commit/rollback;
- in-flight callback survival does not need to be guaranteed solely for native equivalence.
