# make_mirror update_cache subshell signal ownership

State: `landed — worker lifecycle and cleanup-time signal policy`

## TL;DR

`update_cache()` runs in a pipeline subshell while the top-level `make_mirror.sh` process owns the cache proxy. The imported source used one cleanup-only `EXIT INT TERM` trap in the worker. A worker-only signal could therefore kill the parent-owned proxy, run worker cleanup twice, resume later work, and report success after cancellation.

PR #286 landed the first lifecycle repair. It separated worker-owned APT cleanup from parent-owned proxy cleanup, gave INT/QUIT/TERM explicit statuses 130/131/143, routed ordinary completion and signals through one finalizer, and made an existing work or signal failure outrank cleanup failure.

PR #324 landed the second lifecycle repair. It covers signals arriving while bounded worker cleanup is already running: the first handled cleanup-time signal is retained, later handled signals are ignored, cleanup finishes once, and the final result follows an explicit precedence rule.

Together, the landed internal patch sequence establishes:

```text
existing ordinary or explicit-signal failure
> first signal recorded during ordinary cleanup
> cleanup failure
> success
```

The imported upstream source remains unchanged. Linux Fieldwork retains the two patches, deterministic real-`/bin/sh` regressions, exact execution receipts, and the evidence boundary for later upstream or packaging decisions.

## Explain like I'm five

A manager lends a robot to a worker. The manager owns the robot; the worker owns a temporary desk.

The old emergency button told the worker to clean the desk **and** switch off the manager's robot. It also forgot to stop the worker afterward. The worker could clean twice, switch off something it did not own, and continue working as though nobody had pressed stop.

The first repair gives each person one job: the worker cleans the desk, the manager switches off the robot, and a stop request becomes a clear result.

The second repair handles a stop request that arrives while the worker is already cleaning. The worker writes down the first stop request, ignores later presses of the same handled buttons, finishes the bounded cleanup, and reports the strongest result.

## Why care

This is a cancellation-integrity problem rather than cosmetic shell cleanup.

Without an explicit lifecycle policy:

- cancellation can become status 0;
- a worker can kill a process owned by its parent;
- cleanup can run twice after a failure;
- a second signal can replace the first cancellation reason;
- cleanup can stop halfway and leave state that changes the next run;
- a following run can inherit partial APT state or a stale proxy relationship;
- CI and supervisors can receive a misleading result.

The fixes also create a reusable distinction for the wider codebase: ordinary exit, explicit signal handling, and signals accepted during cleanup are separate lifecycle phases and need separate tests.

## Ecosystem position

`mmdebstrap` is an APT-based Debian bootstrap tool and test system. Its `make_mirror.sh` helper prepares local package mirrors and cache generations used by the project test suite. The script deliberately fills one cache generation and then switches a symlink atomically, so an interrupted run should not expose a half-published cache.

That publication design makes cleanup semantics important. `update_cache()` prepares temporary APT state below the new cache generation and is executed as the final command in a pipeline, so POSIX shell process and trap behavior directly affects whether cancellation is observed, whether cleanup completes, and which process owns the proxy.

The public Debian/mmdebstrap source generation retained in this repository still contains the original combined trap. Linux Fieldwork therefore keeps the imported source byte-for-byte and carries the candidate as reviewable patches rather than silently editing the upstream snapshot.

## Canonical landed sequence

### Parent lifecycle

- top-level proxy ownership and cleanup: PR #224;
- merge commit: `386f5c8dbb01e5de1af45ac0eb325ee8567722e3`.

### Worker lifecycle baseline

- owning issue: #231;
- canonical carrier: PR #286;
- reviewed head: `2c85afa8c947ff040b4c6d876d9b88cf545dbb59`;
- merge commit: `782774b01002abf37878d834a54d0bbf8b226397`;
- Linux Fieldwork CI: `30624335126` / 842, success;
- repository discovery: 249 tests, success;
- changed unit: five files;
- patch: `0001-confine-update-cache-signal-cleanup.patch`.

### Cleanup-time signal successor

- canonical carrier: PR #324;
- reviewed head: `0906573b434710032f44807bfb5d6bb017a510f6`;
- merge commit: `404540e46b35df682f1fc006bdadf837aafb1752`;
- executable mechanism gate: CI `30630113839` / 911, 303 tests, success;
- final exact-head gate: CI `30630467076` / 916, success;
- changed unit: four files;
- patch: `0002-retain-signals-through-cleanup.patch`.

The canonical baseline-record refresh landed through PR #322 as `9245dae2b7391b0f60b90c23ebdd1aca55aeb78c`.

Historical construction carriers #238, #259, #260, #267, and #305 are evidence history, not landing surfaces. Their unique bytes and findings were transferred into #286 or #324 before retirement.

## Imported failure shape

`update_cache()` is a subshell. It creates and owns `$rootdir`. The top-level process starts, records, stops, and waits for `$PROXYPID`.

The imported worker trap crossed that ownership boundary:

```sh
trap 'kill "$PROXYPID" || :;cleanupapt' EXIT INT TERM
```

It had four independent problems:

1. the worker signalled a proxy owned by the parent;
2. the signal trap performed cleanup but did not terminate explicitly;
3. ordinary success called `cleanupapt` before clearing EXIT, so cleanup failure could re-enter cleanup;
4. clearing handled signals to their defaults before cleanup opened a window where another signal could replace the selected result or interrupt cleanup.

## Landed mechanism

Patch 0001 introduces one finalizer and separates ordinary EXIT from explicit signals:

```sh
update_cache_finish() {
  status=$1
  trap - EXIT INT QUIT TERM
  cleanup_status=0
  cleanupapt || cleanup_status=$?
  if [ "$status" -ne 0 ]; then
    exit "$status"
  fi
  exit "$cleanup_status"
}
```

