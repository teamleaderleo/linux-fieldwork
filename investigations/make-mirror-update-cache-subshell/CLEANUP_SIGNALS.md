# Signals during update_cache cleanup

State: `landed — post-merge review complete`

## TL;DR

PR #286 established the worker baseline: worker-owned APT cleanup, parent-owned proxy cleanup, explicit INT/QUIT/TERM statuses, one finalizer, and ordinary or explicit-signal failure ahead of cleanup failure.

That finalizer initially reset handled signals to default before `cleanupapt` ran. A later signal could replace the selected result or interrupt cleanup. During ordinary EXIT cleanup, simply ignoring signals would create the opposite error: a new cancellation could disappear and success could be reported.

PR #324 landed the bounded successor. It records the first handled signal accepted during ordinary cleanup, ignores later handled signals after selection, completes cleanup once, and applies:

```text
existing ordinary or explicit-signal failure
> first signal recorded during ordinary cleanup
> cleanup failure
> success
```

PR #324 merged as `404540e46b35df682f1fc006bdadf837aafb1752` after successful synthetic merge-ref integration runs and complete four-file review.

## Explain like I'm five

A worker is putting away a temporary desk. The first repair stopped the worker correctly, but unlocked the stop buttons before the desk was clean. A second press could knock the worker over and replace the first stop reason.

The successor writes down the first stop request, disables later handled buttons, finishes bounded cleanup, and reports the strongest result. A new worker then runs to prove that no stale desk state remains.

## Exact landed identity

- landed baseline: PR #286, merge `782774b01002abf37878d834a54d0bbf8b226397`;
- baseline record refresh: PR #322, merge `9245dae2b7391b0f60b90c23ebdd1aca55aeb78c`;
- cleanup-time successor: PR #324;
- final PR head: `0906573b434710032f44807bfb5d6bb017a510f6`;
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

Historical PR #305 provided the original three successor blobs but replayed the squash-merged #286 files against `main`. The blobs were transferred into clean PR #324, and complete review added the rerun and precedence regression.

## Repair mechanism

Patch 0002 adds one subshell-local slot:

```sh
update_cache_cleanup_signal_status=0
```

The recorder keeps the first cleanup-time signal and ignores later handled signals:

```sh
record_update_cache_cleanup_signal() {
  if [ "$update_cache_cleanup_signal_status" -eq 0 ]; then
    update_cache_cleanup_signal_status=$1
  fi
  trap '' INT QUIT TERM
}
```

Ordinary completion or implicit EXIT installs recorder traps before clearing EXIT. An explicit signal handler stores its selected status and ignores later handled signals before entering the common finalizer. The finalizer performs bounded cleanup and then selects the result in the declared order.

The trap order closes two windows:

1. later handled signals cannot regain default terminating behavior during cleanup;
2. a newly accepted signal cannot arrive after cleanup but before result selection and silently change the outcome.

## Deterministic regressions

The first module applies patches 0001 and 0002 with zero fuzz and uses real `/bin/sh` plus a barrier inside `cleanupapt`.

It proves:

1. predecessor TERM then INT exits by SIGINT after cleanup `start` only and retains APT state;
2. predecessor ordinary cleanup plus TERM exits by SIGTERM after `start` only and retains APT state;
3. repaired explicit TERM then INT returns 143 and completes `start, end`;
4. repaired ordinary cleanup records INT 130, QUIT 131, or TERM 143 and ignores a later handled signal;
5. host failure 42 outranks a cleanup-time signal;
6. cleanup-time signal outranks cleanup failure 74;
7. repaired paths remove APT state and execute no later marker;
8. both patches apply with zero fuzz and the complete source passes `/bin/sh -n`;
9. recorder or ignore policy is installed before EXIT is cleared.

The second module preserves three contracts that complete review found missing from the first matrix:

- cleanup-time TERM followed by INT returns 143 and permits an immediate unsignalled status-0 rerun;
- explicit TERM remains 143 when cleanup also fails with 74 and later INT arrives;
- unsignalled successful work plus cleanup failure remains 74;
- each path logs one complete `start, end`, removes APT state, and omits later work;
- module reuse does not duplicate the original test class.

## Executed evidence and checkout identity

### Mechanism integration run

CI `30630113839` / 911 passed 303 repository tests and all eight cleanup-time/rerun controls.

