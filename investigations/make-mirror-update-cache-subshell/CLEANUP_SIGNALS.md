# Signals during update_cache cleanup

State: `landed — post-merge review complete`

## TL;DR

PR #286 established the `update_cache()` worker baseline: worker-owned APT cleanup, parent-owned proxy cleanup, explicit INT/QUIT/TERM statuses, once-only cleanup, and ordinary or explicit-signal failure ahead of cleanup failure.

That finalizer initially restored handled signals to their default behavior before `cleanupapt` ran. Two cleanup-time conditions remained:

- after explicit TERM selected 143, a later handled signal could replace the first result and interrupt cleanup;
- during ordinary success or implicit EXIT cleanup, the first INT/QUIT/TERM could terminate the shell directly instead of becoming explicit status 130/131/143.

PR #324 landed the bounded successor. It records the first handled signal accepted during ordinary cleanup, ignores later handled signals after selection, completes cleanup once, and applies:

```text
existing ordinary or explicit-signal failure
> first signal recorded during ordinary cleanup
> cleanup failure
> success
```

PR #324 merged as `404540e46b35df682f1fc006bdadf837aafb1752` after two successful exact-head gates and complete four-file review.

## Explain like I'm five

A worker is putting away a temporary desk. The first repair stopped the worker correctly, but it unlocked the stop buttons before the desk was clean. A second button press could knock the worker over and replace the first stop reason.

The landed successor writes down the first stop request, disables later handled stop buttons, finishes the bounded cleanup, and reports the strongest result. A fresh worker is then started to prove that no stale desk state was left behind.

## Why care

A partial cleanup can alter the next mirror run. A replaced signal can also tell CI or a supervisor the wrong reason for cancellation.

The distinction is broader than this one function:

- explicit signal cleanup already has a selected signal result;
- ordinary EXIT cleanup does not;
- ignoring signals is safe for the first path only after the result is retained;
- ordinary cleanup must record the first accepted signal or cancellation can disappear.

## Exact landed identity

- landed baseline: PR #286, merge `782774b01002abf37878d834a54d0bbf8b226397`;
- baseline record refresh: PR #322, merge `9245dae2b7391b0f60b90c23ebdd1aca55aeb78c`;
- cleanup-time successor: PR #324;
- reviewed PR head: `0906573b434710032f44807bfb5d6bb017a510f6`;
- merge commit: `404540e46b35df682f1fc006bdadf837aafb1752`;
- historical stacked successor: closed PR #305 at `0a6b9cc404bcc5e463964be7cbcf74d710528d86`;
- imported source blob: `6c4be092edcf23b56b63a3befe238c099c45f590`;
- imported source changed: no;
- external contact: unauthorized and none.

## Four-file landed unit

1. `0002-retain-signals-through-cleanup.patch`;
2. this record;
3. `tests/test_make_mirror_update_cache_cleanup_signals.py`;
4. `tests/test_make_mirror_update_cache_cleanup_signals_rerun.py`.

The original three successor blobs came from historical PR #305. Its branch replayed the squash-merged PR #286 files against `main`, so the exact successor blobs were transferred into a clean current-main carrier. Complete review then added the fourth rerun and precedence regression.

## Repair mechanism

Patch 0002 adds one subshell-local status slot:

```sh
update_cache_cleanup_signal_status=0
```

The recorder keeps only the first cleanup-time signal and then ignores all three handled signals:

```sh
record_update_cache_cleanup_signal() {
  if [ "$update_cache_cleanup_signal_status" -eq 0 ]; then
    update_cache_cleanup_signal_status=$1
  fi
  trap '' INT QUIT TERM
}
```

Ordinary completion or implicit EXIT installs recorder traps before clearing EXIT. An explicit signal handler stores its selected status and ignores later handled signals before entering the common finalizer. The finalizer performs bounded cleanup, disables handled signals before result selection, and exits by the declared precedence.

The ordering closes two transient windows:

1. a second handled signal cannot regain default terminating behavior between trap changes;
2. a newly accepted signal cannot arrive after cleanup but before final result selection and silently change the outcome.

## Deterministic regressions

The first module applies patches 0001 and 0002 with zero fuzz and uses real `/bin/sh` plus a barrier inside `cleanupapt`.

Its controls prove:

