# Cancellation cleanup must not fall through to success

## In simple words

Cleaning up after a signal is not the same as completing successfully.

A handler can terminate children, remove temporary files, and leave no leaks while still returning the wrong status if control falls back into the normal success epilogue.

## Failure pattern

```python
try:
    child.wait()
except KeyboardInterrupt:
    child.terminate()
    child.wait()
    break

# later
if failures:
    raise SystemExit(1)
# accidental status 0
```

The local state may be clean, but the operation was not complete. CI sees green, remaining work is silently skipped, and retained summaries lack an owning cancellation result.

## Required cancellation contract

For each handled signal, decide explicitly:

1. which descendants receive a signal;
2. whether and how long the parent waits;
3. whether escalation is needed;
4. which files, mounts, locks, sockets, and temporary roots are cleaned;
5. what status the parent returns or whether it re-raises the signal;
6. what durable diagnostic distinguishes cancellation from ordinary failure.

Do not use `break`, `return`, or a cleared flag unless the subsequent path is guaranteed nonzero.

## Conventional SIGINT result

A command that handles Ctrl-C can exit cleanly with 130 (`128 + SIGINT`) after cleanup:

```python
except KeyboardInterrupt:
    child.terminate()
    child.wait()
    print("interrupted by SIGINT", file=sys.stderr)
    raise SystemExit(130)
```

Alternatively it can restore and re-raise SIGINT when exact signal identity is part of the CLI contract. The key is that cancellation cannot become status 0.

## Validation shape

Test more than process-group interruption. Supervisors often signal one PID.

A useful matrix includes:

- parent-only SIGINT;
- parent-only SIGTERM and SIGHUP;
- process-group delivery;
- child already exited;
- child ignoring the first signal;
- no success marker after interruption;
- child/grandchild process table empty;
- temporary state removed;
- immediate clean rerun;
- unsignaled success control.

Assert the exit status, not just the cleanup.

## Source and validation

This note was derived from issue #141 and `investigations/mmdebstrap-coverage-parent-sigint/README.md`. The executable regression is `tests/test_mmdebstrap_coverage_parent_sigint.py`.

No upstream contact is authorized or made by this note.
