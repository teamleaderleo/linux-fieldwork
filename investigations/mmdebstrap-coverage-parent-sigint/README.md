# mmdebstrap coverage parent-only SIGINT status

## TL;DR

`coverage.py` used to catch Ctrl-C, terminate and reap the current child, then leave the test loop through `break`. With no earlier failure, the driver reached its normal epilogue and exited 0 even though the matrix had been cancelled.

The landed repair prints a focused interruption message and exits 130 after child cleanup. PR #204 merged the current-main restack as commit `23522b7f7d39ee3a237820e46168720edafb4d0a`.

## Explain like I'm five

The test runner stopped the test it was watching, skipped the rest of the tests, and still held up a green “finished” sign. The repair changes that sign to “stopped by Ctrl-C.”

## Why care

CI, scripts, and people use the driver status to decide whether the complete test matrix ran. Status 0 after cancellation can promote incomplete work as successful.

## Canonical records

- Issue: #141
- Historical development: PR #143
- Landed current-main carrier: PR #204
- Final source head: `b5efc8faf35c1da725a3b995a344fadc078ad5d2`
- Merge commit: `23522b7f7d39ee3a237820e46168720edafb4d0a`
- Source: `upstream/mmdebstrap/coverage.py`
- Imported blob: `9a522484aef05deae514a98e4b6adf5feb6c886d`
- Candidate patch: `0001-fail-after-parent-sigint.patch`
- Regression: `tests/test_mmdebstrap_coverage_parent_sigint.py`
- Reusable note: `notes/processes/cancellation-cleanup-must-not-fall-through-to-success.md`

## Observed defect

The imported driver uses:

```python
proc = subprocess.Popen(argv)
try:
    proc.wait()
except KeyboardInterrupt:
    proc.terminate()
    proc.wait()
    break
```

The child cleanup succeeds, while the driver records no failure and raises no nonzero result. The final epilogue exits 1 only when `failed` contains an entry.

## Landed change

The retained patch replaces `break` with:

```python
print("interrupted by SIGINT", file=sys.stderr)
raise SystemExit(130)
```

Child termination and reaping remain in the same order. Status 130 gives callers the conventional `128 + SIGINT` result without a Python traceback.

## Distinguishing regression

The regression builds a disposable minimal coverage suite around exact baseline and candidate copies. It supplies one long-running worker, fake successful formatting tools, a small Deb822 parser, required placeholders, and a fake `run_null.sh`.

After the worker records its PID, the test sends SIGINT only to the coverage parent PID. The matrix proves:

- baseline: worker terminated and reaped, completion marker absent, driver status 0;
- candidate: worker terminated and reaped, completion marker absent, focused diagnostic present, driver status 130;
- unsignaled candidate rerun: completion marker present, `result: SUCCESS`, driver status 0;
- retained patch application and Python compilation succeed before behavior tests;
- every fixture lives below `TemporaryDirectory`.

The baseline status 0 is the negative control that distinguishes the defect from ordinary child cleanup.

## Executed evidence

An early run stopped at a stale patch location. That result classified patch packaging and carried no SIGINT behavior claim.

The original repaired line passed focused CI during development. The clean current-main restack at head `b5efc8faf35c1da725a3b995a344fadc078ad5d2` passed Linux Fieldwork CI run `30579733315`. Execution carrier run `30579465025` also applied the exact four-file unit and ran the four-test matrix twice successfully.

Evidence classification:

- defect ownership and success epilogue: source-read;
- parent-only SIGINT, child reaping, marker absence, status, and rerun: model-executed through the real coverage main loop with controlled dependencies;
- repository compatibility: named Linux Fieldwork CI gate;
- full Debian mirror matrix: open integration boundary.

## Severity

Medium reliability, approximately 5/10. The affected component is test orchestration, and its exit status is the completion contract consumed by CI and callers.

## Evidence boundary

The regression delivers SIGINT only to the coverage parent PID. Parent-only SIGTERM and SIGHUP, process-group delivery, grandchildren, QEMU backend cleanup, and escalation after an uncooperative child remain separate questions.

The minimal suite exercises the real main loop with controlled dependencies. It skips the full Debian mirror and package matrix.

## Authority

Internal Linux Fieldwork result. External Debian or upstream contact remains unauthorized.

## Disposition

**MERGED LOCALLY.** Use PR #204 and merge commit `23522b7f7d39ee3a237820e46168720edafb4d0a` as the canonical landed result. Retain PR #143 as development and repair history.