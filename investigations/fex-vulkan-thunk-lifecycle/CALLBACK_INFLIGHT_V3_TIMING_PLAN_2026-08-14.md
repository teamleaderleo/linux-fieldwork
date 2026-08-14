# Callback in-flight race v3 timing plan — 2026-08-14

## Timing clarification

The callback tombstone diagnostic inserts `ThunkHandler_impl::RetireGuestRange(...)` at the beginning of `SyscallHandler::GuestMunmap`, before the baseline unmap block.

Baseline `GuestMunmap` then performs, in order:

1. host `::munmap(addr, length)` (or the 32-bit allocator equivalent),
2. `TrackMunmap(...)` / VMA deletion,
3. exit from the VMA lock,
4. `InvalidateCodeRangeIfNecessary(...)`,
5. ForceTSO metadata removal,
6. return.

Therefore the existing tombstone hook intentionally retires **future host callback entries before physical guest executable reclamation**. This is the right future-entry ordering, and it also gives the in-flight discriminator a precise post-unmap release point.

## v3 discriminator

Remove guest/host filesystem marker synchronization entirely.

Diagnostic FEX state:

- process-global atomic callback-entry counter;
- entry 1 is the fixture's known pre-unload registration callback;
- entry 2 is the worker callback used by the race;
- when entry 2 reaches `ThunkHandler_impl::CallCallback`, store its already-selected `GuestUnpacker` and `GuestTarget`, log `DIAG_CALLBACK_INFLIGHT_SELECTED`, and wait on an internal release flag;
- the wait is bounded so the pin control can auto-resume if no owner retirement occurs.

Unmap arm:

1. guest starts the worker and allows enough time for entry 2 to reach the FEX pause;
2. guest main thread calls `dlclose` on the owner DSO;
3. pre-unmap `RetireGuestRange` tombstones any escaped host trampoline whose cached target/unpacker intersects the retiring range;
4. baseline host `::munmap` physically removes that range and VMA tracking commits the deletion;
5. a diagnostic post-unmap hook checks the paused raw target/unpacker against the just-unmapped range and sets the internal release flag;
6. paused `CallCallback` resumes using the raw values it captured before retirement.

Required receipt ordering:

```text
DIAG_CALLBACK_INFLIGHT_SELECTED
DIAG_CALLBACK_TOMBSTONE
DIAG_CALLBACK_POST_UNMAP_RELEASE
DIAG_CALLBACK_INFLIGHT_RESUME
```

Expected result: the already-entered callback faults when it attempts to enter the now-unmapped guest unpacker/target, while future calls through the escaped stable host trampoline remain controlled by the tombstone path.

Pin arm:

- no `dlclose`;
- the bounded FEX-side wait expires and logs `DIAG_CALLBACK_INFLIGHT_PIN_TIMEOUT_RESUME`;
- worker callback returns the expected generation-1 value (`10063`).

This experiment changes no trampoline template layout and introduces no production drain policy.
