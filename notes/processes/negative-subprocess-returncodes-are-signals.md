# Negative subprocess return codes are signals

## In simple words

Python's `subprocess` uses negative return codes to mean that a child died from a signal. `-15` means SIGTERM; it is not an ordinary exit code that should be passed unchanged to `sys.exit()`.

## Stable rule

Interpret return codes by sign:

```python
if returncode < 0:
    signum = -returncode
    # preserve or deliberately translate signal termination
elif returncode > 0:
    raise SystemExit(returncode)
```

Calling `SystemExit(-15)` produces an ordinary process exit whose low eight bits are 241. That loses both the signal identity and conventional shell status 143.

## Choices

A wrapper can:

1. **Re-raise the signal exactly**: restore the default disposition and signal itself. A Python parent then observes `returncode == -signum` and POSIX wait status remains signaled.
2. **Map to `128 + signum`**: exit normally with the conventional shell number. This is simpler but `WIFSIGNALED` is false.

Choose deliberately and document it. Do not rely on modulo-256 truncation.

## Cleanup ordering

If exact re-raising is used, close files and finish required local cleanup before signaling the wrapper. Code after `os.kill(os.getpid(), signum)` is not a reliable cleanup path.

For catchable signals, restore `SIG_DFL` first because the Python runtime may ignore or handle signals such as SIGPIPE differently. Do not call `signal.signal()` for SIGKILL or SIGSTOP.

## Regression shape

- fake child writes and flushes output;
- child terminates itself by SIGTERM;
- wrapper output/dump bytes remain complete;
- wrapper is observed as signal-terminated, not exit 241;
- ordinary exit 0 and nonzero behavior remains unchanged;
- no child survives.

## Related record

- `investigations/mmdebstrap-proxysolver-signal-status/README.md`
- Issue #165