1. predecessor TERM then INT exits by SIGINT after only cleanup `start` and retains APT state;
2. predecessor ordinary cleanup plus TERM exits by SIGTERM after only `start` and retains APT state;
3. repaired explicit TERM then INT returns 143 and completes `start, end` cleanup;
4. repaired ordinary cleanup records INT 130, QUIT 131, or TERM 143 and ignores a later handled signal;
5. host failure 42 outranks a cleanup-time signal;
6. cleanup-time signal outranks cleanup failure 74;
7. repaired paths remove APT state and execute no later marker;
8. both patches apply with zero fuzz and the complete source passes `/bin/sh -n`;
9. recorder or ignore policy is installed before EXIT is cleared.

The second module was added after complete review found three missing preservation controls. It proves:

- cleanup-time TERM followed by INT returns 143 and permits an immediate unsignalled status-0 rerun;
- explicit TERM remains 143 when cleanup also fails with 74 and a later INT arrives;
- unsignalled successful work plus cleanup failure remains 74;
- each path logs one complete `start, end` cleanup, removes APT state, and omits later work;
- helper-module reuse does not duplicate the original test class during ordinary discovery.

## Executed evidence

### Mechanism gate

Linux Fieldwork CI `30630113839` / 911 passed on executable head `d33871b6c05947384d1c235c653a40b57772d82d`:

- one changed patch and one hunk validated;
- Python compilation passed;
- 303 repository tests passed in 161.326 seconds;
- all five original cleanup-time signal tests passed;
- all three rerun and precedence tests passed;
- existing PR #286 ownership, cleanup-failure, signal-matrix, and rerun tests passed once;
- shell syntax and command-help checks passed.

### Final exact-head gate

Linux Fieldwork CI `30630467076` / 916 passed on PR head `0906573b434710032f44807bfb5d6bb017a510f6`:

- changed-patch validation passed;
- Python compilation passed;
- repository unit tests passed;
- shell syntax and command-help checks passed.

### Post-merge persistence pass

Current `main` retains the same patch 0002 blob and both test blobs that were merged through #324. The later explicit unittest runner introduced by PR #315 filters inherited methods only for three named extension classes; neither #324 test class is in that policy. The focused controls therefore remain part of current repository discovery.

## Historical precedent

This is the same defect family previously characterized in the `run_qemu` lifecycle work:

- a cleanup-only trap can resume later work;
- clearing handled signals to defaults before cleanup lets a later signal replace the first result;
- ignoring signals during ordinary EXIT cleanup can make cancellation disappear;
- deterministic cleanup barriers distinguish those cases more reliably than sleeps.

Reusable notes:

- `notes/processes/signal-traps-must-terminate-after-cleanup.md`;
- `notes/processes/handled-signals-must-remain-stable-through-cleanup.md`;
- `notes/processes/signals-during-exit-cleanup-must-not-disappear.md`.

## Why this approach survived review

The final design is the smallest mechanism that satisfies the selected contexts:

- ownership: worker cleanup never signals the parent-owned proxy;
- lifecycle: ordinary EXIT and explicit signal paths remain separate;
- ordering: first accepted signal remains stable through cleanup;
- evidence: predecessor and repaired cases use the same deterministic barrier;
- rerun: completed cleanup is verified by a fresh unsignalled execution;
- composition: imported source stays exact and both patches apply with zero fuzz;
- scope: process-group delivery and escalation remain separate questions.

## Evidence boundary

The regressions use real shell processes, owner-PID signals, disposable files, and deterministic barriers. They do not run APT, download a mirror, perform root operations, or execute the complete multi-architecture loop.

They do not establish:

- whole-process-group signal delivery during cleanup;
- behavior when a cleanup child receives the same signal as the shell;
- descendants that escape the group or session;
- HUP policy;
- TERM-resistant cleanup or TERM-to-KILL escalation;
- permanently blocking cleanup;
- upstream or Debian-package integration.

The landed policy assumes cleanup is bounded and worth completing after the first handled signal is retained. Any cleanup that can block indefinitely requires a distinct timeout and escalation design.

## Post-merge conclusion

The multi-pass post-merge review found no new source-visible defect inside the declared owner-PID, bounded-cleanup contract. It did find stale reader-facing state in this record and the parent README; the post-merge documentation repair updates both and adds a presentation brief.

The process-group and blocking-cleanup boundaries remain useful follow-up questions. They narrow the claim and do not invalidate the landed result.

## Authority

Internal Linux Fieldwork evidence and retained candidate patches only. External contact authorized: `false`.
