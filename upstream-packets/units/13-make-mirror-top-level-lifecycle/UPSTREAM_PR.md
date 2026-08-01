# Upstream pull request draft

Status: `DRAFT`  
Proposed destination: `josch/mmdebstrap` Forgejo pull request  
Proposed base branch: `main`  
Candidate branch or patch series: `NEEDS FORK / NEEDS BRANCH`  
External contact authorized: `false`

## Proposed title

`make_mirror.sh`: terminate cleanly and own proxies across signal windows

## Draft

### Summary

This change makes the top-level `make_mirror.sh` process own signal termination and both proxy lifetimes across their complete launch, use, cleanup, and publication lifecycle.

INT, QUIT, and TERM now end the owner with statuses 130, 131, and 143 after one cleanup dispatch. Both proxy starts retain the first handled signal until the new child PID has been registered, then stop and wait for that exact child. Cache and QEMU temporary cleanup follow explicit ownership state, and a cache already selected by `shared/cache` remains intact.

### Before

The same cleanup-only trap actions handled ordinary EXIT and signals. A parent-only signal could run cleanup and return to shell flow, allowing later mirror work and a second EXIT cleanup. Raw proxy stops used `kill` without an asserted `wait` or PID clearing.

Each proxy was also started before `$!` was copied into `PROXYPID`. A signal accepted in that interval could enter cleanup without owning the new proxy PID.

### After

- ordinary EXIT calls idempotent owner cleanup;
- INT, QUIT, and TERM clear traps, clean once, and exit 130, 131, or 143;
- the first handled signal accepted during launch remains authoritative;
- each current proxy is signaled when live, waited even when already exited, and removed from owner state;
- the first launch owns proxy cleanup while private-cache deletion remains disabled until readiness;
- the QEMU relaunch owns proxy, private-cache, and active temporary cleanup;
- a cache already published through the active symlink loses private-cleanup ownership;
- cancellation omits later work and permits an immediate clean rerun.

### Implementation

`launch_proxy()` installs temporary INT/QUIT/TERM handlers, starts the child, stores `$!`, dispatches any retained first signal, and restores ordinary terminating handlers only when no signal remains pending.

`stop_proxy()` checks the stored PID, signals a live child, waits in all owned-PID cases, and clears the PID.

`cleanup_owner()` invokes `stop_proxy()` and then performs only currently owned filesystem cleanup. `CLEANUP_PROXY_CACHE` begins after first-proxy readiness. `CLEANUP_TMPDIR` covers only the active QEMU temporary directory. Active-symlink inspection protects a cache already selected for use.

The changes form one reviewable top-level owner unit. The pipeline-subshell `update_cache()` finalizer has a separate process owner and remains outside this change.

### Tests

Focused real-`/bin/sh` regressions cover:

- the cleanup-only baseline resuming after parent-only TERM and exiting 0;
- candidate TERM exiting 143 with no later marker, one owner cleanup, and a reaped proxy;
- ordinary unsignaled status-0 rerun;
- active published-cache preservation;
- both proxy launch-to-PID registration intervals;
- first-signal precedence under TERM followed by INT;
- first-launch ownership with zero signal-time cache deletion and startup-preflight cleanup on rerun;
- second-launch private-cache deletion;
- complete patched-source `/bin/sh -n`.

The retained candidate passed its focused matrix twice and exact-head Linux Fieldwork CI. Before submission, the same patch and tests need a fresh run against the exact current public checkout and the resulting controlled-fork branch.

Upstream-native full mirror construction and `coverage.sh` remain unexecuted for the current candidate branch.

### Compatibility

The change preserves ordinary successful execution, both proxy roles, the two-cache publication design, and the existing startup preflight for an abandoned alternate cache. Primary command or signal failure remains authoritative if cleanup also fails.

Signal results use conventional numeric shell statuses. The change does not re-raise signals, add TERM-to-KILL escalation, alter `caching_proxy.py`, or change the `update_cache()` subshell lifecycle. Parent-only delivery can remain deferred during an unrelated foreground wait.

### Related issue

A separate public issue can carry the reduced reproducer when preferred by the project. The pull request itself contains the full source correction and focused regression rationale.

## Proposed commits or patch order

1. `make_mirror.sh: own signal exit and proxy launch lifecycle`

## Reviewer notes

Please focus on these state transitions:

- temporary launch handlers stay active through pending first-signal dispatch;
- first-launch cache-deletion ownership remains disabled until readiness;
- normal first-proxy stop does not invoke failed-cache cleanup;
- `PROXYPID` is cleared only after `wait`;
- `shared/cache -> $newcache` removes private cleanup authority;
- QEMU temporary cleanup is enabled and disabled around the actual temporary lifetime.

## Submission checklist

- [ ] Candidate rebased onto public `main` commit `77ec9be5417ee44c96343d2347145585da1b1f94` or a newer explicitly recorded base.
- [ ] Complete upstream diff reviewed.
- [ ] Baseline regression fails and candidate passes on the controlled-fork branch.
- [ ] Focused shell syntax and regression tests pass.
- [ ] Cleanup and immediate rerun pass.
- [ ] Full upstream mirror/coverage gate decision recorded.
- [x] Active equivalent work searched on 2026-08-01; no visible match found.
- [ ] Controlled fork and branch created.
- [x] Draft body excludes Linux Fieldwork-only routing and private data.
- [ ] Explicit authorization recorded.
- [ ] Public reference and exact submitted head recorded after submission.
