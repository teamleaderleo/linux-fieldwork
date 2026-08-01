# Upstream issue draft

Status: `DRAFT`  
Proposed destination: `josch/mmdebstrap` Forgejo issue tracker  
External contact authorized: `false`

## Proposed title

`make_mirror.sh` signal cleanup can resume work and miss a newly launched proxy

## Draft

### Summary

The top-level `make_mirror.sh` process uses the same cleanup-only trap actions for ordinary exit and INT/TERM. A signal delivered to the shell can run cleanup and then return to the interrupted shell flow. The script can continue later mirror work, report success or an unrelated later failure, and run cleanup again at EXIT.

Both proxy starts also launch the child and assign `$!` in separate shell commands. A signal accepted between those commands can enter cleanup before the new proxy PID is owned, leaving the proxy alive after the parent exits.

### Observed behavior

Current `main` revision `77ec9be5417ee44c96343d2347145585da1b1f94` contains `make_mirror.sh` blob `6c4be092edcf23b56b63a3befe238c099c45f590` with top-level actions equivalent to:

```sh
./caching_proxy.py "$oldcachedir" "$newcachedir" &
PROXYPID=$!
trap 'kill "$PROXYPID" || :' EXIT INT TERM
...
trap 'kill "$PROXYPID" || :;cleanup_newcachedir' EXIT INT TERM
```

In a reduced real-`/bin/sh` reproducer, parent-PID-only TERM delivered while the shell waits for a foreground child produces this sequence:

1. the foreground child returns;
2. the signal trap runs cleanup;
3. the trap returns;
4. later work executes;
5. EXIT cleanup runs again;
6. the owner exits 0.

At either proxy launch, stopping the owner after child creation and before `PROXYPID=$!` leaves cleanup without the new child PID.

### Expected behavior

- INT, QUIT, and TERM end the top-level owner after cleanup with statuses 130, 131, and 143;
- later mirror work remains absent after cancellation;
- the current proxy is signaled, waited, and removed from owner state;
- a signal accepted during proxy launch is retained until `$!` has been registered;
- the first handled signal remains authoritative;
- cleanup removes only resources currently owned by the top-level process;
- a cache already selected through `shared/cache` remains intact;
- an immediate unsignaled rerun succeeds.

### Minimal reproduction

A compact reproducer can use a long-lived `sleep` as the proxy and a second foreground `sleep` to expose deferred shell-trap delivery:

```sh
#!/bin/sh
set -eu

cleanup() {
  printf 'cleanup\n' >>cleanup.log
  kill "$PROXYPID" 2>/dev/null || :
}

sleep 60 &
PROXYPID=$!
trap cleanup EXIT INT TERM

: >ready
sleep 1
printf 'later-work\n' >later
```

Start the script, wait for `ready`, send TERM to the script PID only, and inspect its status and `later`. The product-focused regression also checks both child-launch/PID-registration intervals with deterministic stopped-owner barriers.

### Source analysis

The top-level shell owns both `caching_proxy.py` children. The current traps mix four different responsibilities:

- ordinary EXIT cleanup;
- terminating signal result;
- proxy shutdown and reaping;
- cache and QEMU temporary cleanup.

A cleanup-only signal trap has no terminating action. Raw `kill` also leaves reaping implicit. The two-command asynchronous launch introduces a child-ownership interval before `$!` is stored.

The first proxy launch occurs before private-cache deletion ownership begins. The QEMU relaunch occurs after that ownership transition. These states require separate cleanup expectations.

### Evidence

Focused real-shell regressions distinguish:

- baseline TERM: later work present, cleanup twice, status 0;
- repaired TERM: later work absent, owner cleanup once, proxy reaped, status 143;
- ordinary rerun: status 0 and no surviving proxy;
- launch one: one owner cleanup, one proxy stop, zero signal-time cache-deletion calls, retained state removed by the next startup preflight;
- launch two: one owner cleanup and one private-cache deletion;
- TERM before PID assignment followed by INT after assignment: status remains 143;
- late cleanup after `shared/cache -> $newcache`: active cache preserved.

The reduced tests use `/bin/sh`, disposable directories and symlinks, and test-owned child processes. They avoid APT, network mirror construction, QEMU, and privileged operations.

### Compatibility and scope

The proposed behavior uses conventional shell statuses `128 + signal` and exits numerically after cleanup. It does not re-raise the kernel signal. Signal delivery can still be deferred while the shell waits for an unrelated foreground process.

A proxy that ignores TERM can keep a blocking `wait`; escalation policy is outside this report. The pipeline-subshell `update_cache()` cleanup lifecycle is a separate process-owner concern.

### Proposed direction

Separate ordinary EXIT cleanup from terminating signal handlers. Route both proxy starts through a helper that temporarily records the first INT/QUIT/TERM until the child PID is registered. Stop and wait for the owned proxy through an idempotent helper, track private-cache and QEMU temporary cleanup with explicit ownership flags, and preserve a cache already selected by the active symlink.

## Submission checklist

- [x] Current public issue and pull-request overlap searched on 2026-08-01; no visible equivalent carrier found.
- [x] Affected public source revision and file blob confirmed.
- [x] Reproduction is minimal and uses owned disposable processes.
- [x] Draft contains no credentials or private artifacts.
- [ ] Fresh zero-fuzz application and focused rerun completed on a current public checkout.
- [ ] Exact external destination and whether an issue precedes a PR confirmed.
- [ ] Explicit authorization recorded.
- [ ] Submitted public reference and timestamp recorded in the unit packet.
