# run_qemu result and signal precedence

State: `delivery-gate-ready`

## TL;DR

`run_qemu.sh` used the same cleanup function for `EXIT`, `INT`, and `TERM`. That function captured `$?`, removed temporary files, read a guest-written status file, and replaced the result with generic 1 whenever the guest status was nonzero.

The exact reduced matrix exposes three product defects:

1. a specific host/QEMU failure such as timeout 124 can be replaced by guest failure 1;
2. parent-only INT/TERM can be deferred and then return guest-dependent 0 or 1 instead of 130/143;
3. signal cleanup exits while the EXIT trap is still installed, so cleanup runs a second time.

Complete-diff review also caught one candidate defect before signoff: a later `rmdir` failure could replace an earlier `rm` failure. The repaired candidate retains the first cleanup failure.

The final precedence is:

```text
host or signal failure > guest failure > first cleanup failure > success
```

## Explain like I'm five

The wrapper can hear several bad reports at the end: the machine runner failed, the guest test failed, someone pressed stop, or cleanup failed.

The old code let the guest report or the last cleanup step cover up an earlier, more useful result. It could also hear “stop” and still say success.

The repair remembers the most important result first, cleans once, and reports that result.

## Why care

A timeout status 124, host failure 42, or cancellation status 130/143 identifies a different owner and recovery path from generic guest failure 1. Replacing it can misclassify infrastructure failure as a test failure, hide cancellation, and waste debugging time.

Running cleanup twice can produce secondary file errors. Letting the last cleanup failure replace the first also hides the operation that initially failed.

## Canonical records

- issue: #269;
- imported source: `upstream/mmdebstrap/run_qemu.sh`;
- source blob: `426aeeb854173569b24e64d6eb85019f45bdf0b6`;
- branch: `fix/run-qemu-result-precedence`;
- candidate patch: `0001-preserve-primary-result.patch`;
- primary regression: `tests/test_run_qemu_result_precedence.py`;
- cleanup-precedence regression: `tests/test_run_qemu_cleanup_failure_precedence.py`;
- reusable note: `notes/processes/result-precedence-must-survive-exit-cleanup.md`.

## Source boundary

The imported source installs:

```sh
trap cleanup INT TERM EXIT
```

Its cleanup function captures `$?`, removes the temporary log and directory, reads `shared/exitstatus.txt` when `shared/output.txt` exists, and sets the result to 1 whenever the guest result is nonzero.

The main body separately captures the `timeout`/`debvm-run`/QEMU result in `ret` and executes `exit $ret`. The EXIT trap can replace that result.

## Executed negative controls

The reduced harness embeds the exact cleanup function and trap from the imported source.

| Host or signal condition | Guest result | Baseline final status | Defect |
| --- | --- | --- | --- |
| host 124 | nonzero | 1 | timeout identity lost |
| host 42 | missing status file | 1 | result-read failure replaces host failure |
| INT | 0 | 0 | false success |
| TERM | 0 | 0 | false success |
| INT | nonzero | 1 | signal identity lost |
| TERM | nonzero | 1 | signal identity lost |

The signal baseline cleanup log is `rm, rmdir, rm`: the handler exits and invokes EXIT cleanup again.

## Candidate

The patch introduces:

- `finish STATUS`: reads the subordinate guest result safely, performs cleanup, and applies explicit precedence;
- `cleanup_exit()`: captures ordinary `$?`, clears EXIT/INT/TERM, then calls `finish`;
- `cleanup_signal STATUS`: receives explicit signal-derived status, clears EXIT/INT/TERM, then calls `finish`;
- separate EXIT, INT 130, and TERM 143 traps;
- first-cleanup-failure retention across both `rm` and `rmdir`.

Guest nonzero, missing, unreadable, or malformed status remains generic 1 when the host path is otherwise successful. This preserves the existing guest-failure contract while keeping a more specific host or signal result.

Cleanup failure becomes final only when host and guest outcomes are successful. If multiple cleanup actions fail, the first failure remains authoritative.

## Executed candidate matrix

Local command:

```text
python3 -m unittest -v \
  tests/test_run_qemu_result_precedence.py \
  tests/test_run_qemu_cleanup_failure_precedence.py
```

The final local suite contains six unique tests. It passed with process status 0. The latest primary four-test run completed in 2.971 seconds. A Python startup spreadsheet-runtime warmup diagnostic was unrelated to the test modules; every named unittest passed.

Covered cases:

- host 0, 42, 124, and signal-like 143;
- guest 0, nonzero, malformed, and missing;
- cleanup success and distinct `rm` 74 / `rmdir` 75 failures;
- host failure over guest and cleanup failures;
- guest failure over cleanup failures;
- first cleanup failure over later cleanup failure;
- INT 130 and TERM 143 with guest success and failure;
- baseline guest-dependent signal 0/1;
- candidate once-only cleanup;
- absent post-signal later marker;
- exact patch application and `/bin/sh -n` on the complete candidate source;
- module-qualified helper import so repository discovery does not duplicate the primary tests.

Candidate signal cleanup log is `rm, rmdir`.

## Complete precedence

| Primary host/signal | Guest channel | Cleanup | Final result |
| --- | --- | --- | --- |
| nonzero | any | any | primary host/signal status |
| 0 | failure, missing, unreadable, malformed | any | 1 |
| 0 | success | one or more failures | first cleanup failure |
| 0 | success | success | 0 |

## Cleanup and safety

The dynamic tests use disposable directories and shell subprocesses only. Signals target only the test shell PID. No QEMU, debvm, timeout workload, guest image, network, root privilege, or persistent shared directory is used.

The candidate clears traps before cleanup, preventing EXIT re-entry. Cleanup failures are captured rather than allowed to trigger implicit `set -e` replacement.

## Evidence boundary

The reduced matrix proves shell trap timing, status precedence, guest-status handling, once-only cleanup, first cleanup failure retention, and later-work suppression for the exact cleanup source shape.

It does not prove:

- full `debvm-run` or QEMU integration;
- timeout interaction with every signal topology;
- background `tail -f` retirement beyond the existing `setpriv --pdeathsig TERM` design;
- HUP or QUIT policy;
- current public upstream source;
- cleanup behavior on unusual filesystems.

## Current disposition

`delivery-gate-ready` / `EXECUTE` on a current-main five-file candidate. Promote only after:

1. exact-head Linux Fieldwork CI applies the retained patch to the complete imported source;
2. `/bin/sh -n` and both focused test modules pass without duplicate discovery;
3. repository discovery passes;
4. complete five-file review confirms precedence, cleanup, and evidence limits;
5. head/base remain current enough for internal landing.

Internal Linux Fieldwork work only. External contact authorized: `false`.
