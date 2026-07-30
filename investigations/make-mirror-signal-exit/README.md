# make_mirror signal exit semantics

## In simple words

`make_mirror.sh` used cleanup-only traps for ordinary exit and for `INT`/`TERM`. A parent-only termination signal could therefore run cleanup and then resume the long mirror workflow instead of exiting with the signal-derived status.

This candidate separates normal exit cleanup from signal handling, closes both proxy launch/PID-registration intervals, stops and waits for either proxy child, tracks QEMU temporary cleanup separately, preserves a cache that has already become the active published cache, and exits with 130, 131, or 143 after cleanup.

## Canonical records

- Issues: #157 and launch-window follow-up #221
- Imported source: `upstream/mmdebstrap/make_mirror.sh`
- Candidate patch: `0001-preserve-signal-exit-status.patch`
- Regression: `tests/test_make_mirror_signal_exit.py`

## Source boundary

The source starts `caching_proxy.py`, stores its PID, and installs:

```sh
trap 'kill "$PROXYPID" || :' EXIT INT TERM
```

After readiness it changes that to:

```sh
trap 'kill "$PROXYPID" || :;cleanup_newcachedir' EXIT INT TERM
```

The QEMU path installs a third cleanup-only signal trap that also removes its temporary directory, then a fourth cleanup-only trap after normal QEMU completion. None of those signal actions exits or re-raises. Normal proxy stops also use raw `kill` without `wait` or clearing the stored PID.

## Candidate

The candidate introduces:

- `stop_proxy()`: signal the child if alive, `wait` for it even if already exited, and clear the PID;
- `cleanup_owner()`: call `stop_proxy()`, remove an active QEMU temporary directory when flagged, and remove the incomplete new cache only while it is still private;
- active-symlink inspection before cache deletion, so a cache already published through `shared/cache` survives a late signal;
- `signal_exit STATUS`: disable all traps, call `cleanup_owner()` once, and exit with the conventional signal-derived status;
- `launch_proxy()`: install temporary signal-recording traps, start the child, register `$!`, restore the terminating traps, and dispatch any signal recorded during registration;
- separate traps for `EXIT`, `INT`, `QUIT`, and `TERM`;
- reuse of `stop_proxy()` at both normal proxy-stop points;
- state flags that keep ordinary proxy shutdown and completed-QEMU cleanup separate from failed-cache deletion.

Separating child shutdown from cache cleanup is essential: normal successful mirror completion stops the first proxy before atomically switching the finished cache into place. Calling failure cleanup from that normal stop point would delete the result. Clearing `PROXYPID` is also required so a later EXIT path cannot act on a reused PID.

After publication, `readlink ./shared/cache` equals `$newcache`. Cleanup then clears its private-cache ownership flag and leaves the active cache intact. Before publication the symlink still identifies the old cache, so signal cleanup removes the incomplete new cache.

Cleanup errors are contained with `|| :` inside `cleanup_owner()`. This protects a signal-derived status, and it also deliberately preserves the primary command failure on ordinary EXIT paths instead of allowing a later cleanup failure to replace it. The tradeoff is that a failed cleanup can leave retained cache or temporary state while the original status is reported; retained cleanup evidence therefore remains part of review.

## Negative control and candidate matrix

The regression applies the patch to an exact temporary source copy and checks shell syntax. It then extracts the exact top-level trap/function block into reduced real `/bin/sh` harnesses.

A parent-PID-only `SIGTERM` is delivered while the shell waits for a foreground child:

- baseline post-readiness trap: cleanup runs, later work executes, EXIT cleanup runs a second time, and the owner exits 0;
- candidate: cleanup runs once, later work is absent, the owner exits 143, and the proxy child is reaped.

An unsignaled candidate rerun must finish 0, execute the later marker, stop and reap the proxy, and clean exactly once through the ordinary EXIT path.

A late-cleanup harness creates `shared/cache -> cache.B`, marks `cache.B` as the candidate's published cache, and invokes the exact cleanup function. The published directory must remain, failed-cache cleanup must stay uncalled, and ownership must transition to `CLEANUP_PROXY_CACHE=no`.

The source assertion requires all four top-level cleanup-only signal traps and all raw top-level `kill $PROXYPID` stops to disappear while leaving the unrelated subshell-local `update_cache()` trap outside this patch. It also requires QEMU temporary cleanup state and active-cache inspection.

Two deterministic launch-window controls instrument the exact `launch_proxy()` seam without changing its signal logic. Each control:

1. stops the owner after child creation and before `PROXYPID=$!`;
2. waits for the child executable to become ready;
3. sends TERM only to the stopped owner;
4. resumes the owner so the temporary trap records TERM;
5. requires PID registration, trap restoration, one cleanup, status 143, no later marker, and no surviving child;
6. immediately reruns the one-launch or two-launch path without a signal and requires status 0.

The second control completes and clears a first proxy before stopping at the second launch, reproducing the QEMU relaunch ownership state.

## Execution record

The first exact-head CI run `30557147115` exposed two regression-carrier defects: the candidate source tree collided with a runtime harness directory, and the source assertion exposed retained top-level QEMU trap text. A second run `30577299080` proved that malformed unified-diff hunk counts had caused GNU `patch` to accept an initial prefix while ignoring trailing hunks as garbage.

Helper G corrected every retained hunk count, separated source-tree and runtime paths, restored strong assertions for every top-level cleanup-only trap, and reran the exact patch. Linux Fieldwork CI run `30577821799` passed that repaired carrier.

Complete-diff review then found a product lifecycle gap after atomic cache publication: the cleanup flag still owned the new cache until final trap removal. The candidate now checks the active cache symlink before deletion and includes a focused post-publication preservation test.

Code-and-test head `113558f6a211196aff0973e941013ec034079bad` passed Linux Fieldwork CI run `30578032937`. The gate covers exact patch application, complete shell syntax, parent-only SIGTERM status 143, one cleanup, proxy reaping, omitted later work, unsignaled status-0 rerun, removal of every top-level cleanup-only trap, and published-cache preservation.

Follow-up #221 found that both launches still used a raw asynchronous command followed by a separate `PROXYPID=$!` assignment. A signal accepted between those commands could run cleanup before the new child was owned. The retained patch now routes both launches through `launch_proxy()` and the focused suite includes the two stopped-owner controls above. The current exact-head hosted receipt is pending.

## Cleanup and safety

The dynamic harnesses use only disposable directories, symlinks, and `sleep` children. They send signals only to subprocesses they created, wait for every owner, and check that the candidate proxy PID no longer exists. No mirror, APT operation, network, root privilege, package mutation, or persistent cache is used.

## Evidence boundary

The reduced harness proves top-level shell semantics, proxy ownership, private-cache deletion, and active-cache preservation without running the multi-hour mirror build. The full script has an additional subshell-local trap inside `update_cache()`; that remains separate because it runs in pipeline/subshell scope and needs its own process-map review.

Signal-derived exit codes follow the conventional `128 + signal` mapping. This candidate does not attempt to re-raise the original signal at the kernel level. Parent-only delivery can remain deferred while the shell waits for an unrelated foreground command, and no escalation policy is added for a proxy that ignores TERM.

## Disposition

HOLD for complete current-main review and the exact-head hosted receipt. No Debian or external upstream contact is included or authorized.
