# Deep dive

## Question and observed failure

`update_cache()` runs in a pipeline subshell. The upstream baseline installs one cleanup-only trap for `EXIT INT TERM`:

```sh
trap 'kill "$PROXYPID" || :;cleanupapt' EXIT INT TERM
```

A signal delivered to the worker can therefore invoke a non-terminating handler, kill a proxy owned by the top-level shell, clean the worker APT root, resume later work, return success, and invoke cleanup again through EXIT. The retained baseline TERM control observed status 0, later work, two cleanup calls, and cross-owner proxy termination.

The first repair centralized completion and ownership. Its finalizer cleared handled signal traps to default before `cleanupapt`, creating a second bounded defect: a first signal during ordinary cleanup could terminate the worker mid-cleanup, and a later signal after explicit TERM could replace status 143.

## Source mechanism

The worker is a shell function declared with parentheses, so it executes in its own process. It owns `$rootdir=$newcachedir/apt`. The top-level shell owns `$PROXYPID` and receives the worker's nonzero result through the pipeline under `set -e`.

The final correction adds one worker-local signal slot. Ordinary/implicit EXIT cleanup installs recorder traps before clearing EXIT. An explicit signal stores its status and ignores later handled signals before entering the same finalizer. Cleanup status is captured once. Result selection occurs after cleanup:

```text
existing ordinary or explicit-signal failure
> first signal recorded during ordinary cleanup
> cleanup failure
> success
```

## Reproduction narrative

The ownership fixture starts a disposable parent-owned proxy process and a real `/bin/sh` worker with the extracted trap lifecycle. The baseline receives TERM only in the worker. It returns 0, logs later work, logs duplicate cleanup, and kills the proxy. The candidate returns 143 through the parent pipeline, omits later work, cleans the worker state once, and lets the parent stop/wait for the proxy.

The cleanup-time fixture places a deterministic barrier inside `cleanupapt`. On the predecessor, ordinary cleanup plus TERM stops after the cleanup `start` marker and leaves APT state; explicit TERM followed by INT can exit by SIGINT. On the candidate, INT/QUIT/TERM during ordinary cleanup produce 130/131/143, later handled signals cannot replace the selected result, cleanup reaches `end`, state is removed, and an immediate unsignaled rerun succeeds.

## Approach history

### Approach A — cleanup-only combined trap

- Mechanism: one `EXIT INT TERM` action kills `$PROXYPID` and calls `cleanupapt`.
- Result: rejected. It crosses process ownership, resumes after signals, reports false success, and permits duplicate cleanup.

### Approach B — separate terminating signal handlers

- Mechanism: implicit EXIT preserves `$?`; INT/QUIT/TERM call one finalizer with 130/131/143; successful completion calls the finalizer directly.
- Evidence: PR #286 matrices and CI `30624335126` / 842.
- Result: accepted as the ownership and once-only cleanup foundation.
- Remaining cost: clearing signal traps to default before cleanup exposed cleanup-time interruption and result replacement.

### Approach C — first-signal recorder through bounded cleanup

- Mechanism: record the first cleanup-time signal, ignore later handled signals, finish cleanup, then apply explicit precedence.
- Evidence: PR #324 matrices and CI `30630467076` / 916.
- Result: accepted and composed with Approach B.

### Approach D — process groups or a supervisor for prompt descendant cancellation

- Mechanism: parent/worker ownership of every command and pipeline group.
- Evidence: issue #263 / PR #264 compared 21 controls.
- Result: held. The remaining problem is unmeasured cancellation latency, while the larger mechanism adds dependency, portability, and lifecycle cost.
- Reopen discriminator: measured harmful APT cancellation latency or an accepted isolated-group/supervisor contract.

## Selected correction

One upstream patch combines the two landed internal patches because they edit the same `update_cache()` finalizer and jointly define one observable worker lifecycle. Splitting them would submit an intermediate state with a known cleanup-time signal gap.

## Why the changes belong together

Ownership, signal termination, once-only cleanup, cleanup-time signal retention, and result precedence share one state machine and overlapping source lines. The cleanup-time repair depends on the common finalizer introduced by the ownership repair. One patch presents the complete final behavior without asking upstream to review or temporarily accept the known intermediate gap.

## Compatibility analysis

### Status, signal, stderr, and continuation

- ordinary command failure remains authoritative;
- explicit INT/QUIT/TERM return 130/131/143;
- first handled signal during ordinary cleanup returns 130/131/143;
- later handled signals do not replace an established result;
- cleanup failure is visible after otherwise successful work;
- later worker work is absent after interruption.

### Process and cleanup state

- worker cleanup owns only `$rootdir`;
- top-level cleanup alone owns proxy stop/wait;
- cleanup executes once to completion for bounded cleanup;
- immediate rerun controls prove disposable APT state is removed;
- no new process, process-group, descriptor, socket, mount, or lock owner is introduced.

### Supported shell and tools

The retained matrices execute real `/bin/sh`. The patch uses shell functions, integer tests, variable assignment, `trap`, and `exit`, all already used by the script. No new external command or package dependency is added.

## Negative controls and losing mutations

The baseline ownership fixture loses with false status 0, later continuation, duplicate cleanup, and wrong-owner proxy kill. The predecessor cleanup-time fixture loses by default signal termination after cleanup `start`, retained APT state, and signal replacement. Cleanup status 74 controls establish that the detector distinguishes success, primary failure, signal, and cleanup failure. Immediate reruns distinguish complete cleanup from a test that checks status alone.

## Current upstream and historical review

Official upstream `main` was observed at `77ec9be5417ee44c96343d2347145585da1b1f94` on 2026-07-31. `make_mirror.sh` remained blob `6c4be092edcf23b56b63a3befe238c099c45f590`, matching the retained import. Indexed official issue/PR searches found no equivalent public work. This is an observed search result, not proof that unindexed or new work is absent.

Historical carrier roles and exact heads are preserved in `SOURCE_MAP.md`. PR #286 and PR #324 are the canonical component implementations. Earlier PRs are construction history. PR #224 is the adjacent top-level owner repair. PR #264 is the explicit hold on broader supervision.

## Remaining questions

1. **Full-tree single-patch application:** apply the packet patch to a controlled checkout of upstream commit `77ec9be...` and require zero fuzz/offset plus `/bin/sh -n make_mirror.sh`.
2. **Upstream-native gate:** select the smallest native entry point that exercises source parsing without running the network mirror, and state separately whether a complete `make_mirror.sh` run is practical.
3. **Candidate diff:** create a controlled fork/branch and review the complete one-file source diff.
4. **Overlap freshness:** inspect the live upstream issue and pull-request lists immediately before authorization.

## Evidence boundary

The retained regressions use real shells, pipelines, signals, owned subprocesses, waits, deterministic cleanup barriers, and disposable files. They do not run APT, network downloads, a full mirror loop, root operations, QEMU, process-group delivery, HUP, escalation, hostile descendants, or permanently blocking cleanup. This pass did not create a controlled upstream checkout because direct container DNS resolution failed. The exact source blob match removes source drift, while full-tree application of the newly collapsed single carrier remains an explicit gate.

## Reopen triggers

- upstream changes the `update_cache()` source blob or surrounding trap lifecycle;
- a live equivalent upstream issue/PR appears;
- the combined patch fails zero-offset application while the two provenance patches still apply;
- an upstream maintainer requests a two-commit review sequence;
- real APT execution contradicts the retained lifecycle result;
- measured harmful descendant cancellation latency clears the PR #264 hold.
