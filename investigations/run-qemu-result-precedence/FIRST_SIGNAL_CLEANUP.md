# Retain the first handled signal through cleanup

State: `repair-complete — exact-head CI pending`

## TL;DR

PR #270 head `14cb0e16014d0e4abe29ea5d2302abfb7ff7c299` passed Linux Fieldwork CI run `30597908319` / 787, but a competing-signal review found a remaining lifecycle defect.

The first candidate clears `INT`, `TERM`, and `EXIT` to their defaults before cleanup. After TERM starts cleanup, a second INT can therefore terminate the shell, replace status 143 with signal 2, and leave cleanup only partly completed.

The focused repair ignores the already-handled INT and TERM while bounded cleanup runs, clears only EXIT to prevent re-entry, then returns the first retained result.

## Explain like I'm five

The wrapper hears “stop with TERM” and starts putting its tools away. The first repair unlocks both stop buttons before the tools are stored. Pressing INT during cleanup can knock the worker over and replace the first stop reason.

The repair keeps those two buttons inactive while cleanup finishes. The first stop request remains the answer.

## Why care

Signal identity tells a supervisor why the wrapper stopped. Partial cleanup can also leave temporary state behind and make the next run depend on an interrupted predecessor.

A green single-signal matrix did not cover this timing window. The new barrier places the second signal exactly after cleanup begins, so the distinction is deterministic rather than dependent on sleep timing.

## Predecessor negative control

The test composes only `0001-preserve-primary-result.patch`, then:

1. starts the wrapper model;
2. sends TERM;
3. waits for the cleanup `rm` function to publish `cleanup-ready`;
4. sends INT while cleanup is blocked;
5. records process result, cleanup log, temporary directory, and later-work marker.

Observed locally:

```text
result: -2 (terminated by SIGINT)
cleanup log: rm
temporary directory: retained
later work: absent
```

The predecessor preserved neither first-signal identity nor complete cleanup.

## Repair

`0002-retain-first-signal-through-cleanup.patch` changes both ordinary EXIT and explicit signal handlers from:

```sh
trap - INT TERM EXIT
```

to:

```sh
trap '' INT TERM
trap - EXIT
```

The order is intentional. INT and TERM become ignored before EXIT is cleared, so there is no intermediate window where a handled signal has default terminating behavior.

HUP and QUIT policy remain unchanged.

## Executed composed controls

Local command:

```text
python3 -m unittest -v tests/test_run_qemu_first_signal_cleanup.py
```

Result: four tests passed in 0.324 seconds with process status 0. A Python spreadsheet-runtime warmup diagnostic was unrelated to the test module.

The module proves:

- zero-fuzz application of both retained patches;
- complete `/bin/sh -n` on the composed source;
- host/signal, guest, first-cleanup-failure, and success precedence across eleven cases;
- the predecessor TERM-then-INT result of signal 2 with partial cleanup;
- the repaired TERM-then-INT result of 143 with `rm, rmdir` cleanup;
- no post-signal later marker;
- removal of the temporary directory;
- exactly two ignore rules for handled INT/TERM and two EXIT clear operations.

## Evidence boundary

The regression uses real `/bin/sh`, real process signals, a deterministic cleanup barrier, and disposable directories. It does not run QEMU, debvm, a guest image, network traffic, root operations, or the full wrapper workload.

It proves the first handled INT/TERM remains authoritative through the tested cleanup path. It does not define HUP/QUIT behavior, signal escalation, process-group delivery, or foreground-child cancellation.

## Disposition

The predecessor CI remains valid evidence for the original result-precedence repair, but it cannot clear this new lifecycle condition.

Required next gate:

1. exact-head Linux Fieldwork CI on the stacked repair;
2. complete review of the second patch, regression, and both records;
3. merge the repair into the PR #270 branch only after the unchanged head passes;
4. refresh PR #270 and issue #269 to the composed exact head and gate.

Internal Linux Fieldwork work only. External contact authorized: `false`.
