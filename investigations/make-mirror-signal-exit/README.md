# make_mirror signal exit semantics

## In simple words

`make_mirror.sh` used one cleanup-only trap for ordinary exit and for `INT`/`TERM`. A parent-only termination signal could therefore run cleanup and then resume the long mirror workflow instead of exiting with the signal-derived status.

This candidate separates normal exit cleanup from signal handling, stops and waits for the proxy child, and exits with 130, 131, or 143 after cleanup.

## Canonical records

- Issue: #157
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

Near the QEMU path it installs another cleanup-only signal trap. None of those signal actions exits or re-raises.

## Candidate

The candidate introduces:

- `stop_proxy()`: signal the child if alive, `wait` for it even if already exited, and clear the PID;
- `cleanup_owner()`: call `stop_proxy()` and remove the incomplete new cache only after the workflow has crossed the readiness boundary;
- `signal_exit STATUS`: disable all traps, call `cleanup_owner()` once, and exit with the conventional signal-derived status;
- separate traps for `EXIT`, `INT`, `QUIT`, and `TERM`;
- reuse of `stop_proxy()` at the existing normal proxy-stop point without deleting the completed cache.

Separating child shutdown from cache cleanup is essential: normal successful mirror completion stops the proxy before atomically switching the finished cache into place. Calling failure cleanup from that normal stop point would delete the result.

Cleanup errors are contained with `|| :` so they cannot replace the cancellation status.

## Negative control and candidate matrix

The regression applies the patch to an exact temporary source copy and checks shell syntax. It then extracts the exact top-level trap/function structure into a reduced real `/bin/sh` harness.

A parent-PID-only `SIGTERM` is delivered while the shell waits for a foreground child:

- baseline: the deferred cleanup-only trap runs, later work executes, and the owner exits 0;
- candidate: cleanup runs once, later work is absent, the owner exits 143, and the proxy child is reaped.

An unsignaled candidate rerun must finish 0, execute the later marker, stop and reap the proxy, and clean exactly once through the ordinary EXIT path.

The source assertion requires all three top-level cleanup-only signal traps to disappear while leaving unrelated nested `update_cache()` trap behavior outside this patch.

## Cleanup and safety

The dynamic harness uses only disposable directories and `sleep` children. It sends signals only to subprocesses it created, waits for every owner, and checks that the candidate proxy PID no longer exists. No mirror, APT operation, network, root privilege, package mutation, or persistent cache is used.

## Evidence boundary

The reduced harness proves the shell trap semantics and candidate ownership without running the multi-hour mirror build. The full script has additional subshell-local traps inside `update_cache()`; those remain separate because they run in pipeline/subshell scope and need their own process-map review.

Signal-derived exit codes follow the conventional `128 + signal` mapping. This candidate does not attempt to re-raise the original signal at the kernel level.

## Disposition

Retain the focused patch and regression. No Debian or external upstream contact is included or authorized.
