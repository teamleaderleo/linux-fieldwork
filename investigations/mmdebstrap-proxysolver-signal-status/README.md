# proxysolver child signal propagation

## In simple words

The ordinary exit-status repair for `proxysolver` correctly forwards child exit 7, but a child killed by SIGTERM produces `Popen.returncode == -15`. Passing `-15` to `SystemExit` wraps to shell status 241 instead of preserving termination by SIGTERM.

This follow-up flushes retained stdout, restores the signal's default disposition, unblocks an inherited blocked mask for catchable signals, and signals the wrapper itself after stdout/dump files have closed.

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
    sys.stdout.flush()
    signum = -returncode
    if signum not in (signal.SIGKILL, signal.SIGSTOP):
        signal.signal(signum, signal.SIG_DFL)
        signal.pthread_sigmask(signal.SIG_UNBLOCK, {signum})
    os.kill(os.getpid(), signum)
if returncode != 0:
    raise SystemExit(returncode)
```

The explicit flush is required because the wrapper replaces normal interpreter shutdown with signal termination. Without it, stdout captured through a pipe can remain buffered even though the dump file has already closed cleanly.

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

## Execution record

The first exact-head CI run on `f57b43b32d78ad5dcd58039c816907fe7abe27de` stopped before signal semantics because the retained follow-up patch was malformed. That run is packaging evidence, not a product failure.

Helper G regenerated the patch against the canonical ordinary-status candidate and independently reconstructed the focused regression. The first corrected reconstruction exposed a second defect: exact self-signaling preserved `-SIGTERM` and dump bytes but lost buffered stdout. Adding `sys.stdout.flush()` before restoring and re-raising the signal made all four focused tests pass locally:

```text
python3 -m unittest -v tests/test_mmdebstrap_proxysolver_signal_status.py
Ran 4 tests in 9.206s
OK
```

Code-and-patch head `5209d881092f07f28759d77c5a82e768d9f87b76` then passed Linux Fieldwork CI run `30577241772`.

## Cleanup and safety

The test signals only fake solver/wrapper subprocesses created below `TemporaryDirectory`. It uses no APT transaction, package mutation, root privilege, external network, mount, or persistent file. The focused rerun leaves every fake solver PID gone and the temporary root is removed by `TemporaryDirectory` cleanup.

## Evidence boundary

Exact signal re-raising means the wrapper does not execute Python cleanup after `os.kill()`. The source deliberately places that action after both subprocess and dump context managers have closed and after stdout has been flushed. Signals caught or transformed by an outer supervisor remain outside this wrapper.

The candidate depends on POSIX `signal.pthread_sigmask`, which is appropriate for this Linux-specific helper. A broken stdout sink during the explicit flush remains an ordinary output-path failure boundary and is outside this focused child-signal regression.

## Disposition

READY FOR FINAL HUMAN CHECK as an independent follow-up after the ordinary-status repair. No Debian or external upstream contact is included or authorized.
