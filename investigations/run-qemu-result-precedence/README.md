# run_qemu result and signal precedence

State: `composed-repair — final exact-head CI pending`

## TL;DR

`run_qemu.sh` used the same cleanup function for `EXIT`, `INT`, and `TERM`. It could replace a specific host/QEMU failure with guest status 1, report INT/TERM as guest-dependent 0 or 1, and run cleanup twice through the still-installed EXIT trap.

The first candidate separated ordinary EXIT from explicit signal cleanup and retained the first cleanup failure. Review of that green candidate found another lifecycle defect: it restored default INT/TERM behavior before cleanup, so a second signal could replace the first signal result and interrupt cleanup.

The composed two-patch candidate applies:

```text
host or first handled signal failure > guest failure > first cleanup failure > success
```

Handled INT/TERM remain ignored while bounded cleanup runs. EXIT is cleared separately to prevent re-entry.

## Explain like I'm five

The wrapper can hear several bad reports at the end: the machine runner failed, the guest failed, someone pressed stop, or cleanup failed.

The old code let a later report cover an earlier, more useful one. The first repair remembered the result but unlocked the stop buttons while putting tools away. The composed repair keeps those buttons inactive until cleanup finishes, then reports the first useful result.

## Why care

Timeout 124, host failure 42, cancellation 130/143, guest failure 1, and cleanup failure identify different owners and recovery paths. Replacing one with another misclassifies the incident.

Running cleanup twice or interrupting it halfway can create secondary errors and leave temporary state behind.

## Canonical records

- issue: #269;
- pull request: #270;
- imported source: `upstream/mmdebstrap/run_qemu.sh`;
- source blob: `426aeeb854173569b24e64d6eb85019f45bdf0b6`;
- branch: `fix/run-qemu-result-precedence`;
- primary patch: `0001-preserve-primary-result.patch`;
- first-signal repair: `0002-retain-first-signal-through-cleanup.patch`;
- primary regression: `tests/test_run_qemu_result_precedence.py`;
- cleanup-precedence regression: `tests/test_run_qemu_cleanup_failure_precedence.py`;
- competing-signal regression: `tests/test_run_qemu_first_signal_cleanup.py`;
- focused repair record: `FIRST_SIGNAL_CLEANUP.md`;
- reusable notes:
  - `notes/processes/result-precedence-must-survive-exit-cleanup.md`;
  - `notes/processes/handled-signals-must-remain-stable-through-cleanup.md`.

## Source boundary

The imported source installs:

```sh
trap cleanup INT TERM EXIT
```

Its cleanup function captures `$?`, removes the temporary log and directory, reads `shared/exitstatus.txt` when `shared/output.txt` exists, and sets the result to 1 whenever the guest result is nonzero.

The main body separately captures the `timeout`/`debvm-run`/QEMU result in `ret` and executes `exit $ret`. The EXIT trap can replace that result.

## Executed baseline defects

| Condition | Guest result | Baseline final status | Defect |
| --- | --- | --- | --- |
| host 124 | nonzero | 1 | timeout identity lost |
| host 42 | missing status | 1 | result-read failure replaces host failure |
| INT | 0 | 0 | false success |
| TERM | 0 | 0 | false success |
| INT | nonzero | 1 | signal identity lost |
| TERM | nonzero | 1 | signal identity lost |

Baseline signal cleanup logs `rm, rmdir, rm`: the signal handler exits and invokes EXIT cleanup again.

## First candidate and review repair

The first patch introduces:

- `finish STATUS`, which reads the guest result safely, performs cleanup, and applies explicit precedence;
- separate ordinary EXIT and explicit INT 130 / TERM 143 handlers;
- first-cleanup-failure retention across `rm` and `rmdir`;
- once-only cleanup by clearing EXIT before `finish`.

Its predecessor handlers restored default INT/TERM behavior before cleanup. A deterministic review control sent TERM, waited for the first cleanup action, then sent INT:

```text
result: -2 (terminated by SIGINT)
cleanup log: rm
temporary directory: retained
later work: absent
```

The second patch changes handler preparation to:

```sh
trap '' INT TERM
trap - EXIT
```

The order is intentional: already-handled INT/TERM become ignored before EXIT is cleared, closing the intermediate default-signal window.

## Composed contract

- ordinary EXIT captures `$?` before cleanup;
- INT and TERM use explicit 130 and 143;
- handled INT/TERM remain ignored through bounded cleanup;
- EXIT is cleared before `finish`, preventing re-entry;
- an existing host or first handled signal nonzero result wins;
- otherwise guest nonzero, missing, unreadable, or malformed status becomes generic 1;
- otherwise the first cleanup failure becomes final;
- later cleanup actions still run but cannot replace that first cleanup failure;
- otherwise result is 0;
- no later work executes after handled cancellation;
- both patches apply with zero fuzz and the composed source passes `/bin/sh -n`.

## Executed evidence

Focused original discovery contained six unique tests and covered:

- host 0, 42, 124, and signal-like 143;
- guest success, nonzero, malformed, and missing status;
- distinct cleanup failures 74 and 75;
- host over guest and cleanup;
- guest over cleanup;
- first cleanup failure over later cleanup failure;
- explicit INT 130 and TERM 143;
- baseline false success and result overwrite;
- once-only cleanup and no later marker;
- patch application, shell syntax, and nonduplicating discovery.

The composed competing-signal module contains four tests and covers:

- zero-fuzz application of both patches;
- complete shell syntax;
- eleven composed precedence cases;
- deterministic predecessor TERM-to-INT failure;
- repaired result 143;
- complete `rm, rmdir` cleanup;
- removed temporary state and no later work;
- exact trap-source contract.

Receipts:

- predecessor head `14cb0e16014d0e4abe29ea5d2302abfb7ff7c299`: Linux Fieldwork CI `30597908319` / 787 passed;
- stacked repair head `643b81767cf3e1f2a1f9b3ff5d74363f12e02c4a`: CI `30622357399` / 806 passed;
- composed pre-refresh head `39a7fafcde48ee8efb99ce6829486327e51abbdb`: CI `30622514585` / 808 passed;
- current-main merge head `1b8f628b4fa55a178e3160c368ef7b88e5aaff2b`: CI `30622671969` / 810 passed.

The latest documentation alignment changes require one final exact-head run. A Python spreadsheet-runtime warmup diagnostic observed during local execution was unrelated to the test modules.

## Cleanup and safety

Dynamic tests use disposable directories and shell subprocesses. Signals target only the test shell PID. No QEMU, debvm, timeout workload, guest image, network, root privilege, or persistent shared directory is used.

Cleanup failures are captured rather than allowed to trigger implicit `set -e` replacement.

## Evidence boundary

The reduced matrices prove shell trap timing, result precedence, guest-status handling, once-only cleanup, first-cleanup-failure retention, competing handled-signal behavior, complete tested cleanup, and later-work suppression for the exact source shape.

They do not prove:

- full `debvm-run` or QEMU integration;
- every timeout and foreground-child signal topology;
- process-group delivery or escalation;
- background `tail -f` retirement beyond the existing `setpriv --pdeathsig TERM` design;
- HUP or QUIT policy;
- current public upstream source;
- cleanup behavior on unusual filesystems.

## Current disposition

`COMPOSED REPAIR — FINAL EXACT-HEAD CI AND NINE-FILE REVIEW`.

The branch is current with main and the direct candidate diff is nine added files. Land internally only after the documentation-aligned exact head passes Linux Fieldwork CI and a final complete review confirms the same file fence and boundaries.

Internal Linux Fieldwork work only. External contact authorized: `false`.
