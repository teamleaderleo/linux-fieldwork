# Signals during update_cache cleanup

State: `current-main successor — exact-head execution pending`

## TL;DR

PR #286 landed the `update_cache()` ownership, direct-signal, result-precedence, and once-only cleanup baseline. Its finalizer still clears handled signals to their default behavior before `cleanupapt` runs.

That leaves two cleanup-time conditions:

- after explicit TERM selects 143, a later INT/QUIT/TERM can replace the first result and interrupt cleanup;
- during ordinary success or implicit EXIT cleanup, the first INT/QUIT/TERM receives default termination instead of explicit 130/131/143 handling and can interrupt cleanup.

PR #324 is the clean current-main successor. It records the first signal that arrives during ordinary cleanup, ignores later handled signals after any signal is selected, completes bounded cleanup, and applies:

```text
existing ordinary or explicit-signal failure
> first signal recorded during ordinary cleanup
> cleanup failure
> success
```

## Explain like I'm five

The worker starts putting away its temporary APT desk. The landed baseline unlocks the stop buttons before the desk is clean. A button press can knock the worker over, or a second button can replace the first stop reason.

The successor writes down the first stop request, disables later stop buttons, finishes putting the desk away, and reports the strongest result. A separate rerun control then starts a fresh worker to prove that the first interrupted cleanup left no state behind.

## Why care

A partial `cleanupapt` can leave state that changes the next mirror run. Replacing TERM 143 with a later signal also misclassifies why the worker stopped.

The PR #286 evidence remains authoritative for signals delivered before cleanup. This record owns only the later boundary created by the finalizer itself.

## Exact current carrier

- landed baseline: PR #286, merge `782774b01002abf37878d834a54d0bbf8b226397`;
- historical stacked successor: PR #305 at `0a6b9cc404bcc5e463964be7cbcf74d710528d86`;
- clean current-main carrier: PR #324;
- branch: `repair/make-mirror-update-cache-cleanup-signals-current-main`;
- base: the PR #286 merge on `main`;
- direct unit: this record, patch 0002, the focused cleanup-signal matrix, and the rerun/precedence matrix;
- imported source: unchanged;
- external contact: unauthorized and none.

PR #305 remains historical construction evidence. It replayed the squashed PR #286 files when compared to `main`; PR #324 transfers its three successor blobs and adds one review-driven regression.

## Repair mechanism

`0002-retain-signals-through-cleanup.patch` adds one subshell-local status slot and recorder.

Ordinary completion and implicit EXIT install recorder traps before clearing EXIT. The first cleanup-time INT/QUIT/TERM records 130/131/143 and converts all three handled signals to ignore. Cleanup continues.

An explicit signal handler records its status and ignores handled signals before entering the common finalizer. A second signal therefore cannot replace the first selected result.

After cleanup, the finalizer ignores handled signals before evaluating precedence and exiting.

## Deterministic regressions

`tests/test_make_mirror_update_cache_cleanup_signals.py` applies the landed patch and this successor with zero fuzz, then uses real `/bin/sh` and a barrier inside `cleanupapt`.

Its controls require:

1. predecessor TERM then INT during cleanup exits by SIGINT after only cleanup `start` and retains APT state;
2. predecessor ordinary cleanup plus TERM exits by SIGTERM after only `start` and retains APT state;
3. repaired explicit TERM then INT returns 143 and completes `start, end` cleanup;
4. repaired ordinary cleanup records INT 130, QUIT 131, or TERM 143 and ignores a later handled signal;
5. existing host failure 42 outranks a cleanup-time TERM;
6. cleanup-time TERM outranks cleanup failure 74;
7. no later marker executes and APT state is removed on repaired paths;
8. both patches apply with zero fuzz and the complete source passes `/bin/sh -n`;
9. source order installs recorder or ignore policy before EXIT is cleared.

`tests/test_make_mirror_update_cache_cleanup_signals_rerun.py` was added during complete review because the first matrix did not independently preserve three landed lifecycle promises after patch 2 changed the finalizer. It requires:

- a cleanup-time TERM followed by INT returns 143, finishes cleanup, and permits an immediate unsignaled status-0 rerun;
- explicit TERM remains 143 when cleanup also fails with status 74 and a later INT arrives;
- unsignaled successful work plus cleanup failure still returns 74;
- all paths remove APT state, omit later work, and log one complete `start, end` cleanup.

The added module imports the existing test module rather than inheriting its `TestCase`, so repository discovery does not duplicate the original matrix. Its class setup initializes the shared exact-source fixture explicitly.

## Evidence boundary

The regressions use real shell processes, signals, disposable files, and a deterministic cleanup barrier. They do not run APT, network downloads, a mirror loop, root operations, or process-group delivery.

They assume cleanup is bounded and should complete after the first handled signal. TERM-to-KILL escalation, HUP, hostile descendants, and permanently blocking cleanup remain outside the repair.

The attempted local clone for direct execution failed at DNS resolution before repository retrieval. That environment failure is not candidate evidence; hosted exact-head CI remains the execution authority.

## Disposition

PR #324 must receive exact-head repository CI and complete four-file review. A green unchanged head may advance this bounded internal successor to final human check or local landing.

Internal Linux Fieldwork work only. External contact authorized: `false`.