Patch 0002 adds a subshell-local cleanup-signal slot. During ordinary cleanup it installs recorder traps before clearing EXIT. During explicit-signal cleanup it records the selected status and ignores later handled signals before entering the finalizer. After cleanup it selects the final result in the declared order.

The key ordering is intentional:

- record or ignore INT/QUIT/TERM first;
- clear EXIT to prevent cleanup re-entry;
- run bounded cleanup once;
- ignore handled signals before reading the final state;
- return the strongest already-observed result.

## Why this approach

The chosen mechanism is narrow and compositional:

- it changes only the worker lifecycle;
- it preserves the parent as the sole proxy owner;
- it keeps the imported source unchanged;
- it represents cancellation with conventional shell statuses;
- it preserves ordinary work failure over cleanup noise;
- it preserves a cancellation accepted during ordinary cleanup rather than turning it into success;
- it finishes only a cleanup path already treated as bounded;
- it leaves process-group cancellation, escalation, and hostile descendants to separate investigations.

This follows the repository's evidence practice: isolate one lifecycle boundary, retain the losing implementation as a negative control, apply exact patches with zero fuzz, use deterministic barriers rather than timing guesses, and stop when adjacent contexts can no longer change the bounded decision.

## Alternatives considered

### Keep one combined cleanup trap

Rejected. A cleanup-only signal trap can return to the interrupted workflow, run cleanup again through EXIT, cross ownership boundaries, and hide cancellation.

### Reset every trap to default before cleanup

Rejected. A later handled signal can terminate the shell during cleanup, replace the first result, and leave partial state.

### Ignore handled signals for every cleanup entry

Rejected for ordinary EXIT cleanup. No signal has been selected yet, so ignoring the first cleanup-time signal can convert cancellation into success.

### Re-raise the original signal after cleanup

Useful in some wrappers when exact kernel signal identity or core-dump semantics is required. It was not selected for this bounded patch because the surrounding script and tests already use conventional `128 + signal` statuses, and the immediate need was explicit result precedence across ordinary, signal, and cleanup failures. A re-raise policy would still require the same cleanup-time recording and process-delivery analysis.

### Signal the whole process group or escalate TERM to KILL

A different and broader contract. It can improve descendant cancellation, but it changes which processes receive signals and requires timeout, survivor, and ownership policies. Those questions are tracked separately rather than folded into this worker-finalizer patch.

### Make cleanup permanently uninterruptible

Rejected as a general policy. Ignoring signals is appropriate here only for the bounded cleanup interval after a handled result has been retained. A cleanup routine that can block indefinitely needs an escalation or timeout design.

### Edit the imported source directly

Rejected by repository policy. The imported tree is retained as exact upstream evidence; candidate changes remain explicit patches with application and behavioral controls.

## Executed evidence

The combined regressions use real `/bin/sh`, real signals, process waits, disposable directories, exact patch application, and a deterministic barrier inside `cleanupapt`.

They demonstrate:

- imported worker-only TERM can return 0, execute later work, clean twice, and kill the parent-owned proxy;
- patch 0001 returns 130/131/143 and confines worker cleanup;
- ordinary failure 42 and explicit TERM 143 remain ahead of cleanup failure 74;
- successful work plus cleanup failure returns 74 after one cleanup;
- before patch 0002, TERM followed by INT during cleanup is replaced by SIGINT and cleanup remains partial;
- before patch 0002, TERM during ordinary cleanup terminates directly and leaves APT state;
- after patch 0002, INT/QUIT/TERM during ordinary cleanup return 130/131/143;
- the first handled signal remains authoritative over later handled signals;
- cleanup completes once, removes APT state, and executes no later marker;
- an immediate unsignalled rerun succeeds;
- both patches apply with zero fuzz and the complete transformed script passes `/bin/sh -n`;
- repository discovery executes the focused ownership cases once.

The later repository test-runner change in PR #315 does not filter either #324 test class. The landed test blobs remain unchanged on current `main`.

## Evidence boundary

Established for the reduced worker lifecycle:

- owner-only signals delivered to the shell process;
- INT, QUIT, and TERM status selection;
- ordinary, explicit-signal, cleanup-time signal, and cleanup-failure precedence;
- once-complete bounded cleanup;
- no later work;
- removed temporary APT state;
- immediate clean rerun;
- exact two-patch composition.

Not established:

- a complete APT or mirror run with the patches applied;
- signals sent to the whole foreground process group;
- cleanup commands that receive the same terminal signal as the shell;
- descendants that create another session or process group;
- TERM-resistant or hostile descendants;
- HUP policy;
- repeated escalation or TERM-to-KILL;
- permanently blocking cleanup;
- non-Linux or non-POSIX-shell portability beyond the executed Ubuntu `/bin/sh` environment;
- upstream acceptance or package integration.

The process-group distinction is especially important when presenting the result. This work proves a shell-owner lifecycle policy. It does not claim that every descendant topology is quiescent after terminal-style cancellation.

## Presentation and follow-up

A reader-facing explanation, decision history, alternative analysis, evidence map, anticipated questions, and suggested talk outline are retained in [`PRESENTATION_BRIEF.md`](PRESENTATION_BRIEF.md).

The cleanup-time mechanism and full execution receipt are retained in [`CLEANUP_SIGNALS.md`](CLEANUP_SIGNALS.md).

Further work should begin only with a new bounded question, such as process-group delivery during cleanup, escalation for a blocking cleanup, or a full disposable mirror integration. External contact remains a separate human decision.

## Authority

Internal Linux Fieldwork evidence and candidate patches only. External contact authorized: `false`.
