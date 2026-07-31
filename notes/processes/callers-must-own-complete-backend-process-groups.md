# Callers should own backend process-group signal boundaries

## In simple words

Waiting for one wrapper PID does not prove that every process started by the wrapper is gone.

When a caller launches a backend that creates nested shells, pipelines, log forwarders, helpers, or virtual machines, the caller needs an operation-wide signal boundary. Terminating only the immediate wrapper can return while descendants continue working.

A dedicated process group solves signal delivery. It does not automatically prove group quiescence.

## Why care

A supervisor can appear to finish cancellation while child work continues to:

- modify shared files;
- hold locks or pipes;
- run privileged commands;
- write output after the caller has moved on;
- interfere with the next test;
- become reparented and invisible to the original waiter.

Correct parent status, group-wide signal delivery, wrapper settlement, and complete operation quiescence are separate requirements.

## Useful signal-boundary pattern

For a Linux/POSIX backend launched from Python:

```python
proc = subprocess.Popen(argv, start_new_session=True)
```

This gives the backend invocation a dedicated session and process group whose ID is initially the wrapper PID.

On parent cancellation:

```python
try:
    os.killpg(proc.pid, signal.SIGTERM)
except ProcessLookupError:
    pass
proc.wait()
```

Then report the parent-visible cancellation status separately.

This pattern establishes caller-owned group-wide TERM delivery. It proves complete cleanup only when evidence also shows that every relevant descendant remains in the group and responds to TERM.

## Why isolate before signalling

Never send a process-group signal unless the caller knows the group is dedicated to the owned operation. Signalling an inherited foreground group can terminate the caller, unrelated helpers, or the controlling shell.

`start_new_session=True` establishes isolation before the child executable runs.

## Required comparisons

Retain at least three variants:

1. **baseline** — parent cancellation terminates one wrapper PID;
2. **status-only repair** — parent status is corrected while descendants remain outside caller cleanup;
3. **group-delivery repair** — parent status is correct and TERM reaches the dedicated operation group.

Check both:

- PID-targeted parent cancellation;
- normal foreground-group cancellation, which may already reach every descendant without a source change.

This prevents a repair from claiming a general interactive defect when the actual hole is supervisor-targeted delivery.

## Required process evidence

Record:

- wrapper PID and process-group ID;
- all group members before cancellation;
- live non-zombie members after wrapper settlement;
- reparenting to PID 1;
- later-work markers;
- cleanup of every retained process;
- transient zombie reaping;
- immediate unsignaled rerun.

A wrapper exit code alone is not process-lifecycle evidence.

## Quiescence and repeated-signal boundary

`proc.wait()` waits for the immediate child only. A descendant can ignore TERM, remain alive after the wrapper exits, or move to another group/session. A second parent signal can also interrupt the cleanup wait unless first-signal retention is designed explicitly.

Stronger claims require separate policy and tests for:

- descendant group liveness after wrapper settlement;
- TERM-resistant descendants;
- timeout and survivor diagnostics;
- repeated-signal handling;
- optional TERM-to-KILL escalation;
- group/session escape;
- remote supervisors or subreapers.

Do not infer complete quiescence from group-wide TERM delivery plus leader `wait()` alone.

## Compatibility boundary

Starting a backend in a new session changes direct terminal-signal delivery. The caller becomes responsible for translating its own cancellation into the backend group's chosen signal and final parent status.

Inherited terminal file-descriptor I/O may remain usable while direct controlling-terminal access such as `/dev/tty` changes. Test the actual backend.

## Working rule

> Own the signal boundary first; prove settlement and quiescence separately.
