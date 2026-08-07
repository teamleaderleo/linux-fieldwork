# Kernel VT pending-state boundary — 2026-08-08

## Result

Current Linux `drivers/tty/vt/vt_ioctl.c` confirms the critical asymmetry behind systemd issue #42091:

- `VT_SETMODE` replaces `vc->vt_mode`, updates `vt_pid`, and unconditionally sets `vc->vt_newvt = -1`;
- `VT_GETMODE` copies only `vc->vt_mode` to userspace;
- `VT_GETSTATE` exposes the active VT and an open-VT bitmask;
- none of those interfaces exposes `vc->vt_newvt`, the pending switch target consumed by the release protocol.

Therefore current userspace cannot reliably query “is there a pending switch-from that `VT_SETMODE` would destroy?” before `session_restore_vt()` resets the mode.

## Consequence for candidate families

### Defensive VT_GETMODE check

Insufficient as a correctness predicate. `VT_PROCESS` means the VT is process-controlled, not that a switch is pending. A restore path cannot distinguish:

- process-controlled VT with no pending transition, where normal cleanup should restore `VT_AUTO`;
- process-controlled VT with `vt_newvt >= 0`, where `VT_SETMODE` would erase the pending transition.

A `VT_GETMODE`-only repair is therefore heuristic.

### Existing userspace state

`Seat.pending_switch` also cannot supply the missing fact on VT seats: the VT branch of `session_activate()` returns through `chvt()` before the non-VT `pending_switch` assignment.

### Priority ordering

When the kernel release signal and D-Bus controller teardown are both ready in the same sd-event iteration, assigning the release signal an important priority is now the smallest mechanism that uses information userspace actually has: the kernel has delivered the release notification, so acknowledge it before normal-priority teardown work.

Priority still does not prove safety for a window where D-Bus teardown executes before the signal becomes readable. That remaining window must be tested, not assumed away.

## Next discriminator

Compile the retained priority candidate and then capture two timelines:

1. both sources ready together: release must win deterministically;
2. ReleaseControl begins before the signal is ready: determine whether the kernel can already have `vt_newvt` pending in that window.

If case 2 is observable, priority alone is not a complete protocol repair and a new earlier userspace transition marker or kernel API would be required.

## Boundary

Public kernel and systemd source review only. No kernel/systemd upstream interaction and no live VT state was changed.