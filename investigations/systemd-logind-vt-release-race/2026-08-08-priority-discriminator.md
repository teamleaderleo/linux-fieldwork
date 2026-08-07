# logind VT release race — priority discriminator, 2026-08-08

## TL;DR

Current systemd `a24a50cfc284e02f48c1daac11d8ffbeb0f829d5` still has the event-order race from `systemd/systemd#42091` and no overlapping upstream PR was found.

Two source questions are now resolved:

1. `Seat.pending_switch` cannot protect this race. `session_activate()` returns directly to `chvt()` on seats with VTs; `pending_switch` is only populated by logind's non-VT seat switching path.
2. A priority experiment does not require persistent new Manager state. sd-event explicitly supports creating an event source non-floating, setting properties such as priority, then marking it floating and dropping the temporary caller reference.

The next diagnostic candidate is therefore: make only the `SIGRTMIN+0` VT-release signal source `SD_EVENT_PRIORITY_IMPORTANT`, leaving the system bus at `SD_EVENT_PRIORITY_NORMAL`.

This is a diagnostic candidate, not a final-fix claim.

## Exact source boundary

- canonical systemd: `a24a50cfc284e02f48c1daac11d8ffbeb0f829d5`
- issue: `systemd/systemd#42091`
- `src/login/logind.c`: system bus attaches at `SD_EVENT_PRIORITY_NORMAL`; VT release source has default normal priority
- `src/login/logind-session.c`: VT-seat `session_activate()` calls `chvt()` and does not set `Seat.pending_switch`
- `src/login/logind-seat.h`: `Seat.pending_switch` exists, but belongs to the non-VT session-switch mechanism
- sd-event priority contract: smaller values dispatch first when multiple sources have seen events; `IMPORTANT=-100`, `NORMAL=0`

## Why the existing pending_switch cannot be reused

For VT seats, `session_activate()` does:

```text
seat has VTs
  -> require vtnr
  -> chvt(vtnr)
  -> return
```

The assignment:

```text
s->seat->pending_switch = s
```

occurs only after the VT-seat branch has returned, in the non-VT seat implementation that pauses session devices in userspace before `seat_complete_switch()`.

Therefore `Seat.pending_switch` is not set during the kernel `VT_ACTIVATE` / `VT_PROCESS` handshake described by issue #42091. Testing it in `session_restore_vt()` would not distinguish the reported D-Bus-first ordering.

## Why priority is a valid first discriminator

`manager_connect_bus()` attaches the system bus to `m->event` at `SD_EVENT_PRIORITY_NORMAL`.

`manager_connect_console()` creates the `SIGRTMIN+0` release source without changing its priority, so it is also normal priority.

The sd-event contract states that when multiple sources have seen events, lower numerical priority dispatches first. Same-priority ordering is undefined and only loosely follows when the backing kernel primitives happened to be observed.

The comment above `manager_vt_switch()` says the release signal must be acknowledged immediately. Assigning that one source `SD_EVENT_PRIORITY_IMPORTANT` converts the exact undefined bus-vs-release ordering into a defined release-first ordering when both are ready for the same dispatch cycle.

## Diagnostic candidate

See `priority-candidate.patch` in this directory.

The candidate deliberately does not:

- change bus priority;
- change any other logind signal source;
- add per-session or per-seat state;
- alter `vt_restore()`, `session_restore_vt()`, or `session_drop_controller()`;
- claim to cover a D-Bus teardown that has already executed before the signal becomes ready in userspace.

## Acceptance matrix

### Candidate supports the observed mechanism if

- with both D-Bus ReleaseControl and SIGRTMIN+0 ready, the release handler always dispatches first;
- `VT_RELDISP=1` completes before controller teardown reaches `VT_SETMODE(VT_AUTO)`;
- the reporter's high-rate reproducer stops losing `vt_newvt`;
- normal controller loss with no pending VT switch still calls `session_restore_vt()` normally;
- existing logind tests and build remain green.

### Candidate is insufficient if

- the failing trace shows ReleaseControl entering `session_restore_vt()` before the signal source becomes ready to sd-event;
- the kernel pending switch exists but no userspace signal is dispatchable yet;
- prioritizing the signal changes the measured ordering but `VT_SETMODE(VT_AUTO)` can still erase a pending transition through another path.

In those cases the final repair needs state available earlier than `manager_vt_switch()`, or a defensive kernel-facing restore protocol. A flag set inside `manager_vt_switch()` remains too late for the D-Bus-first case.

## Test plan

1. Compile the priority candidate on exact current systemd.
2. Add a deterministic sd-event-level fixture with two simultaneously-ready sources representing release and controller teardown; verify normal/normal has no contractual order while important/normal gives release first.
3. Run a VT integration fixture that captures `VT_ACTIVATE`, `VT_SETMODE`, `VT_RELDISP`, and `VT_WAITACTIVE` results.
4. Test controller drop with no pending switch as the negative control.
5. If available, A/B the candidate on the issue reporter's reproducing hardware; treat that as hardware confirmation, not the only correctness proof.

## Current disposition

`PROMOTE TO COMPILE/ORDERING EXPERIMENT`

The one-line conceptual change is now source-justified enough to compile and test, but not yet ready as a final systemd repair.

## Authority

No canonical systemd issue comment, PR, review, email, or other upstream interaction was made.