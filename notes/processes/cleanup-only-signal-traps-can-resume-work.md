# Cleanup-only signal traps can resume work

## In simple words

A shell trap does only what its action says. If a signal trap removes temporary files and returns, the shell can continue with the next command.

Cleanup is not termination.

## Stable rule

Use separate ordinary-exit and signal actions:

```sh
cleanup() {
    rm -rf -- "$workdir"
}

signal_exit() {
    status=$1
    trap - EXIT INT TERM
    cleanup || :
    exit "$status"
}

trap cleanup EXIT
trap 'signal_exit 130' INT
trap 'signal_exit 143' TERM
```

## Why foreground waits hide the bug

Shells commonly defer a trap while waiting for a foreground child or pipeline. With a signal delivered only to the wrapper PID:

1. the foreground operation can finish normally;
2. the wrapper runs cleanup;
3. cleanup returns;
4. later work resumes;
5. ordinary EXIT cleanup runs again;
6. the wrapper may report 0.

A process-group signal often looks better because the foreground child dies too. Test parent-only and group delivery separately.

## Cleanup errors

The signal path should preserve the cancellation reason. If cleanup fails under `set -e`, it can otherwise replace 143 with 1.

Contain cleanup errors in the signal action while deciding separately whether ordinary EXIT cleanup failures should remain visible.

## Limits

Exiting from the trap after the foreground command returns does not make cancellation prompt. Prompt parent-only cancellation requires the wrapper to own the foreground PID, forward the signal, and wait for every child. That can change stdin, job-control, or pipeline semantics and needs a process-map review.

## Related records

- `investigations/qemu-builder-signal-exit/README.md`
- `investigations/make-mirror-signal-exit/README.md`
- Issues #170 and #157
