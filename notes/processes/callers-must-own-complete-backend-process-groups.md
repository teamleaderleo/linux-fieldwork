# Callers must own complete backend process groups

## In simple words

Waiting for one wrapper PID does not mean all work started by that wrapper is gone.

When a caller launches a backend that creates nested shells, pipelines, log forwarders, helpers, or virtual machines, the caller needs an operation-wide ownership boundary. Terminating only the immediate wrapper can return quickly while descendants keep running.

## Why care

A supervisor can appear to finish cancellation while child work continues to:

- modify shared files;
- hold locks or pipes;
- run privileged commands;
- write output after the caller has moved on;
- interfere with the next test;
- become reparented and invisible to the original waiter.

A correct parent status is necessary but not sufficient. The operation must also stop.

## Useful ownership pattern

For a Linux/POSIX backend launched from Python:

```python
proc = subprocess.Popen(argv, start_new_session=True)
```

This gives the backend operation a dedicated session and process group whose ID is the wrapper PID.

On parent cancellation:

```python
try:
    os.killpg(proc.pid, signal.SIGTERM)
except ProcessLookupError:
    pass
proc.wait()
```

Then report the parent-visible cancellation status separately.

## Why isolate before signalling

Never send a negative process-group signal unless the caller knows the group is dedicated to the owned operation. Signalling an inherited foreground group can terminate the caller, unrelated helpers, or the controlling shell.

`start_new_session=True` establishes that isolation before the child executable runs.

## Required comparisons

Retain at least three variants:

1. **baseline** — parent cancellation terminates one wrapper PID;
2. **status-only repair** — parent status is corrected but descendants are still not owned;
3. **group-owned repair** — parent status is correct and no live backend work remains.

Check both:

- PID-targeted parent cancellation;
- normal foreground-group cancellation, which may already reach every descendant without a source change.

This prevents a repair from claiming a general interactive defect when the actual hole is supervisor-targeted delivery.

## Required process evidence

Record:

- wrapper PID and process-group ID;
- all group members before cancellation;
- live non-zombie members after the wrapper returns;
- reparenting to PID 1;
- later-work markers;
- cleanup of every retained process;
- transient zombie reaping;
- immediate unsignaled rerun.

A wrapper exit code alone is not process-lifecycle evidence.

## Compatibility boundary

A process group does not contain descendants that deliberately create a new session or process group. TERM may also be ignored. Escalation, privileged descendants, remote helpers, and subreapers require separate policy.

Starting a backend in a new session also changes direct terminal-signal delivery. The caller becomes responsible for translating its own cancellation into the backend group's chosen signal and final parent status.

## Working rule

> Own the operation boundary, not merely the first PID returned by `Popen`.