The run did **not** check out literal head `d33871b6c05947384d1c235c653a40b57772d82d`. It checked out generated merge commit:

```text
708029227238d5078d1936579456355806ab3384
= merge(base e93b0353871dd29ebf9eda32245b2607f9572cc7,
        head d33871b6c05947384d1c235c653a40b57772d82d)
```

Classification: `synthetic-merge-ref`.

The run passed:

- changed-patch validation;
- Python compilation;
- 303 repository tests;
- five original cleanup-time controls;
- three rerun/precedence controls;
- existing #286 ownership, cleanup-failure, signal-matrix, and rerun controls;
- shell syntax and command-help checks.

### Final record-generation integration run

CI `30630467076` / 916 passed on generated merge commit:

```text
53a69677756ce1501e2c501663f15ba4eee6b5b4
= merge(base e93b0353871dd29ebf9eda32245b2607f9572cc7,
        head 0906573b434710032f44807bfb5d6bb017a510f6)
```

Classification: `synthetic-merge-ref`.

It passed changed-patch validation, compilation, repository tests, shell syntax, and command-help checks.

### Meaning of the correction

The old records called these “exact-head” gates. PR #344 later introduced strict head-versus-merge-ref classification and showed that the default `pull_request` checkout is a generated merge.

The correction narrows receipt wording:

- established: the #324 content integrated and executed successfully with base `e93b0353...`;
- retained: exact PR head, exact base, generated merge checkout, run, and outcome;
- not established: literal-head execution of the historical #324 heads.

The observed mechanism evidence remains valid because the patches and tests were present in the generated merge and the exact changed-file relation was recorded. The receipt should be called merge-ref integration evidence.

## Post-merge persistence

Current `main` retains the patch 0002 blob and both test blobs merged through #324. The later explicit unittest runner from PR #315 filters inherited methods only for named unrelated extension classes; neither #324 test class is filtered. The focused controls remain in repository discovery.

## Historical precedent

The same defect family was characterized in `run_qemu` lifecycle work:

- cleanup-only signal traps can resume later work;
- resetting handled signals to default can let a later signal replace the first result;
- ignoring signals during ordinary EXIT cleanup can make cancellation disappear;
- deterministic cleanup barriers distinguish these cases more reliably than sleeps.

Reusable notes:

- `notes/processes/signal-traps-must-terminate-after-cleanup.md`;
- `notes/processes/handled-signals-must-remain-stable-through-cleanup.md`;
- `notes/processes/signals-during-exit-cleanup-must-not-disappear.md`.

## Why this approach survived review

The design is the smallest mechanism satisfying the selected contexts:

- worker cleanup never signals the parent-owned proxy;
- ordinary EXIT and explicit signal paths stay separate;
- first accepted signal remains stable through bounded cleanup;
- predecessor and repaired cases use the same deterministic barrier;
- a fresh unsignalled run proves cleanup completion;
- imported source stays exact and patches compose with zero fuzz;
- process-group delivery and escalation remain separate questions.

## Evidence boundary

Established:

- real shell processes and owner-PID signals;
- INT/QUIT/TERM status selection;
- first-signal retention;
- work/signal/cleanup precedence;
- once-complete bounded cleanup;
- removed APT state and omitted later work;
- immediate clean rerun;
- current-base merge-ref integration.

Not established:

- literal-head CI for the historical PR heads;
- whole-process-group signal delivery during cleanup;
- a cleanup child receiving the same signal as the shell;
- group/session escape;
- HUP policy;
- TERM-resistant cleanup;
- timeout or TERM-to-KILL escalation;
- permanently blocking cleanup;
- full APT, network, mirror, or root integration;
- upstream or package acceptance.

The landed policy assumes cleanup is bounded and worth completing after the first handled signal is retained. A cleanup that can block indefinitely needs a distinct timeout and escalation design.

## Post-merge conclusion

The exhaustive post-merge review found no new source-visible defect inside the owner-PID, bounded-cleanup contract. It found and corrected two reader-facing issues:

1. #324 was still described as pending after merge;
2. runs 911 and 916 were called exact-head gates despite testing generated merge refs.

The process-group, blocking-cleanup, literal-head, and full-mirror boundaries remain useful follow-ups. They narrow the claim rather than invalidate the landed result.

## Authority

Internal Linux Fieldwork evidence and retained candidate patches only. External contact authorized: `false`.
