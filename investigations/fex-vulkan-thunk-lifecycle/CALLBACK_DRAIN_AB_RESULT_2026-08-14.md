# FEX thunk lifetime: callback descriptor drain A-B — 2026-08-14

Carrier: `teamleaderleo/FEX` branch `ci/thunk-callback-descriptor-drain-20260814`

Run: `31785643435`

Artifact: `thunk-callback-inflight-drain-ab-31785643435`

## Matrix

```text
baseline=139
drain=0
```

## Descriptor-only baseline

The worker enters the host-to-guest callback and blocks in a native host thunk while the guest callback frame remains active.

Observed ordering:

```text
DIAG_CALLBACK_DESCRIPTOR_CREATE trampoline=0x7ffff7d4c000 descriptor=0x7ffff6000000 unpacker=0x7ffff7da2190 target=0x7ffff7da2270
DIAG_CALLBACK_DESCRIPTOR_LIVE descriptor=0x7ffff6000000 unpacker=0x7ffff7da2190 target=0x7ffff7da2270
INFLIGHT callback-entered-host-block
DIAG_CALLBACK_DESCRIPTOR_RETIRE trampoline=0x7ffff7d4c000 descriptor=0x7ffff6000000 unpacker=0x7ffff7da2190 target=0x7ffff7da2270 range=0x7ffff7da1000+0x5000
INFLIGHT dlclose-returned rc=0
INFLIGHT close-done-before-release=1
INFLIGHT released-host-block
```

The process exits 139 after release. Descriptor tombstoning prevents later callback entries, but it cannot preserve a callback frame that was already active when the guest DSO was unmapped.

## Execution-drain candidate

The drain candidate adds `Live -> Draining -> Revoked` plus an active callback count.

Observed ordering:

```text
DIAG_CALLBACK_DESCRIPTOR_CREATE trampoline=0x7ffff7d4c000 descriptor=0x7ffff6000000 unpacker=0x7ffff7da2190 target=0x7ffff7da2270
DIAG_CALLBACK_DESCRIPTOR_ACQUIRE descriptor=0x7ffff6000000 active=1
DIAG_CALLBACK_DESCRIPTOR_LIVE descriptor=0x7ffff6000000 unpacker=0x7ffff7da2190 target=0x7ffff7da2270
INFLIGHT callback-entered-host-block
DIAG_CALLBACK_DESCRIPTOR_DRAIN_BEGIN trampoline=0x7ffff7d4c000 descriptor=0x7ffff6000000 unpacker=0x7ffff7da2190 target=0x7ffff7da2270 active=1 range=0x7ffff7da1000+0x5000
DIAG_CALLBACK_DESCRIPTOR_DRAIN_WAIT descriptor=0x7ffff6000000 active=1
INFLIGHT close-done-before-release=0
INFLIGHT released-host-block
DIAG_CALLBACK_DESCRIPTOR_DRAIN_COMPLETE descriptor=0x7ffff6000000 active=0
INFLIGHT worker-returned rv=70053
INFLIGHT dlclose-returned rc=0
INFLIGHT joined worker=70053 close=0
DIAG_CALLBACK_DESCRIPTOR_REVOKED descriptor=0x7ffff6000000 state=2 active=0
INFLIGHT child stale-first-callback exit=113
INFLIGHT DRAIN_PASS
```

The candidate waits outside `ThunksMutex`, so the blocked callback can continue through thunk paths while draining. After the active callback releases its lease, guest teardown completes. A later retained stale trampoline is rejected with exit 113.

## Native comparison

Run `31785817017` executes the equivalent lifetime sequence with a native DSO callback on x86-64 and ARM64:

```text
pin=0
unmap=139
```

The native callback has already entered its DSO and is blocked inside `read()`. Another thread `dlclose`s the DSO, confirms the callback address is unmapped, releases the callback, and the process exits 139 when execution returns toward the unmapped DSO frame.

Therefore the drain candidate intentionally supplies a stronger lifetime guarantee than native callback-pointer semantics. It remains useful as a causal upper bound and perhaps as an FEX-specific safety policy if separately justified, but its success alone is not evidence that FEX requires the drain for compatibility.

## Next adversarial discriminator

The current drain waits for `Active == 0`. A callback that itself initiates teardown of its owner can hold the active lease on the same thread that enters `RetireGuestRange`. That sequence can self-wait indefinitely.

Next fixture:

1. enter a host-to-guest callback and acquire descriptor lease;
2. from inside the guest callback target, initiate owner teardown on the same emulation thread;
3. descriptor-only candidate should follow its existing stale/native-style behavior;
4. drain candidate is expected to expose a self-drain deadlock unless it detects the current lease;
5. retain timeout and diagnostics as a design constraint before considering any execution-drain production path.
