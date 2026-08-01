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

The collapsed source candidate was built twice. The first controlled staging build used a downstream-history GitHub branch whose `make_mirror.sh` blob matched canonical upstream exactly. The final build cloned current canonical Forgejo `main`, mirrored its real history to `linux-fieldwork/upstream-main-snapshot`, applied the fixed patch with zero fuzz, and committed one source change at `b2a9a09b36fd13f22a024ebf8522ac58543eac28`. Ten candidate-facing lifecycle cases passed on that exact source in 3.459 seconds.

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

### Approach E — rewrite the user fork's default branch

- Mechanism: force the downstream-history `master` branch to canonical upstream.
- Result: rejected. The branch carries independent downstream history that the unit does not own.
- Selected alternative: preserve `master`, mirror canonical Forgejo history to a dedicated snapshot branch, and build the candidate directly on that snapshot.

## Selected correction

One source patch combines the two landed internal patches because they edit the same `update_cache()` finalizer and jointly define one observable worker lifecycle. Splitting them would submit an intermediate state with a known cleanup-time signal gap.

The final controlled source branch is `linux-fieldwork/unit-14-make-mirror-update-cache-upstream-main`. Its base is exact canonical upstream `77ec9be5417ee44c96343d2347145585da1b1f94`; its source commit is `b2a9a09b36fd13f22a024ebf8522ac58543eac28` before the project-native regression commit.

## Why the changes belong together

Ownership, signal termination, once-only cleanup, cleanup-time signal retention, and result precedence share one state machine and overlapping source lines. The cleanup-time repair depends on the common finalizer introduced by the ownership repair. One source commit presents the complete final behavior without asking upstream to review or temporarily accept the known intermediate gap.

A project-native regression belongs in the same pull request as a separate test commit. It verifies the final source through the repository's `tests/` and `coverage.txt` conventions without mixing test mechanics into the source patch.

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

The retained and exact-candidate matrices execute real `/bin/sh`. The patch uses shell functions, integer tests, variable assignment, `trap`, and `exit`, all already used by the script. No new runtime command or package dependency is added.

The proposed native regression is a repository test shell file that invokes Python's standard library to drive deterministic real-shell cases. The project test runner itself is Python and already requires Python 3. The regression adds no product runtime dependency.

## Negative controls and losing mutations

The baseline ownership fixture loses with false status 0, later continuation, duplicate cleanup, and wrong-owner proxy kill. The predecessor cleanup-time fixture loses by default signal termination after cleanup `start`, retained APT state, and signal replacement. Cleanup status 74 controls establish that the detector distinguishes success, primary failure, signal, and cleanup failure. Immediate reruns distinguish complete cleanup from a test that checks status alone.

The exact-candidate adapter selects candidate-facing cases from the retained modules and replaces their old patch-construction hooks with the final source file. This proves the collapsed source identity while preserving the original negative controls as separate provenance.

## Current upstream and historical review

A hosted clone on 2026-08-01 confirmed canonical Forgejo `main` remains `77ec9be5417ee44c96343d2347145585da1b1f94`. `make_mirror.sh` remains blob `6c4be092edcf23b56b63a3befe238c099c45f590`. The controlled snapshot branch preserves that exact history.

Indexed official issue/PR searches on 2026-07-31 found no equivalent public work. This is an observed search result, not proof that unindexed or newly created work is absent. A direct live recheck remains required before authorization.

Historical carrier roles and exact heads are preserved in `SOURCE_MAP.md`. PR #286 and PR #324 are the canonical component implementations. Earlier PRs are construction history. PR #224 is the adjacent top-level owner repair. PR #264 is the explicit hold on broader supervision.

## Remaining questions

1. **Project-native regression result:** complete the hosted `tests/make-mirror-update-cache-worker-lifecycle` run with shellcheck, upstream shfmt options, direct execution, coverage registration, and diff hygiene.
2. **Native harness entry point:** decide whether direct execution of the registered focused test is sufficient, or whether a complete `coverage.py` invocation is worth the required prebuilt mirror state.
3. **Overlap freshness:** inspect the live upstream issue and pull-request lists immediately before authorization.
4. **Delivery route:** create a canonical Forgejo-compatible fork/branch or confirm an accepted patch submission route. The GitHub branches are controlled staging and evidence surfaces.

## Evidence boundary

The retained regressions use real shells, pipelines, signals, owned subprocesses, waits, deterministic cleanup barriers, and disposable files. They do not run APT, network downloads, a full mirror loop, root operations, QEMU, process-group delivery, HUP, escalation, hostile descendants, or permanently blocking cleanup.

The exact canonical clone, zero-fuzz application, shell syntax, diff hygiene, ownership assertions, complete one-file review, and ten-case dynamic matrix have all run on the canonical-ancestry candidate. A complete mirror build remains outside the focused gate because it introduces network and package-state variables unrelated to the shell lifecycle discriminator.

## Reopen triggers

- upstream changes the `update_cache()` source blob or surrounding trap lifecycle;
- a live equivalent upstream issue/PR appears;
- the project-native test contradicts the retained or exact-candidate matrix;
- an upstream maintainer requests a two-commit source sequence;
- real APT execution contradicts the retained lifecycle result;
- measured harmful descendant cancellation latency clears the PR #264 hold.
