# Deep dive — `run_qemu.sh` result and cleanup precedence

## Original mechanism

The imported script used one function for `INT`, `TERM`, and `EXIT`:

```sh
trap cleanup INT TERM EXIT
```

That mixed five owners: host/QEMU/timeout status, guest/protocol status, explicit signal, signal during ordinary cleanup, and cleanup failure. Guest inspection could overwrite a host failure, signal identity was guest-dependent, and exiting from the signal handler could re-enter cleanup through the still-installed EXIT trap.

## Selected result order

```text
captured host failure
> completed guest or protocol failure
> first cleanup-time signal
> first cleanup failure
> success
```

This follows the point at which each result becomes authoritative: the host status is captured before cleanup; the guest result is complete before `debvm-run` returns; cleanup-time signals arrive later; cleanup failures occur while finalization runs.

## Patches 1–4 and their losing controls

### Patch 1 — preserve primary result

Introduces `finish()`, `cleanup_exit()`, and `cleanup_signal()`. It preserves host over guest over cleanup, retains the first cleanup failure, attempts later cleanup actions, and clears EXIT before finalization.

Losing control before patch 1: host timeout 124 plus guest failure returned 1.

Remaining loss after patch 1: TERM entered cleanup, then INT arrived after default signal behavior was restored; the shell died by SIGINT after only the first cleanup action.

### Patch 2 — retain first explicit signal

Changes later INT/TERM behavior during bounded cleanup from default to ignored. TERM then INT retains 143 and cleanup completes.

Remaining loss after patch 2: ordinary EXIT cleanup began without a selected signal and ignored a TERM received during cleanup, returning false success 0.

### Patch 3 — retain signal during ordinary cleanup

Adds `cleanup_signal_status` and a first-writer recorder. Ordinary EXIT cleanup installs recorder traps; finalization ignores later handled signals before result selection.

Remaining loss after patch 3: the recorded cleanup-time signal was selected before a guest failure that had already completed, so guest 1 plus later TERM returned 143.

### Patch 4 — preserve completed guest failure

Moves the recorded cleanup-time signal below the guest result. The four-commit order became host, guest, cleanup-time signal, cleanup failure, success.

## Complete-diff review of the four-commit candidate

The established focused tests exercised handler behavior after trap transitions were complete. The repository instructions require adjacent setup/cleanup review and a discriminator that can make the mechanism lose. Two handler-entry contexts could change the decision.

### Explicit signal-handler entry window

Four-commit code:

```sh
cleanup_signal() {
  rv=$1
  trap '' INT TERM
  trap - EXIT
  finish "$rv"
}
```

The assignment `rv=$1` is a separate shell command before INT and TERM become ignored. A widened deterministic fixture held execution after that assignment, sent TERM first, then INT, and released the handler. The re-entered handler replaced the first result:

```text
observed: 130
required: 143
```

Cleanup completed, so the distinguishing failure was first-signal ownership.

### Ordinary EXIT-handler entry window

Four-commit code:

```sh
cleanup_exit() {
  rv=$?
  trap 'record_cleanup_signal 130' INT
  trap 'record_cleanup_signal 143' TERM
  trap - EXIT
  finish "$rv"
}
```

The assignment `rv=$?` is a separate command before recorder traps are installed. A widened deterministic fixture completed guest failure 1, held execution after `rv=$?`, sent TERM, and released the handler. The old top-level TERM action entered explicit-signal cleanup and bypassed completed guest precedence:

```text
observed: 143
required: 1
```

Again cleanup completed; the loss was result ownership.

## Patch 5 — close handler setup windows

Selected commit:

```text
6efe6945f9f89cff57fe84086ede7bda747c3879
run_qemu: close signal-handler setup windows
```

### Ordinary cleanup phase becomes visible with status capture

```sh
cleanup_phase=running

cleanup_exit() {
  rv=$? cleanup_phase=exit
  ...
}
```

POSIX shell assignment-only command processing captures the incoming `$?` and marks the ordinary-cleanup phase in one command. There is no intervening command where the old signal action can enter without seeing `cleanup_phase=exit`.

### Signal trap actions disable overlap before handler entry

```sh
trap 'trap "" INT TERM; cleanup_signal 130' INT
trap 'trap "" INT TERM; cleanup_signal 143' TERM
```

