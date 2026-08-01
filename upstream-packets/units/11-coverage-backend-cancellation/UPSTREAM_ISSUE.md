# Proposed upstream issue draft

State: `DRAFT ONLY — DO NOT SEND WITHOUT EXPLICIT AUTHORIZATION`

## Title

`coverage.py` can leave the selected backend running after parent-only SIGINT

## Body

When SIGINT is delivered directly to `coverage.py` instead of the foreground process group, the current handler terminates only the immediate backend wrapper:

```python
proc = subprocess.Popen(argv)
try:
    proc.wait()
except KeyboardInterrupt:
    proc.terminate()
    proc.wait()
    break
```

Nested work behind `run_null.sh`, `run_null.sh SUDO`, or `run_qemu.sh` can remain alive after the wrapper receives TERM. The driver also reaches its ordinary epilogue after `break`, so a cancelled run can return status 0.

A status-only repair that exits 130 after terminating the wrapper fixes the false-success result while leaving the nested-backend survivor case intact.

The proposed repair gives each selected backend a dedicated session/process group, sends TERM to that group when the coverage parent receives SIGINT, waits for the wrapper, reports the interruption, and exits 130:

```python
proc = subprocess.Popen(argv, start_new_session=True)
try:
    proc.wait()
except KeyboardInterrupt:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    proc.wait()
    print("interrupted by SIGINT", file=sys.stderr)
    raise SystemExit(130)
```

Focused responsive-topology controls should cover:

- the imported baseline returning 0 while nested work survives;
- a status-only comparator returning 130 while nested work survives;
- the group candidate returning 130 with no surviving in-group work and no later-work marker;
- null, QEMU-wrapper, and sudo paths;
- ordinary unsignaled success;
- wrapper reap, temporary-state cleanup, and immediate rerun.

This issue would cover parent-only SIGINT and TERM-responsive work inside the selected backend group. TERM-resistant descendants, repeated SIGINT during cleanup, timeout/escalation policy, and descendants that create another session remain separate policy questions.

## Evidence to attach before sending

- exact current upstream base commit;
- zero-fuzz patch-application receipt;
- exact focused test command and output;
- candidate commit in a controlled fork;
- cleanup and rerun receipt.

No issue has been sent from this workspace.
