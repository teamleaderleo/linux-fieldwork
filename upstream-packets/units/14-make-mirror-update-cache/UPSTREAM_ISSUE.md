# Upstream issue draft

Status: `NOT NEEDED`  
Proposed destination: canonical mmdebstrap Forgejo repository  
External contact authorized: `false`

A standalone issue is currently unnecessary because the defect, correction, and deterministic regressions form one reviewable pull request. Convert this file to `DRAFT` only if upstream contribution practice or maintainer feedback requires issue-first discussion.

## Proposed title

`make_mirror.sh: keep update_cache cleanup worker-owned and retain signals through cleanup`

## Draft

### Summary

`update_cache()` runs in a pipeline subshell but its signal trap also terminates the top-level caching proxy and performs cleanup without terminating the worker. A worker-only signal can therefore resume later work, report success, clean twice, and stop a process owned by the parent shell.

A common finalizer confines the worker to its APT root, reports INT/QUIT/TERM as 130/131/143, preserves command or signal failure over cleanup failure, records the first handled signal arriving during ordinary cleanup, ignores later handled signals until bounded cleanup completes, and leaves proxy stop/wait to the top-level owner.

### Observed behavior

With the current `make_mirror.sh` source blob `6c4be092edcf23b56b63a3befe238c099c45f590`, a reduced real-`/bin/sh` worker-only TERM case returns 0, executes a later marker, invokes APT cleanup twice, and kills the parent-owned proxy. After the first finalizer repair, a signal delivered at a barrier inside cleanup can interrupt cleanup or replace an already selected TERM status.

### Expected behavior

The worker cleans only worker-owned APT state, terminates with the selected command or signal result, completes bounded cleanup once, preserves the first handled signal during cleanup, and leaves proxy lifecycle to the top-level shell.

### Minimal reproduction

```text
1. Extract the update_cache trap/finalizer lifecycle into a real /bin/sh worker.
2. Start a disposable parent-owned proxy process.
3. Deliver TERM only to the worker before cleanup.
4. Observe baseline status 0, later work, duplicate cleanup, and proxy termination.
5. Place a barrier inside cleanup and deliver TERM followed by INT.
6. Observe the predecessor cleanup interrupted and the later signal replacing the first result.
```

### Source analysis

`update_cache()` is declared with parentheses and runs as its own process. It creates `$newcachedir/apt`; the top-level shell starts and owns `$PROXYPID`. The current combined trap crosses those owners and lacks explicit signal termination. Clearing handled traps to default before cleanup also exposes cleanup-time interruption.

### Evidence

Linux Fieldwork retained real-shell matrices passed on the exact source blob:

- worker ownership/failure/signal/rerun composition: CI `30624335126` / 842;
- cleanup-time signal retention and rerun composition: CI `30630467076` / 916.

The tests use disposable files and owned subprocesses. They do not run APT, network downloads, root operations, QEMU, or the complete mirror loop.

### Compatibility and scope

The correction adds no external command or package dependency and changes only `update_cache()` finalization. Top-level proxy launch/PID registration, prompt descendant cancellation, HUP, escalation, hostile descendants, and permanently blocking cleanup remain separate.

### Proposed direction

Use one worker-local result slot and common finalizer. Ordinary/implicit EXIT cleanup installs first-signal recorder traps; explicit signal handlers record their status and ignore later handled signals; cleanup runs once; result selection follows:

```text
existing ordinary or explicit-signal failure
> first signal recorded during ordinary cleanup
> cleanup failure
> success
```

## Submission checklist

- [x] Current indexed public issue and pull-request overlap searched on 2026-07-31.
- [x] Affected current upstream revision and source blob confirmed.
- [x] Reproduction is minimal and safe.
- [x] No private credentials, internal-only links, or unsafe artifacts included in this draft.
- [x] Exact external destination identified.
- [ ] Upstream issue confirmed necessary.
- [ ] Explicit authorization recorded.
- [ ] Submitted public reference and timestamp recorded in the unit `README.md` and `DECISIONS.md`.