The first command executed by the trap action disables both handled signals. `cleanup_signal()` no longer performs a vulnerable status assignment before trap replacement; it receives the literal selected status directly in `finish "$1"`.

Ordinary-cleanup recorder actions use the same transition:

```sh
trap 'trap "" INT TERM; record_cleanup_signal 130' INT
trap 'trap "" INT TERM; record_cleanup_signal 143' TERM
```

### Early signal through the old action rejoins ordinary cleanup

A signal can be selected for delivery immediately after `cleanup_phase=exit` becomes visible but before the recorder traps are installed. In that case the old action invokes `cleanup_signal()`, which now detects the phase:

```sh
if [ "$cleanup_phase" = exit ]; then
  record_cleanup_signal "$1"
  return
fi
```

The handler records the first cleanup-time signal and returns to `cleanup_exit()`. Ordinary cleanup continues, recorder traps are installed, and host/guest precedence remains intact.

### First-writer behavior survives trap reinstallation

`record_cleanup_signal()` still changes the slot only when it is zero. A deterministic fixture delivered early TERM through the old action, allowed ordinary recorder traps to install, then delivered INT during cleanup. The repaired result remained 143 and cleanup completed.

## Rejected repair shapes

### Set the phase only inside `cleanup_exit()` after capturing `$?`

This leaves the original between-command window intact.

### Put another ordinary assignment at the top of `cleanup_signal()`

A re-entering signal can overwrite shared shell variables before traps change. The repair must disable overlap in the trap action, before handler-body commands.

### Let nested signal handlers return naturally

Nested handlers can clobber global shell variables and resume an older frame with changed state. The selected explicit-signal trap action prevents nested handled-signal entry.

### Ignore all signals for the whole ordinary cleanup

That loses the first cleanup-time signal and can report success after cancellation.

### Make signal always win

That still replaces a completed host or guest failure with a later event.

### Squash all changes immediately

Each predecessor patch has a distinct losing control, and patch 5 exists because complete-diff review found a new transition class. The ordered series remains useful for review. A canonical-upstream rebase may reshape commits when required, but the five logical boundaries and controls must remain visible.

## Current evidence

Controlled mirror base:

```text
commit: 574048f2a720057b75e56622003932f344dc700a
run_qemu.sh blob: 426aeeb854173569b24e64d6eb85019f45bdf0b6
bytes: 2029
SHA-256: da89b51df80786f4e379b2ba5b033aab6c4e1d7acc8ba17cf57e67159a32e300
```

Five-commit candidate:

```text
head: 6efe6945f9f89cff57fe84086ede7bda747c3879
run_qemu.sh blob: 1fc816d6fe982351f6519fd1458329112eebdcfb
bytes: 3095
SHA-256: 434e7b6b9c32e30b506ea6af121608414c42b668c329e6395e75e19dc09ff276
/bin/sh -n: success
```

Executed reduced evidence:

- established lifecycle matrix: 58/58 pass;
- four-commit explicit setup window: TERM then INT returned 130, losing expected 143;
- repaired explicit setup window: returned 143, cleanup completed;
- four-commit EXIT setup window: guest 1 then TERM returned 143, losing expected 1;
- repaired EXIT setup window: returned 1, cleanup completed;
- repaired early TERM then later INT: returned 143, cleanup completed;
- immediate clean rerun: pass.

## Project-native boundary

mmdebstrap documents `make_mirror.sh` plus `coverage.sh`; individual cases use `coverage.py`. QEMU-classified cases execute `./run_qemu.sh`. This runtime did not have canonical Salsa access, prepared mirror images, or a disposable QEMU environment, so those authoritative integration gates remain unexecuted.

The new checked-in regression module is `tests/test_run_qemu_handler_setup_windows.py`. Equivalent fixtures executed during this pass; the exact module still needs a complete-checkout or hosted-CI run.

## Evidence limits and reopen triggers

Reopen or redesign when:

- canonical upstream changes handler structure or guest-result publication;
- the guest result is provisional when host cleanup starts;
- cleanup becomes unbounded and requires escalation;
- process-group delivery changes signal ownership;
- HUP or QUIT enter scope;
- current upstream already contains an equivalent or stronger mechanism;
- a real QEMU run exposes a different caller/child ownership contract.
