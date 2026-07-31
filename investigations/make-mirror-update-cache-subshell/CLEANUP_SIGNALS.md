# Signals during update_cache cleanup

State: `stacked repair prepared — exact-head execution pending`

## TL;DR

PR #286 correctly repairs ownership, result precedence, duplicate cleanup, and direct INT/QUIT/TERM handling before cleanup begins. Its finalizer still clears handled signals to their defaults before `cleanupapt` runs.

That leaves two cleanup-time conditions:

- after explicit TERM selects 143, a later INT/QUIT/TERM can replace the first result and interrupt cleanup;
- during ordinary success or implicit EXIT cleanup, the first INT/QUIT/TERM receives default termination instead of explicit 130/131/143 handling and can interrupt cleanup.

The stacked repair records the first signal that arrives during ordinary cleanup, ignores later handled signals after any signal is selected, completes bounded cleanup, and applies:

```text
existing ordinary or explicit-signal failure
> first signal recorded during ordinary cleanup
> cleanup failure
> success
```

## Explain like I'm five

The worker starts putting away its temporary APT desk. The first candidate unlocks all three stop buttons before the desk is clean. A button press can knock the worker over, or a second button can replace the first stop reason.

The repair writes down the first stop request, disables later stop buttons, finishes putting the desk away, and reports the most useful reason.

## Why care

A partial `cleanupapt` can leave state that changes the next mirror run. Replacing TERM 143 with a later signal also misclassifies why the worker stopped.

The predecessor evidence remains valid for signals delivered before cleanup. This is a distinct lifecycle boundary newly owned by the finalizer.

## Repair mechanism

`0002-retain-signals-through-cleanup.patch` adds one subshell-local status slot and recorder.

Ordinary completion and implicit EXIT install recorder traps before clearing EXIT. The first cleanup-time INT/QUIT/TERM records 130/131/143 and converts all three handled signals to ignore. Cleanup continues.

An explicit signal handler records its status and ignores handled signals before entering the common finalizer. A second signal therefore cannot replace the first selected result.

After cleanup, the finalizer ignores handled signals before evaluating precedence and exiting.

## Deterministic regression

`tests/test_make_mirror_update_cache_cleanup_signals.py` applies the PR #286 patch and optionally the stacked repair with zero fuzz, then uses real `/bin/sh` and a barrier inside `cleanupapt`.

Prepared controls require:

1. predecessor TERM then INT during cleanup exits by SIGINT after only cleanup `start` and retains APT state;
2. predecessor ordinary cleanup plus TERM exits by SIGTERM after only `start` and retains APT state;
3. repaired explicit TERM then INT returns 143 and completes `start, end` cleanup;
4. repaired ordinary cleanup records INT 130, QUIT 131, or TERM 143 and ignores a later handled signal;
5. existing host failure 42 outranks a cleanup-time TERM;
6. cleanup-time TERM outranks cleanup failure 74;
7. no later marker executes and APT state is removed on repaired paths;
8. both patches apply with zero fuzz and the complete source passes `/bin/sh -n`;
9. source order installs recorder or ignore policy before EXIT is cleared.

## Evidence boundary

The regression uses real shell processes, signals, disposable files, and a deterministic cleanup barrier. It does not run APT, network downloads, a mirror loop, root operations, or process-group delivery.

It assumes cleanup is bounded and should complete after the first handled signal. TERM-to-KILL escalation, HUP, hostile descendants, and a permanently blocking cleanup action remain outside the repair.

## Disposition

Execute exact-head repository CI, review the three-file stacked delta, then compose it into PR #286 only if the predecessor and repaired controls behave as stated.

Internal Linux Fieldwork work only. External contact authorized: `false`.
