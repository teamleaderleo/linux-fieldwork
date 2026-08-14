# Callback in-flight unmap race proof — 2026-08-14

## Scope

Carrier: `teamleaderleo/FEX` branch `ci/callback-inflight-unmap-race-v3-20260814`, head `5c1eda9f08786101451877bc3a59616f58a63431`.

Exact FEX product under test: `71afe476751deac24adabd1adb575fd2337b6e0a`.

Retained synthetic fixture: `teamleaderleo/linux-fieldwork` commit `9eca19ac8743567ce2af7b4c82f2483d97c19b09`, archive SHA-256 `0582bf8832699cfb2614c1781473d07054ba01f03e3342735a45ea04735c2a01`.

GitHub Actions:

```text
run: 31787836044
job: 94727664063
artifact: 9214309358
artifact sha256: c32a8aae872b123b0be01339610361d410e5f785d1fe1bd4c0ea4554ad094fb3
```

The workflow completed successfully because its expected matrix includes a controlled crash in the unmap arm.

## Discriminator

The fixture's initial callback is entry 1. The worker callback is entry 2.

Diagnostic FEX pauses entry 2 inside `ThunkHandler_impl::CallCallback` after the trampoline has already supplied the raw guest unpacker and target values but before `HandleCallback` enters guest code.

For the unmap arm, the main guest thread then calls `dlclose` on the owner DSO. The existing callback tombstone diagnostic retires future calls before physical unmap. A second diagnostic hook releases the already-entered callback only after host `munmap` and VMA deletion have completed for the range containing its selected unpacker/target.

This directly distinguishes:

- future callback entries through the escaped native trampoline; and
- a callback that already crossed the selection boundary with raw guest executable addresses in hand.

## Matrix

```text
pin=0
unmap=139
```

### Pin control

The owner stays mapped. Entry 2 pauses inside FEX, no owner retirement arrives, the bounded diagnostic wait expires, and the callback resumes normally:

```text
pre-unload host->guest callback  rv=10053 want=10053
DIAG_CALLBACK_INFLIGHT_SELECTED entry=2 unpacker=0x7ffff7da2190 target=0x7ffff7da2170
CALLBACK_RACE_PINNED
DIAG_CALLBACK_INFLIGHT_PIN_TIMEOUT_RESUME unpacker=0x7ffff7da2190 target=0x7ffff7da2170
CALLBACK_RACE_WORKER_RETURN rv=10063
```

### Unmap arm

The same callback entry pauses with the same raw guest addresses. The owner then closes, the escaped host trampoline is tombstoned, the guest executable range is physically unmapped, the already-entered callback is released, and the process faults with exit 139:

```text
DIAG_CALLBACK_INFLIGHT_SELECTED entry=2 unpacker=0x7ffff7da2190 target=0x7ffff7da2170
CALLBACK_RACE_DLCLOSE_BEGIN target=0x00007ffff7da2170 unpacker=0x00007ffff7da2190
DIAG_CALLBACK_TOMBSTONE trampoline=0x7ffff7d7c000 unpacker=0x7ffff7da2190 target=0x7ffff7da2170 range=0x7ffff7da1000+0x5000
DIAG_CALLBACK_POST_UNMAP_RELEASE unpacker=0x7ffff7da2190 target=0x7ffff7da2170 range=0x7ffff7da1000+0x5000
DIAG_CALLBACK_INFLIGHT_RESUME unpacker=0x7ffff7da2190 target=0x7ffff7da2170
```

The receipt enforces that exact ordering. Byte positions in `unmap.stderr` were:

```text
DIAG_CALLBACK_INFLIGHT_SELECTED=289
DIAG_CALLBACK_TOMBSTONE=457
DIAG_CALLBACK_POST_UNMAP_RELEASE=581
DIAG_CALLBACK_INFLIGHT_RESUME=688
```

## Conclusion

Callback tombstoning solves **future entry** through an escaped native callback pointer. It cannot protect a callback that has already entered FEX and captured raw guest executable addresses before the owner is reclaimed.

That already-entered interval needs an execution-lifetime mechanism if the compatibility goal is safe concurrent unload:

- acquire an owner/generation execution lease before guest callback dispatch;
- keep that owner executable until the callback returns;
- retirement blocks future entries immediately via tombstone/state transition;
- physical reclamation occurs after outstanding leases reach zero.

The separate self-unload discriminator shows why this cannot be implemented as an unconditional synchronous drain inside `dlclose`: a callback that unloads its own owner would wait on its own active lease and deadlock. Reclamation therefore needs deferred retirement when the retiring thread currently holds a lease on that owner/generation.

This is the callback-side analogue of the previously demonstrated H→T select-before-unmap race.
