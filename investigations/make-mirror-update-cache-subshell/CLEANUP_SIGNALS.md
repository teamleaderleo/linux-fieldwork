# Signals during update_cache cleanup

State: `current-main restack — exact-head gate pending`

## TL;DR

The landed `update_cache()` lifecycle repair owns the APT root, preserves ordinary and explicit-signal status, and cleans once. Its common finalizer still restored default INT/QUIT/TERM behavior before `cleanupapt`, so a first signal during ordinary cleanup could interrupt cleanup and a second signal could replace an already selected result.

PR #330 is the current carrier for the reviewed second patch. It records the first cleanup-time signal, ignores later handled signals after any signal is selected, completes bounded cleanup, and applies:

```text
existing ordinary or explicit-signal failure
> first signal recorded during ordinary cleanup
> cleanup failure
> success
```

## Explain like I'm five

The worker begins putting away its temporary APT desk. The landed baseline unlocks the stop buttons too early. A button press can knock the worker over, or a second button can replace the first stop reason.

The second patch writes down the first stop request, disables later stop buttons, finishes putting the desk away, and reports the strongest result.

## Why care

Partial cleanup can leave state that changes the next mirror run. Replacing TERM 143 with a later signal also misclassifies why the worker stopped.

## Current carrier

- landed baseline patch: `0001-confine-update-cache-signal-cleanup.patch` on `main`;
- current successor: PR #330;
- branch: `restack/make-mirror-cleanup-signals-main-v2`;
- technical predecessor: PR #324 exact head `0906573b434710032f44807bfb5d6bb017a510f6`;
- historical stacked construction: closed PR #305;
- direct unit: this record, patch 0002, focused cleanup-signal matrix, and rerun/precedence matrix;
- imported `make_mirror.sh`: unchanged;
- external contact: unauthorized and none.

The moving exact head and gate state belong in PR #330 rather than this commit, so the durable record does not become stale merely by recording its own update.

## Repair mechanism

`0002-retain-signals-through-cleanup.patch` adds one subshell-local status slot and recorder.

Ordinary completion and implicit EXIT install recorder traps before clearing EXIT. The first cleanup-time INT/QUIT/TERM records 130/131/143 and converts all three handled signals to ignore. Cleanup continues.

An explicit signal handler records its status and ignores handled signals before entering the common finalizer. A second signal therefore cannot replace the first selected result.

After cleanup, the finalizer ignores handled signals before evaluating precedence and exiting.

## Cross-context review

The current-main review sampled these adjacent contexts:

- **ordinary completion versus implicit EXIT** — both enter the same finalizer and preserve incoming status;
- **explicit signal versus cleanup-time signal** — explicit status remains authoritative, while ordinary cleanup records the first later signal;
- **signal versus cleanup failure** — existing ordinary or explicit failure wins; otherwise signal wins; otherwise cleanup failure wins;
- **trap lifecycle** — recorder or ignore policy is installed before EXIT is cleared and before bounded cleanup runs;
- **rerun state** — signaled cleanup removes APT state and an immediate unsignaled run returns 0;
- **evidence composition** — both retained patches apply with zero fuzz and the complete shell passes syntax validation;
- **test discovery** — the rerun module imports the helper module and initializes its fixture explicitly instead of inheriting duplicate tests.

No adjacent context changed the selected mechanism. APT execution, process-group delivery, hostile descendants, unbounded cleanup, HUP, and escalation remain separate boundaries.

## Deterministic regressions

`tests/test_make_mirror_update_cache_cleanup_signals.py` uses real `/bin/sh` and a barrier inside `cleanupapt` to prove:

1. the predecessor lets a later signal replace explicit TERM and interrupt cleanup;
2. the predecessor lets the first signal terminate ordinary cleanup by default;
3. the repair returns explicit TERM 143 and completes cleanup despite later INT;
4. ordinary cleanup records INT 130, QUIT 131, or TERM 143 and ignores a later handled signal;
5. host failure 42 remains ahead of cleanup-time TERM;
6. cleanup-time TERM remains ahead of cleanup failure 74;
7. APT state is removed and later work does not execute;
8. both patches compose with zero fuzz and the complete source passes `/bin/sh -n`.

`tests/test_make_mirror_update_cache_cleanup_signals_rerun.py` preserves three surrounding lifecycle contracts:

- cleanup-time TERM followed by INT returns 143 and permits an immediate clean rerun;
- explicit TERM remains 143 when cleanup also fails with 74;
- unsignaled successful work plus cleanup failure remains 74.

## Preserved evidence

PR #324 passed Linux Fieldwork CI on exact executable head `d33871b6c05947384d1c235c653a40b57772d82d` and again after its record update at `0906573b434710032f44807bfb5d6bb017a510f6`.

Those runs established the mechanism and four-file test boundary on their exact generations. PR #330 requires its own fresh exact-head gate because main has since gained additional repository instructions and evidence tooling.

## Evidence boundary

The regressions use synthetic real shell processes, signals, disposable files, and a deterministic cleanup barrier. They do not run APT, network downloads, the full mirror loop, root operations, process-group delivery, HUP, escalation, hostile descendants, or permanently blocking cleanup.

## Disposition

`HOLD FOR PR #330 EXACT-HEAD CI AND COMPLETE FOUR-FILE REVIEW`.

If the exact head passes unchanged and the direct diff remains the four declared files, the internal carrier is ready to land. No upstream interaction is authorized or included.
