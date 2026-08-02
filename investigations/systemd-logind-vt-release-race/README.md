# systemd-logind VT release and controller-drop race

## TL;DR

At systemd commit `ac33190d1f66e870d511827cbed3ebeee2d704c2`, the source still permits the race described in `systemd/systemd#42091`: the system bus is attached to the event loop at `SD_EVENT_PRIORITY_NORMAL`, the VT release signal source is added without a different priority, and `Session.ReleaseControl()` reaches `session_drop_controller()` which restores `VT_AUTO` immediately. There is no explicit state recording that the kernel has a pending VT release to acknowledge. Source review establishes a live ordering hazard; it does not yet establish the best repair.

## Explain like I'm five

Two messages arrive almost together:

- the screen switch says, “please release this console now”;
- the old desktop says, “I am done controlling the console.”

If the second message is handled first, logind resets the console before answering the first message. The kernel forgets the pending switch, so the process waiting for the new console can block.

Literal example: kernel queues SIGRTMIN release request → greeter sends `ReleaseControl()` → D-Bus handler runs first and calls `VT_SETMODE(VT_AUTO)` → kernel clears its pending target → later `VT_RELDISP` cannot complete the switch.

## Why care

The user can see a long black screen or be returned to the login greeter even though the desktop started. The blocked operation is a kernel VT transition, so consumer-side timeouts only interrupt one caller; they do not repair logind's protocol state for other display managers or fast-user-switch paths.

## Current state

- State: `SCOPING`
- Exact working head: canonical `ac33190d1f66e870d511827cbed3ebeee2d704c2`
- Latest authoritative gate or artifact: current source review plus the public issue's bpftrace attribution
- First incomplete step: build a deterministic event-order test that drives a pending VT release and controller drop without relying on fast GPU hardware
- Cleanup state: no VT mode, session, compositor, signal source, or login-manager state changed in this round
- Next safe action: model the two event orders and define the invariant before selecting priority ordering or explicit state
- External-contact state: none authorized or made

## Intent and precedent

The VT integration comments state that release signals must be acknowledged immediately and that logind uses synchronous `VT_PROCESS` mode. `manager_vt_switch()` reads the active VT and calls `session_leave_vt()`, which pauses devices and invokes `vt_release(..., restore=false)`.

Separately, controller loss and `ReleaseControl()` call `session_drop_controller()`. That function releases controlled devices, saves session state, and calls `session_restore_vt()`. `session_restore_vt()` invokes `vt_restore()`, which returns the terminal to normal automatic VT handling, then closes the session's VT descriptor.

The system bus is attached to the same `sd_event` loop at `SD_EVENT_PRIORITY_NORMAL`. The signal source is added without a subsequent priority override, so no source-level ordering guarantee gives the VT release handler precedence over the D-Bus handler.

The public report includes kernel and user-stack tracing showing the controller-drop path reaching `VT_SETMODE(VT_AUTO)` shortly before the signalfd path. No matching upstream pull request was found during this round.

## Question

What invariant should prevent controller teardown from restoring a VT while a kernel-requested VT release is pending, including failure and shutdown paths?

## Source

- Project: systemd
- Public issue: `systemd/systemd#42091`
- Requested revision: current canonical `main` observed 2026-08-03
- Resolved commit: `ac33190d1f66e870d511827cbed3ebeee2d704c2`
- `src/login/logind.c` blob: `9fcf57ab91699ee4317f1b03c0e952c04c131bf6`
- `src/login/logind-session.c` blob: `f5fb47920749c2e3aa64669c4a0516626f898f16`
- Candidate source commit: none
- Controlled fork: `teamleaderleo/systemd`
- Local source path: not imported yet

## Environment

The public report used a Fedora system with a Wayland greeter/session and fast GPU teardown. A contribution-quality fixture should reduce dependence on that hardware.

Record:

- systemd and kernel commits;
- login manager and compositor versions;
- active VT and session IDs;
- `VT_GETMODE` results;
- signal and bus event timestamps;
- event-source priorities;
- `VT_SETMODE`, `VT_RELDISP`, `VT_ACTIVATE`, and `VT_WAITACTIVE` calls and results;
- controller ownership and session lifecycle transitions.

## Current source behavior

### Event sources

`manager_connect_bus()` attaches the system bus to the manager event loop at normal priority.

`manager_connect_console()` adds the `SIGRTMIN+0` release signal source and does not set a distinct priority.

### Signal path

`manager_vt_switch()`:

1. reads the current active VT;
2. finds the active session with a VT descriptor;
3. calls `session_leave_vt()`;
4. `session_leave_vt()` pauses session devices;
5. it calls `vt_release(vtfd, restore=false)` to acknowledge the kernel release.

### Controller-drop path

`session_drop_controller()`:

1. removes bus tracking;
2. restores the original session type;
3. releases session devices and controller identity;
4. saves session state;
5. calls `session_restore_vt()`.

`session_restore_vt()` calls `vt_restore(vtfd)`, retries with a reopened VT on `EIO`, logs failure, and closes `s->vtfd`.

No current field on `Session`, `Seat`, or `Manager` in the reviewed path records “kernel VT release pending and not yet acknowledged.”

## Protocol invariant

The kernel-facing invariant should be written before the patch:

> Once a VT release request has been observed or is pending for a VT in `VT_PROCESS` mode, logind must not issue a mode-reset operation that can discard that request before it has either acknowledged the release or deliberately resolved a terminal failure path.

This is stronger and more local than “the signal callback should usually run first.”

## Candidate families

### A. Event-priority ordering

Set the signal source to an important priority so it dispatches before normal-priority bus work already queued in the same event iteration.

Advantages:

- minimal change;
- directly addresses the observed dispatch order;
- easy to test with queued signal and bus messages.

