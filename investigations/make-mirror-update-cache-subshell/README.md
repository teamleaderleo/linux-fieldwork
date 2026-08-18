# make_mirror update_cache subshell signal ownership

State: `landed — worker lifecycle and cleanup-time signal policy`

## TL;DR

`update_cache()` runs in a pipeline subshell while the top-level `make_mirror.sh` process owns the cache proxy. The imported source used one cleanup-only `EXIT INT TERM` trap in the worker. A worker-only signal could therefore kill the parent-owned proxy, run worker cleanup twice, resume later work, and report success after cancellation.

PR #286 landed the first repair: worker-owned APT cleanup, parent-owned proxy cleanup, explicit INT/QUIT/TERM statuses 130/131/143, one finalizer, once-only cleanup, and ordinary or explicit-signal failure ahead of cleanup failure.

PR #324 landed the cleanup-time successor: the first handled signal accepted during ordinary cleanup is retained, later handled signals are ignored, bounded cleanup completes once, and the final result follows:

```text
existing ordinary or explicit-signal failure
> first signal recorded during ordinary cleanup
> cleanup failure
> success
```

The imported upstream source remains unchanged. Linux Fieldwork retains two patches, real-`/bin/sh` regressions, merge-ref integration receipts, exact PR-head and merge identities, and the limits of the claim.

## Explain like I'm five

A manager lends a robot to a worker. The manager owns the robot; the worker owns a temporary desk.

The old emergency button told the worker to clean the desk **and** switch off the manager's robot. It also forgot to stop the worker afterward. The worker could clean twice, switch off something it did not own, and continue as though nobody pressed stop.

The first repair gives each person one job. The second repair handles a stop request that arrives while the worker is already cleaning: write down the first request, ignore later handled presses, finish bounded cleanup, and report the strongest result.

## Why care

This is cancellation integrity, not cosmetic shell tidying. Without an explicit lifecycle policy:

- cancellation can become status 0;
- a worker can kill a parent-owned process;
- cleanup can run twice;
- a second signal can replace the first cancellation reason;
- cleanup can stop halfway and alter the next run;
- CI and supervisors can receive a misleading result.

The reusable lesson is that ordinary exit, explicit signal handling, and a signal accepted during cleanup are different lifecycle phases.

## Ecosystem position

`mmdebstrap` is an APT-based Debian bootstrap tool. Its test suite uses `make_mirror.sh` to fill minimal local mirror caches before `coverage.sh` runs many bootstrap scenarios. The helper fills a new cache generation and switches publication only after it is ready, so interruption and cleanup directly affect reproducibility and rerun behavior.

`update_cache()` creates temporary APT state below the new cache and runs as the final command in a pipeline. Shell process ownership and trap timing therefore decide whether cancellation is visible, cleanup completes, and the correct process stops the proxy.

The public Debian/mmdebstrap source generation examined during the post-merge review still contains the original combined trap. Refresh that external fact before any public presentation or upstream decision.

## Canonical landed sequence

### Parent lifecycle

- top-level proxy ownership and cleanup: PR #224;
- merge: `386f5c8dbb01e5de1af45ac0eb325ee8567722e3`.

### Worker lifecycle baseline

- issue: #231;
- carrier: PR #286;
- reviewed PR head: `2c85afa8c947ff040b4c6d876d9b88cf545dbb59`;
- merge: `782774b01002abf37878d834a54d0bbf8b226397`;
- CI `30624335126` / 842: success;
- repository discovery: 249 tests;
- patch: `0001-confine-update-cache-signal-cleanup.patch`.

### Cleanup-time signal successor

- carrier: PR #324;
- final PR head: `0906573b434710032f44807bfb5d6bb017a510f6`;
- merge: `404540e46b35df682f1fc006bdadf837aafb1752`;
- executable mechanism integration: CI `30630113839` / 911, 303 tests, success;
- final record-generation integration: CI `30630467076` / 916, success;
- patch: `0002-retain-signals-through-cleanup.patch`;
- landed unit: four files.

PR #322 refreshed the baseline record and merged as `9245dae2b7391b0f60b90c23ebdd1aca55aeb78c`.

Historical carriers #238, #259, #260, #267, and #305 are construction history, not current landing surfaces.

## CI evidence identity correction

The repository previously described runs 911 and 916 as “exact-head” gates. Post-merge PR #344 established a strict distinction between a literal PR-head checkout and GitHub's generated pull-request merge ref.

The logs show that both #324 runs checked out synthetic merge refs:

| Run | Declared PR head | Tested checkout | Base parent | Classification |
| --- | --- | --- | --- | --- |
| CI 911 | `d33871b6c05947384d1c235c653a40b57772d82d` | `708029227238d5078d1936579456355806ab3384` | `e93b0353871dd29ebf9eda32245b2607f9572cc7` | synthetic merge ref |
| CI 916 | `0906573b434710032f44807bfb5d6bb017a510f6` | `53a69677756ce1501e2c501663f15ba4eee6b5b4` | `e93b0353871dd29ebf9eda32245b2607f9572cc7` | synthetic merge ref |

Those are valid current-base integration receipts. They are not literal-head execution receipts. The distinction changes the wording, not the observed test outcome:

- the PR-head patches and tests were present in the generated merge;
- the merge-ref integration passed;
- the exact PR head and base are retained;
- the final content later merged as `404540e4...`;
- current `main` retains the same patch and test blobs.

A future presentation should say “merge-ref integration gate” unless a literal-head checkout is separately recorded.

## Imported failure shape

The imported worker trap crossed ownership boundaries:

