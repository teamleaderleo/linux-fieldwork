# make_mirror signal exit semantics

## TL;DR

`make_mirror.sh` used cleanup-only signal traps. A parent-only signal could trigger cleanup, return to interrupted shell control flow, resume later mirror work, and finish with status 0.

The landed repair separates ordinary EXIT cleanup from INT, QUIT, and TERM termination, stops and reaps the proxy, preserves a cache already published through `shared/cache`, and clears temporary ownership. PR #205 merged the current-main restack as `69a16e988a37af957c4ba8eb5f2c36e396827fe4`.

## Explain like I'm five

The mirror builder heard “stop,” put away some tools, and then kept building. The repair makes it stop for real, waits for its helper to finish, and avoids throwing away a mirror that already reached the public shelf.

## Why care

A cancelled multi-hour mirror job could report success, leave child processes behind, delete the wrong cache state, or continue package and QEMU work after cleanup. Callers need one terminal status and one clear owner for private versus published cache data.

## Canonical records

- Issue: #157
- Historical development: PR #159
- Landed current-main carrier: PR #205
- Final source head: `ac2680e0dc92b497f6ada5622b50e7f41ebb56af`
- Merge commit: `69a16e988a37af957c4ba8eb5f2c36e396827fe4`
- Imported source: `upstream/mmdebstrap/make_mirror.sh`
- Imported blob: `6c4be092edcf23b56b63a3befe238c099c45f590`
- Candidate patch: `0001-preserve-signal-exit-status.patch`
- Regression: `tests/test_make_mirror_signal_exit.py`
- Reusable note: `notes/processes/signal-traps-must-terminate-after-cleanup.md`

## Observed defect

The source starts `caching_proxy.py`, records its PID, and installs cleanup actions such as:

```sh
trap 'kill "$PROXYPID" || :;cleanup_newcachedir' EXIT INT TERM
```

The QEMU path adds temporary-directory cleanup to the same pattern. These signal actions kill or remove state and then return. A shell can resume after the interrupted foreground command completes. Raw proxy stops also skipped `wait` and retained the old PID value.

## Landed ownership model

The repair adds:

- `stop_proxy()`: check a stored PID, signal a live proxy, wait in every case, then clear the PID;
- `cleanup_owner()`: stop the proxy, remove an active QEMU temporary directory, and remove the new cache only while it remains private;
- active-cache inspection: when `shared/cache` already points to `$newcache`, clear private ownership and preserve the published cache;
- `signal_exit STATUS`: clear traps, run cleanup once, and exit with the selected signal-derived status;
- separate EXIT, INT, QUIT, and TERM actions;
- state flags for private cache and QEMU temporary ownership;
- normal proxy shutdown through `stop_proxy()`.

This division keeps child shutdown separate from failure cleanup. Normal mirror completion stops the first proxy before publishing the cache. A late signal after publication sees the active symlink and leaves that cache intact.

Cleanup errors remain contained inside `cleanup_owner()`, preserving the primary command or signal result. A cleanup failure may therefore leave retained private state for diagnosis while the original status remains authoritative.

## Distinguishing regression

The exact patch is applied to a temporary source copy and the complete script passes `sh -n`. Reduced real `/bin/sh` harnesses prove:

- baseline parent-only SIGTERM: cleanup runs, later work executes, EXIT cleanup runs again, owner status 0;
- candidate parent-only SIGTERM: status 143, later work absent, cleanup once, proxy reaped, private cache marker removed;
- unsignaled candidate rerun: status 0, later marker present, cleanup once, proxy reaped;
- late cleanup after `shared/cache -> cache.B`: published directory preserved, failed-cache deletion uncalled, ownership cleared;
- every top-level cleanup-only signal trap and raw proxy stop is replaced;
- the separate subshell-local `update_cache()` trap remains outside this patch.

The baseline continuation and duplicate cleanup provide the negative control.

## Executed evidence

Early red runs classified regression-carrier defects: source/runtime directory collision, incomplete assertions, and malformed unified-diff hunk counts. Those failures occurred before a complete product matrix.

Complete-diff review then found a product gap: private-cache ownership survived past publication. The active-symlink guard and post-publication preservation test repaired that gap.

The clean current-main restack at `ac2680e0dc92b497f6ada5622b50e7f41ebb56af` passed Linux Fieldwork CI run `30579821292`. Execution carrier run `30579465025` applied the exact four-file unit and ran the four-test matrix twice successfully.

Evidence classification:

- trap, PID, cache, and publication ownership: source-read;
- signal status, proxy reaping, once-only cleanup, private-cache deletion, published-cache preservation, and rerun: model-executed with real shell processes and symlinks;
- repository compatibility: named Linux Fieldwork CI gate;
- multi-hour mirror, APT, network, package, and QEMU operation: open integration boundary.

## Cleanup and safety

The harnesses use disposable directories, symlinks, and `sleep` children. They signal and wait only for subprocesses they create. No mirror, APT transaction, network request, root operation, package mutation, or persistent cache is created.

## Evidence boundary

The retained tests cover top-level shell ownership. The subshell-local `update_cache()` trap remains a separate process-map question. Parent-only signals can remain deferred during an unrelated foreground wait. The repair adds no escalation policy for a proxy that ignores TERM and maps signals to conventional `128 + signal` exit codes instead of kernel-level re-raising.

## Authority

Internal Linux Fieldwork result. External Debian or upstream contact remains unauthorized.

## Disposition

**MERGED LOCALLY.** Use PR #205 and merge commit `69a16e988a37af957c4ba8eb5f2c36e396827fe4` as the canonical result. Retain PR #159 as development and repair history.