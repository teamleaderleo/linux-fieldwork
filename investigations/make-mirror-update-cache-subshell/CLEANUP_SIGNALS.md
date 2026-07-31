# Signals during update_cache cleanup

State: `review complete — final record-only exact-head gate pending`

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

The complete four-file candidate passed exact-head Linux Fieldwork CI 911 at `d33871b6c05947384d1c235c653a40b57772d82d`. This record-only update preserves that receipt and requires one final unchanged-head gate before disposition.

## Explain like I'm five

The worker starts putting away its temporary APT desk. The landed baseline unlocks the stop buttons before the desk is clean. A button press can knock the worker over, or a second button can replace the first stop reason.

The successor writes down the first stop request, disables later stop buttons, finishes putting the desk away, and reports the strongest result. A separate rerun control then starts a fresh worker to prove that the first interrupted cleanup left no state behind.

## Why care

A partial `cleanupapt` can leave state that changes the next mirror run. Replacing TERM 143 with a later signal also misclassifies why the worker stopped.

The PR #286 evidence remains authoritative for signals delivered before cleanup. This record owns only the later boundary created by the finalizer itself.

## Exact current carrier

- landed baseline: PR #286, merge `782774b01002abf37878d834a54d0bbf8b226397`;
- canonical landed record refresh: PR #322, merge `9245dae2b7391b0f60b90c23ebdd1aca55aeb78c`;
- historical stacked successor: PR #305 at `0a6b9cc404bcc5e463964be7cbcf74d710528d86`;
- clean current-main carrier: PR #324;
- branch: `repair/make-mirror-update-cache-cleanup-signals-current-main`;
- reviewed executable head: `d33871b6c05947384d1c235c653a40b57772d82d`;
- reviewed base: `9245dae2b7391b0f60b90c23ebdd1aca55aeb78c`;
- relation at execution: six commits ahead, zero behind, merge base equal to current `main`;
- direct unit: this record, patch 0002, the focused cleanup-signal matrix, and the rerun/precedence matrix;
- imported source: unchanged;
- external contact: unauthorized and none.

PR #305 remains historical construction evidence. It replayed the squash-merged PR #286 files when compared to `main`; PR #324 transfers its three successor blobs and adds one review-driven regression.

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

## Executed evidence

Linux Fieldwork CI `30630113839` / 911 completed successfully on exact head `d33871b6c05947384d1c235c653a40b57772d82d`.

The hosted merge-ref gate established:

- changed-patch validation: one patch file and one hunk, valid;
- Python compilation: success;
- repository discovery: 303 tests in 161.326 seconds, success;
- shell syntax and command-help checks: success;
- the five original cleanup-time signal tests: all passed;
- the three review-driven rerun/precedence tests: all passed;
- existing PR #286 cleanup-failure, signal matrix, ownership, and rerun controls: all passed once under ordinary repository discovery.

The exact new tests proved:

- predecessor ordinary-cleanup TERM and explicit TERM-then-INT failure modes remain distinguishing controls;
- repaired INT/QUIT/TERM statuses are 130/131/143;
- later handled signals do not replace the selected result;
- host failure 42 remains ahead of a cleanup-time signal;
- cleanup-time signal remains ahead of cleanup failure 74;
- explicit TERM remains ahead of cleanup failure 74 and later INT;
- unsignaled cleanup failure remains 74;
- immediate unsignaled rerun succeeds after a cleanup-time signal;
- repaired cleanup completes once, removes APT state, and omits later work.

## Complete-diff review

The current direct unit contains four files and leaves imported `make_mirror.sh` unchanged. Review covered:

- first-signal recording and later-signal ignore policy;
- trap installation and EXIT-clearing order;
- ordinary, explicit-signal, cleanup-signal, and cleanup-failure precedence;
- zero-fuzz two-patch composition and complete `/bin/sh -n`;
- predecessor negative controls;
- immediate clean rerun;
- test process ownership, bounded waits, disposable state, and duplicate-discovery avoidance;
- exact current-main relation and evidence limits.

No remaining source-visible defect was identified in the bounded candidate.

## Evidence boundary

The regressions use real shell processes, signals, disposable files, and a deterministic cleanup barrier. They do not run APT, network downloads, a mirror loop, root operations, or process-group delivery.

They assume cleanup is bounded and should complete after the first handled signal. TERM-to-KILL escalation, HUP, hostile descendants, and permanently blocking cleanup remain outside the repair.

The attempted local clone for direct execution failed at DNS resolution before repository retrieval. That environment failure is not candidate evidence; hosted exact-head CI is the execution authority.

## Disposition

`READY FOR FINAL HUMAN CHECK` after one green unchanged-head gate for this record-only update.

The human decision is whether to merge this bounded internal evidence-and-patch carrier. It does not authorize or perform any upstream interaction.

Internal Linux Fieldwork work only. External contact authorized: `false`.
