# Wrappers must propagate child status, not just child output

## In simple words

A process wrapper can copy every byte correctly and still lie about success.

Waiting for a child only guarantees that it finished. The wrapper must inspect the return code and deliberately map failure into its own process contract.

## Failure pattern

```python
with subprocess.Popen(command, stdout=subprocess.PIPE, text=True) as child:
    for line in child.stdout:
        print(line, end="")
# wrapper exits 0 here
```

`Popen.__exit__()` waits, but it does not raise for a nonzero return code. If the child emits a partial protocol response and exits 7, the wrapper forwards the partial output and then exits 0.

That can move the visible failure downstream:

- the immediate process appears successful;
- a parser later reports malformed or incomplete data;
- retained logs point at the consumer instead of the producer;
- a dump file can look complete because the capture step itself passed.

## Safer sequence

```python
with subprocess.Popen(command, stdout=subprocess.PIPE, text=True) as child:
    for line in child.stdout:
        forward(line)
    returncode = child.wait()

if returncode != 0:
    raise SystemExit(returncode)
```

When output is also written to a file, close or flush that file before exiting so the retained evidence matches what was forwarded.

## Contract choices

A wrapper should choose and document one of these:

1. **Exact numeric propagation** — child 7 becomes wrapper 7.
2. **Signal propagation** — a signaled child causes the wrapper to terminate by the same signal.
3. **Stable wrapper failure code** — all child failures become one documented nonzero code.
4. **Protocol conversion** — the wrapper emits a complete protocol-level error and returns the status required by that protocol.

Doing nothing is not a contract; it is accidental status 0.

## Validation shape

Use a fake child that can select output and status independently:

- complete output, status 0;
- partial output, status 7;
- optionally no output, signal termination;
- write failure in the capture path.

Require stdout and retained dump equality, expected wrapper status, closed file descriptors, and no surviving child.

## Source and validation

This note was derived from issue #133 and `investigations/mmdebstrap-proxysolver-exit-status/README.md`. The executable regression is `tests/test_mmdebstrap_proxysolver_exit_status.py`.

No upstream contact is authorized or made by this note.