Risks:

- priority is a scheduler preference, not protocol state;
- it affects every VT release signal relative to all normal-priority work;
- it may not cover controller teardown that starts before the signal is readable or a pending kernel state not yet reflected in userspace;
- it can hide, rather than represent, the invariant.

### B. Explicit pending-release state

Record pending VT transition state and block or defer `session_restore_vt()` until release acknowledgement or a terminal failure path.

Possible homes:

- per-session, when a specific controller/VT owns the handshake;
- per-seat, when the transition belongs to the seat's active VT;
- manager plus VT number, if the kernel signal is global and session identity can change during lookup.

Advantages:

- represents the protocol explicitly;
- limits the repair to VT lifecycle behavior;
- supports assertions and deterministic unit tests.

Risks:

- the userspace signal arrives after the kernel has already marked a release pending, so state set only inside `manager_vt_switch()` may be too late to stop a bus handler that runs first;
- state must clear on successful release, `EIO`, failed reopen, session free, seat change, shutdown, and daemon restart;
- multiple or stale signals and legacy sessions require defined behavior.

### C. Defensive restore sequencing

Before restoring, query VT mode and attempt a release acknowledgement when the terminal is still in `VT_PROCESS` mode.

Advantages:

- protects every restore call site;
- small local change.

Risks:

- `VT_GETMODE` reports mode but not whether a target switch is actually pending;
- an unconditional release attempt may acknowledge a nonexistent or unrelated transition;
- it can mix cleanup and transition protocols in a generic terminal helper.

### D. Remove restore from controller drop

Not acceptable as a general repair. Controller disappearance without a successor still requires restoring the VT to a usable state. Removing cleanup would trade the race for leaked `VT_PROCESS` state.

## The key design problem

A per-session flag set only by `manager_vt_switch()` cannot prevent the exact reported ordering when D-Bus dispatch occurs first. An explicit-state design therefore needs a source of truth available before restore, for example:

- a kernel query capable of identifying a pending switch, if one exists;
- ordering the signal first, then using state to protect subsequent paths;
- deferring restore by one event-loop turn while draining higher-priority VT signals;
- a two-part repair: important signal priority plus explicit state during and after signal handling.

This is why a one-line priority change and a state flag should be evaluated together rather than treated as mutually exclusive without testing.

## Deterministic reproduction design

### Kernel/integration fixture

1. Create or use a controlled VT session with a controller and valid `vtfd`.
2. Put the VT in `VT_PROCESS` mode with logind's release signal.
3. Initiate `VT_ACTIVATE` from a helper that records the `VT_WAITACTIVE` duration.
4. Arrange for `ReleaseControl()` and the signalfd event to be ready in the same event-loop window.
5. Vary event-source priority or insert a controlled barrier so both dispatch orders can be observed.
6. Trace relevant ioctls and userspace stacks.

### Model/unit fixture

Where direct VT integration is too hardware-dependent, factor the decision into a small state machine and test event sequences:

- `release-request`, then `controller-drop`;
- `controller-drop`, then `release-request` already pending in kernel;
- release failure;
- controller disappears without any pending switch;
- session free during transition;
- repeated signal;
- switch to legacy session;
- daemon shutdown/restart boundary.

The model must not claim kernel proof by itself, but it can make the intended transition invariant reviewable.

## Results

### Demonstrated by current source review

- bus and VT signal handling share the same event loop without a source-level priority distinction favoring the release signal;
- the signal path acknowledges release through `session_leave_vt()`;
- controller drop restores VT mode immediately through `session_restore_vt()`;
- the reviewed path has no explicit pending-release state;
- the current code therefore contains the ordering ingredients described by the public report;
- no competing pull request matching issue 42091 or the exact pending-release terms was found during this round.

### Not yet demonstrated here

- a local current-head race reproduction;
- which event was already queued at the instant of controller teardown;
- whether important priority alone closes all windows;
- whether the kernel exposes a safe pending-switch query;
- the correct owner and lifetime of explicit state;
- behavior across daemon restart.

## Interpretation

The report remains technically actionable on current source. The unsafe operation is not controller cleanup by itself; it is performing mode-reset cleanup while a kernel transition may need acknowledgement.

A robust repair should make the protocol invariant visible. Priority ordering is a strong first experiment and may be part of the final solution, but it should be tested against windows where controller teardown begins before userspace handles the signal.

## Cross-context review

| Context | Desired outcome |
|---|---|
| Normal logout, no pending switch | restore VT promptly |
| Greeter-to-session handoff with pending release | acknowledge release before restore |
| Controller crash/OOM | restore unless transition is pending; then resolve transition first |
| `vt_release()` failure | clear or retain state according to kernel outcome, never silently deadlock |
| Hung-up `vtfd` | reopen behavior remains valid |
| Legacy session sharing VT | preserve existing lookup and pause semantics |
| Session/seat removal | no stale pointer or permanently deferred restore |
| Repeated signal | acknowledgement remains idempotent enough for kernel behavior |
| Daemon restart | serialized state cannot falsely claim or forget a live kernel transition |
| Shutdown | cleanup must not leave a user locked on a VT |

Stop the candidate at VT lifecycle. Do not mix display-manager timeout changes or unrelated seat scheduling into the same patch.

## Evidence boundary

This is a source-supported race analysis and test plan. No VT ioctls, display manager, compositor, or kernel tracing were run in this round. It does not claim that any proposed candidate fixes the race.

## Next step

Create an exact-base systemd research branch and first test priority ordering as a diagnostic, not a presumed final fix. In parallel, determine whether pending transition state can be queried or must be represented by a combined ordering/state protocol. Retain both dispatch orders and exact ioctl traces.

## Authority

No upstream issue, pull request, comment, email, review, or other external interaction has been authorized or made.