```sh
trap 'kill "$PROXYPID" || :;cleanupapt' EXIT INT TERM
```

It combined four independent defects:

1. the worker signalled the parent-owned proxy;
2. the signal trap cleaned but did not explicitly terminate;
3. ordinary success could enter cleanup again through EXIT after cleanup failure;
4. resetting handled signals to defaults before cleanup let a later signal replace the selected result or interrupt cleanup.

## Landed mechanism

Patch 0001 introduces one finalizer, separates EXIT from INT/QUIT/TERM, removes proxy signalling from the worker, and establishes:

```text
ordinary or explicit-signal failure > cleanup failure > success
```

Patch 0002 adds a subshell-local cleanup-signal slot. Ordinary cleanup installs first-signal recorders before clearing EXIT. Explicit-signal cleanup stores the chosen result and ignores later handled signals before entering the finalizer. After bounded cleanup, the finalizer returns the strongest recorded result.

The ordering is deliberate:

1. record or ignore INT/QUIT/TERM;
2. clear EXIT to prevent re-entry;
3. run bounded cleanup once;
4. ignore handled signals before reading final state;
5. return the strongest result.

## Why this approach

The selected mechanism is narrow and compositional:

- each process cleans only what it owns;
- the parent remains sole proxy owner;
- cancellation uses conventional shell statuses;
- primary work failure is not hidden by cleanup noise;
- cancellation during ordinary cleanup cannot become success;
- only an existing bounded cleanup interval is protected;
- process-group delivery and escalation stay separate questions;
- the imported source remains exact and candidates stay explicit patches.

This matches Linux Fieldwork practice: retain the losing variant, use deterministic barriers, apply exact patches with zero fuzz, state event-order precedence, and stop at a bounded claim.

## Alternatives considered

### Keep one combined trap

Rejected. It mixes ownership, can resume later work, can re-enter cleanup, and has no explicit result policy.

### Reset all traps to default before cleanup

Rejected. A later signal can replace the first result and leave cleanup partial.

### Ignore all handled signals whenever cleanup starts

Rejected for ordinary EXIT cleanup. No signal result exists yet, so cancellation can disappear and success can be reported.

### Re-raise the original signal

Potentially useful when direct signal identity or core-dump semantics is required. It still needs first-signal recording and cleanup ordering, and it changes the existing `128 + signal` interface. It was not selected for this bounded worker-status contract.

### Signal the process group or escalate TERM to KILL

A broader operation-ownership contract requiring safe group creation, waits, survivor diagnostics, timeout, and escalation policy. PR #313 and issue #341 own adjacent process-group questions.

### Make cleanup permanently uninterruptible

Rejected as a general rule. Ignoring later handled signals is justified only for the bounded cleanup interval after a result is retained. A potentially blocking cleanup needs timeout and escalation.

### Edit the imported source directly

Rejected by repository evidence policy. Exact imports and explicit patches preserve source identity and future upstream choices.

## Executed evidence

The regressions use real `/bin/sh`, signals sent to owned test processes, waits, disposable directories, exact patch application, and a deterministic barrier inside `cleanupapt`.

They show:

- the imported worker-only TERM can return 0, continue, clean twice, and kill the parent-owned proxy;
- patch 0001 returns 130/131/143 and confines cleanup ownership;
- work failure 42 and explicit TERM 143 outrank cleanup failure 74;
- successful work plus cleanup failure returns 74 after one cleanup;
- before patch 0002, TERM then INT during cleanup becomes SIGINT and leaves partial state;
- before patch 0002, TERM during ordinary cleanup directly terminates and leaves APT state;
- after patch 0002, ordinary-cleanup INT/QUIT/TERM return 130/131/143;
- the first handled signal remains authoritative;
- cleanup completes once, removes APT state, and omits later work;
- an immediate unsignalled rerun succeeds;
- patches 0001 and 0002 apply with zero fuzz;
- the transformed script passes `/bin/sh -n`;
- focused cases execute once under repository discovery.

The later unittest runner in PR #315 does not filter either #324 test class. Current `main` retains the landed patch and test blobs.

## Evidence boundary

Established for the executed Ubuntu `/bin/sh` reduction:

- owner-PID signals delivered to the shell process;
- INT, QUIT, and TERM result selection;
- ordinary, explicit-signal, cleanup-time signal, and cleanup-failure precedence;
- once-complete bounded cleanup;
- no later work;
- removed temporary APT state;
- immediate clean rerun;
- two-patch composition;
- current-base merge-ref integration.

Not established:

- a complete APT or mirror run with the patches;
- literal PR-head CI for the historical #324 heads;
- signals sent to the whole foreground process group;
- cleanup commands receiving the same terminal signal as the shell;
- descendants escaping the process group or session;
- TERM-resistant descendants;
- HUP policy;
- repeated escalation or TERM-to-KILL;
- permanently blocking cleanup;
- broad shell/platform portability;
- upstream acceptance or Debian package integration.

The process-group distinction is the most important spoken caveat. This work proves a shell-owner lifecycle policy, not complete descendant quiescence.

## Presentation and follow-up

- [`PRESENTATION_BRIEF.md`](PRESENTATION_BRIEF.md) contains the lay explanation, context, alternatives, evidence table, talk outline, and anticipated questions.
- [`CLEANUP_SIGNALS.md`](CLEANUP_SIGNALS.md) contains the cleanup-time mechanism and corrected execution identity.

New work should begin with a distinct bounded question: process-group delivery during cleanup, escalation for blocking cleanup, a literal-head audit, or a disposable full-mirror integration.

## Authority

Internal Linux Fieldwork evidence and candidate history only. External contact authorized: `false`.
