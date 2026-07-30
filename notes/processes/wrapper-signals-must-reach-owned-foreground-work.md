# Wrapper signals must reach owned foreground work

## In simple words

A wrapper can install a signal trap and still fail to cancel its child. Many shells defer the trap while waiting for a foreground process. The wrapper eventually exits with a signal-derived status, but only after the child finishes on its own.

## Stable rule

When a wrapper claims cancellation ownership:

1. start the child in a way that gives the wrapper a PID;
2. wait for that PID explicitly;
3. on a wrapper signal, forward the signal to the child;
4. reap every owned child;
5. close or drain related pipes before deleting them;
6. clear stored PIDs after `wait`;
7. exit or re-raise rather than resuming later work.

A trap that only says `exit 143` does not forward TERM to a foreground child. A cleanup trap that kills only a sidecar process does not cancel the operation owner.

## Pipe and filter ordering

For a producer feeding a filter through a FIFO:

```text
signal producer
wait producer / close writer
let filter drain and flush
wait filter
remove FIFO
exit wrapper
```

Killing the filter at the same time as the producer can discard status bytes that the producer already wrote.

## Evidence checklist

A useful regression should distinguish:

- wrapper-only signal delivery;
- process-group delivery;
- child PID survival;
- sidecar/filter PID survival;
- flushed output preservation;
- exact wrapper status;
- cleanup of FIFO and temporary directories;
- ordinary child success and failure status precedence.

## Limits

Forwarding one signal does not guarantee prompt termination when the child ignores it. Forced escalation and descendant process-group ownership are separate policy decisions and should be documented explicitly.

## Related record

- `investigations/mmdebstrap-gpgvnoexpkeysig-signal/README.md`
- Issue #176
