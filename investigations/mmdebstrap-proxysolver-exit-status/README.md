# mmdebstrap proxysolver child-status propagation

## In simple words

`proxysolver` captures the real APT solver's output but always exits 0 after the child finishes. A solver that emits a partial response and exits 7 therefore looks successful to the caller.

The local candidate waits explicitly and returns the child's nonzero status while preserving stdout and dump bytes.

## Canonical records

- issue: #133
- source: `upstream/mmdebstrap/proxysolver`
- imported blob: `5cd51fab89104d30b8b12bff18a49d38d9be0003`
- candidate: `0001-propagate-solver-status.patch`
- regression: `tests/test_mmdebstrap_proxysolver_exit_status.py`
- reusable note: `notes/processes/wrappers-must-propagate-child-status.md`

## Exact source boundary

The wrapper opens `APT_EDSP_DUMP_FILENAME`, starts `/usr/lib/apt/solvers/apt`, forwards every stdout line to its own stdout, and writes the same line to the dump.

`Popen`'s context manager waits for the process on exit, but waiting and checking are separate responsibilities. The source never reads `p.returncode` and reaches normal Python end-of-file with status 0.

## Negative control

The regression copies the exact imported source into a disposable tree and replaces the two hard-coded solver path literals only in those temporary copies with a purpose-built fake solver.

The fake solver:

- consumes stdin;
- emits caller-selected output;
- exits with caller-selected status.

For a partial line plus status 7, the unmodified wrapper must reproduce:

```text
stdout: partial solver response
dump:   identical partial solver response
status: 0
```

That false success is the negative control.

## Candidate

The retained patch adds:

```python
returncode = p.wait()
...
if returncode != 0:
    raise SystemExit(returncode)
```

The wait occurs after stdout forwarding while the dump file remains open. The nonzero exit is raised after both context managers close, so stdout and dump contents remain identical and complete for everything the child emitted.

## Regression matrix

- successful fake solver, status 0: baseline and candidate both return 0;
- failing fake solver, status 7: baseline returns 0 and candidate returns 7;
- successful and failing stdout bytes equal their dump bytes in both versions;
- candidate source contains the explicit wait and status check;
- both temporary wrappers pass Python compilation;
- the fake solver and all dump files remain under `TemporaryDirectory` and no process survives `subprocess.run()`.

## Severity

**Medium correctness/reliability, approximately 5/10.**

The defect requires the underlying solver to fail, but the wrapper's purpose is faithful capture and forwarding. False success can turn a solver crash into a protocol parse failure, make a partial dump look complete, and obscure the first owning operation.

## Evidence limits

- The executable regression covers normal status 0 and explicit status 7.
- Signal-derived negative return codes are not re-raised as the same signal; exact signal propagation remains a possible follow-up.
- Dump-file creation and solver-exec diagnostics are unchanged by this focused patch.
- The real `/usr/lib/apt/solvers/apt` is not replaced or invoked by the test.

## Disposition

Retain the candidate and regression for internal review. No Debian or external upstream issue, patch, email, merge request, comment, or review is authorized or created.
