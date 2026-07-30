# proxysolver child signal propagation

## TL;DR

The ordinary-status repair made `proxysolver` forward child exit 7, while a solver killed by SIGTERM produced `Popen.returncode == -15`. Passing `-15` to `SystemExit` created ordinary exit 241 and erased the signal boundary.

The landed follow-up flushes stdout, closes the dump and subprocess contexts, restores and unblocks the signal, then signals the wrapper itself. PR #207 merged the current-main restack as `72f4d27aadf1863ee1b534d9751f3061c55b2ba4`.

## Explain like I'm five

The real solver was knocked over by SIGTERM, but its wrapper told everyone “I exited with number 241.” The repair makes the wrapper fall the same way as the solver after safely putting away its output.

## Why care

Supervisors, retry logic, cancellation reporting, and shell tooling distinguish signal termination from ordinary nonzero exit. Status 241 hides the reason the solver stopped and can trigger the wrong policy.

## Canonical records

- Issue: #165
- Ordinary-status prerequisite: issue #133 / merged PR #134
- Historical development: PR #166
- Landed current-main carrier: PR #207
- Final source head: `e4b16f5180e8bf67bf58621cac4447f4a4a55f44`
- Merge commit: `72f4d27aadf1863ee1b534d9751f3061c55b2ba4`
- Imported source: `upstream/mmdebstrap/proxysolver`
- Imported blob: `5cd51fab89104d30b8b12bff18a49d38d9be0003`
- Base patch: `../mmdebstrap-proxysolver-exit-status/0001-propagate-solver-status.patch`
- Follow-up patch: `0001-reraise-solver-signals.patch`
- Regression: `tests/test_mmdebstrap_proxysolver_signal_status.py`
- Reusable note: `notes/processes/negative-subprocess-returncodes-are-signals.md`

## Observed defect

Python reports a child killed by signal as a negative subprocess return code. SIGTERM becomes `-15`. The ordinary-status wrapper performed:

```python
if returncode != 0:
    raise SystemExit(returncode)
```

Unix process exit truncation converted `SystemExit(-15)` into ordinary status 241. The wrapper therefore lost both `WIFSIGNALED` semantics and the conventional shell-visible signal result.

## Landed change

After the solver and dump contexts close, the repair performs:

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

The stdout flush preserves bytes that normal interpreter shutdown would otherwise emit. Restoring `SIG_DFL` avoids Python-specific signal handling. Unblocking the inherited mask ensures self-signaling terminates the wrapper instead of leaving the signal pending. SIGKILL and SIGSTOP skip handler restoration because their dispositions cannot be changed.

## Distinguishing regression

A disposable fake solver records its PID, writes and flushes one complete line, and terminates itself with SIGTERM. The matrix proves:

- canonical ordinary-status source: wrapper exits normally with 241;
- repaired wrapper: Python parent observes `-SIGTERM`;
- repaired wrapper under an inherited blocked SIGTERM mask: parent still observes `-SIGTERM`;
- stdout and dump bytes remain complete and identical;
- ordinary solver exit 0 and 7 behavior remains unchanged;
- every fake solver PID is gone;
- exact source copies compile.

The blocked-mask launcher calls `pthread_sigmask(SIG_BLOCK)` and then `execv()`. The fake solver unblocks SIGTERM before self-termination, preserving a true negative child return code while the wrapper retains the adverse inherited mask.

## Executed evidence

The first retained follow-up patch was malformed, so its red run classified packaging. The first corrected implementation preserved signal identity and dump bytes but lost buffered stdout. Adding `sys.stdout.flush()` repaired that product defect.

The clean current-main restack at `e4b16f5180e8bf67bf58621cac4447f4a4a55f44` passed Linux Fieldwork CI run `30579889333`. Execution carrier run `30579465025` applied the exact four-file unit and ran the four-test matrix twice successfully.

Evidence classification:

- negative subprocess return-code interpretation and output ordering: source-read;
- exact SIGTERM re-raising, inherited-mask behavior, bytes, ordinary exits, and child cleanup: model-executed with real subprocesses and POSIX signals;
- repository compatibility: named Linux Fieldwork CI gate;
- real APT solver transaction and outer-supervisor policies: open integration boundary.

## Cleanup and safety

The regression signals only fake solver and wrapper subprocesses below `TemporaryDirectory`. It creates no APT transaction, package mutation, root operation, network request, mount, or persistent file. Every fake solver PID is gone before fixture cleanup.

## Evidence boundary

Exact self-signaling ends Python execution after `os.kill()`, so all required output closure and flushing occurs first. An outer supervisor may catch or transform the signal. The implementation depends on POSIX `signal.pthread_sigmask`, appropriate for this Linux helper. A broken stdout sink during the explicit flush remains an ordinary output-path failure.

## Authority

Internal Linux Fieldwork result. External Debian or upstream contact remains unauthorized.

## Disposition

**MERGED LOCALLY.** Use PR #207 and merge commit `72f4d27aadf1863ee1b534d9751f3061c55b2ba4` as the canonical result. Retain PR #166 as development and repair history.