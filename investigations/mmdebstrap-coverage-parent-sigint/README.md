# mmdebstrap coverage parent-only SIGINT status

## In simple words

The coverage driver catches Ctrl-C, terminates and reaps the current test child, then breaks out of the test loop. With no earlier failure, it exits 0 and reports a cancelled matrix as successful.

The local candidate exits 130 immediately after child cleanup and prints a focused interruption diagnostic.

## Canonical records

- issue: #141
- source: `upstream/mmdebstrap/coverage.py`
- imported blob: `9a522484aef05deae514a98e4b6adf5feb6c886d`
- candidate: `0001-fail-after-parent-sigint.patch`
- regression: `tests/test_mmdebstrap_coverage_parent_sigint.py`
- reusable note: `notes/processes/cancellation-cleanup-must-not-fall-through-to-success.md`

## Exact source boundary

The driver uses:

```python
proc = subprocess.Popen(argv)
try:
    proc.wait()
except KeyboardInterrupt:
    proc.terminate()
    proc.wait()
    break
```

The current child is cleaned, but no failure is recorded and no nonzero status is raised. The final epilogue exits 1 only when `failed` is nonempty.

## Negative control

The executable regression constructs a minimal disposable coverage suite around an exact copy of the imported driver:

- one generated test;
- a fake `run_null.sh` that execs the generated script;
- a small Python worker that records its PID, handles TERM, sleeps, and writes a success marker only after the sleep;
- fake successful `shellcheck` and `shfmt`;
- a dependency-free fake `debian.deb822` parser;
- required source/shared placeholders and release path.

After the worker records its PID, the test sends SIGINT only to the coverage parent PID.

The unmodified driver must:

- terminate and reap the worker;
- omit the worker success marker;
- stop before completing the matrix;
- return status 0.

That last result is the defect.

## Candidate

The retained source patch replaces `break` with:

```python
print("interrupted by SIGINT", file=sys.stderr)
raise SystemExit(130)
```

The current child is still terminated and waited before the exit. Status 130 is the conventional shell-visible `128 + SIGINT` result and avoids an unhandled Python traceback.

## Regression matrix

- imported driver, parent-only SIGINT: status 0 negative control;
- candidate, parent-only SIGINT: status 130 and focused diagnostic;
- both interrupted runs: worker PID gone and success marker absent;
- candidate without a signal: test completes, success marker exists, result is SUCCESS, driver exits 0;
- exact patch application and Python compilation run before scenarios;
- every suite lives under the test's `TemporaryDirectory`.

## Execution record

An earlier exact-head run failed before signal execution because the retained patch hunk targeted a stale line location. The patch was regenerated against the imported blob; that red run remains classified as patch-packaging evidence.

Exact head `b0b87f9f1b30816b21dddcb6c3657b5a75b2b7f9` passed Linux Fieldwork CI run `30556199982`. The focused log records all four required tests as passing:

```text
test_baseline_reports_parent_only_sigint_as_success ... ok
test_candidate_reports_parent_only_sigint_as_failure ... ok
test_candidate_source_has_explicit_sigint_exit ... ok
test_candidate_unsignaled_run_still_succeeds ... ok
```

The exact retained patch applied and compiled inside the test setup. Interrupted baseline and candidate runs left the worker PID gone and no completion marker; the immediate unsignaled candidate rerun returned 0 and produced `result: SUCCESS`.

## Severity

**Medium reliability, approximately 5/10.**

This is test orchestration rather than mmdebstrap runtime behavior, but CI and callers rely on the coverage driver status to distinguish a complete matrix from cancellation.

## Evidence limits

- The regression delivers SIGINT only to the coverage parent PID.
- Parent-only SIGTERM/SIGHUP, process-group delivery, QEMU backend cleanup, and grandchildren remain separate lifecycle boundaries.
- The candidate uses TERM for the immediate child exactly as the existing handler does; escalation after an uncooperative child is outside this focused patch.
- The minimal suite exercises the real main loop with controlled dependencies rather than the full Debian mirror matrix.

## Disposition

READY FOR FINAL HUMAN CHECK as an independent coverage-driver repair. No Debian or external upstream issue, patch, email, merge request, comment, or review is authorized or created.
