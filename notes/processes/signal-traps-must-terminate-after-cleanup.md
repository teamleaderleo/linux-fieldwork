# Signal traps must terminate after cleanup

## In simple words

A shell signal trap that only removes files or kills children does not automatically terminate the script. After the trap returns, the shell can resume the interrupted workflow.

## Stable rule

Separate ordinary exit cleanup from signal handling.

```sh
cleanup() {
    # idempotent resource cleanup
}

on_term() {
    trap - EXIT INT TERM
    cleanup
    exit 143
}

trap cleanup EXIT
trap 'on_term' TERM
```

Use the conventional `128 + signal` status or deliberately re-raise the signal after cleanup. Do not let a cleanup error replace the cancellation reason.

## Deferred traps matter

When a shell is waiting for a foreground child, it may defer its own trap until that child returns. If the signal was delivered only to the shell PID:

1. the foreground child can finish normally;
2. the shell runs the cleanup trap;
3. the trap returns;
4. the shell continues with the next command.

A process-group signal can look correct while a parent-only signal is swallowed. Test both delivery models.

## Child cleanup

Killing a child is not the same as reaping it.

A robust helper should:

- tolerate an already-exited child;
- signal a live child;
- call `wait` in both cases;
- clear the stored PID to avoid acting on a reused number;
- be idempotent because EXIT and signal paths can converge.

## Regression shape

A useful reduced harness should:

- start one long-lived child;
- write a ready marker;
- wait in a foreground command;
- receive a signal at the owner PID only;
- place a marker after the wait;
- assert the post-signal marker is absent;
- assert cleanup ran exactly once;
- assert signal-derived status;
- assert no child survives;
- run once without a signal as a clean control.

## Related record

- `investigations/make-mirror-signal-exit/README.md`
- Issue #157
