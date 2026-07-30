# proxysolver child signal propagation

## In simple words

The ordinary exit-status repair for `proxysolver` correctly forwards child exit 7, but a child killed by SIGTERM produces `Popen.returncode == -15`. Passing `-15` to `SystemExit` wraps to shell status 241 instead of preserving termination by SIGTERM.

This follow-up restores the signal's default disposition, unblocks an inherited blocked mask for catchable signals, and signals the wrapper itself after stdout/dump files have closed.

## Canonical records

- Issue: #165
- Base repair: #133 / merged PR #134
- Imported source: `upstream/mmdebstrap/proxysolver`
- Base patch: `../mmdebstrap-proxysolver-exit-status/0001-propagate-solver-status.patch`
- Follow-up patch: `0001-reraise-solver-signals.patch`
- Regression: `tests/test_mmdebstrap_proxysolver_signal_status.py`

## Candidate

After waiting for the real solver:

```python
if returncode < 0:
    signum = -returncode
    if signum not in (signal.SIGKILL, signal.SIGSTOP):
        signal.signal(signum, signal.SIG_DFL)
        signal.pthread_sigmask(signal.SIG_UNBLOCK, {signum})
    os.kill(os.getpid(), signum)
if returncode != 0:
    raise SystemExit(returncode)
```

Catchable signals have their default disposition restored because Python ignores or handles some signals differently from a freshly executed child. They are also explicitly unblocked: a wrapper can inherit a blocked mask from its launcher, and `os.kill()` would otherwise only leave the signal pending before execution falls through to wrapped `SystemExit(-N)` behavior.

SIGKILL and SIGSTOP cannot have a handler installed or be blocked effectively, but can still be sent to the wrapper.

## Regression

A disposable Python fake solver writes one complete line, records its PID, flushes stdout, explicitly unblocks SIGTERM in the child, and terminates itself with SIGTERM.

The matrix requires:

- the canonical PR #134 source to exit normally with status 241;
- the repaired wrapper to return `-SIGTERM` to its Python parent, proving actual signal termination;
- the same repaired result when a launcher blocks SIGTERM before `exec`ing the wrapper;
- stdout and dump bytes to retain the flushed line in every case;
- ordinary exit 0 and 7 behavior to remain unchanged;
- every fake solver PID to be gone;
- both candidate files to compile.

The blocked-mask launcher is a separate process that calls `pthread_sigmask(SIG_BLOCK)` and then `execv()`s the wrapper, preserving the mask across exec. The fake solver unblocks SIGTERM before killing itself so the child still reports a true negative return code while the parent retains the adverse inherited state.

## Cleanup and safety

The test signals only fake solver/wrapper subprocesses created below `TemporaryDirectory`. It uses no APT transaction, package mutation, root privilege, external network, mount, or persistent file.

## Evidence boundary

Exact signal re-raising means the wrapper does not execute Python cleanup after `os.kill()`. The source deliberately places that action after both subprocess and dump context managers have closed. Signals caught or transformed by an outer supervisor remain outside this wrapper.

The candidate depends on POSIX `signal.pthread_sigmask`, which is appropriate for this Linux-specific helper.

## Disposition

Retain the focused follow-up. No Debian or external upstream contact is included or authorized.
