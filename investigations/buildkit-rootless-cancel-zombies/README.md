# BuildKit rootless cancellation and zombie ownership

## TL;DR

`moby/buildkit#2855` reports that cancelling a solve in rootless `--oci-worker-no-process-sandbox` mode leaves the build command running and later leaves zombies. The report targets BuildKit 0.10.3 from 2022. Current BuildKit has materially different runc process handling: a 2023 change keeps runc alive while killing the in-container process so runc can reap it, and a 2026 change prevents non-tty stdin forwarding from holding `cmd.Wait()` open after kill. The old report is therefore a valuable regression specification, not current-head proof.

## Explain like I'm five

The old builder sometimes fired the babysitter before the child was collected. Newer code tries to tell the child to stop while keeping the babysitter alive long enough to clean up. We must rerun the old test to learn whether that repair also works in the unusual mode where build processes share the host PID namespace.

Literal example: client cancels `Solve()` → BuildKit should SIGKILL the build process → runc should observe and reap it → executor should delete the container → no running or zombie descendant should remain.

## Why care

A cancelled build must stop consuming CPU, memory, network, credentials, and filesystem access. Surviving commands can continue side effects after the caller believes the build ended. Zombies also reveal an ownership failure and can wedge later namespace shutdown or accumulate under a long-running daemon.

## Current state

- State: `SCOPING`
- Exact working head: canonical BuildKit `275d6864ff0ce91a06225af5f5b012887bd257cf`
- Latest authoritative gate or artifact: current executor source review plus cancellation-history review
- First incomplete step: reproduce the old scenario on current head in four worker/process-sandbox combinations
- Cleanup state: no buildkitd, rootlesskit, runc container, process, or cgroup created in this round
- Next safe action: build a deterministic signal-recording fixture and run current head before proposing product changes
- External-contact state: none authorized or made

## Intent and precedent

The 2022 issue isolates the symptom to rootless mode with `--oci-worker-no-process-sandbox`. In that process mode, current OCI spec generation uses the host PID namespace and a bound `/proc`, rather than giving each build an isolated PID namespace.

Current executor history includes two directly relevant repairs:

- commit `b76f8c02482e11b3b480e0c6ddf54cc91a667730` changed runc execution so cancellation kills the process inside the container while the runc monitor remains alive to reap it;
- commit `953437b10276e77a6f907bc60bb0f4ecc4c8e3fa` forwards non-tty stdin through an `os.Pipe`, allowing runc's `cmd.Wait()` to return after the build process is killed even if the caller's reader remains open.

Current code creates a `procHandle` with a background runc context. When the request context is cancelled, it calls a process-specific killer. For `runc run`, the killer invokes `runc kill ... SIGKILL`. The code retries failed kills, then waits for the monitored runc process to end. For `runc exec`, it reads a pidfile and signals the process directly.

These changes cover several mechanisms named in the old issue, but they do not prove behavior in host-PID-namespace mode.

## Question

On current BuildKit, does cancelling a rootless solve stop and reap the exact build process in both normal process-sandbox and no-process-sandbox modes, without allowing a later solve to attach to the cancelled execution?

## Source

- Project: BuildKit
- Public issue: `moby/buildkit#2855`
- Reported version: `v0.10.3`
- Current resolved commit: `275d6864ff0ce91a06225af5f5b012887bd257cf`
- Process-mode source: `executor/oci/spec_linux.go`, blob `2e1430aff7d7c545173cd88178cdbc343236bc09`
- Executor source: `executor/runcexecutor/executor.go`, blob `a301fecb294e07a93f513eb6bc7897bc4d8d6bda`
- Linux executor source: `executor/runcexecutor/executor_linux.go`, blob `f5097e59a5dbd48427b3a477208a4f680d5512e0`
- Relevant historical repair: `b76f8c02482e11b3b480e0c6ddf54cc91a667730`
- Relevant stdin repair: `953437b10276e77a6f907bc60bb0f4ecc4c8e3fa`
- Candidate source commit: none
- Controlled fork: `teamleaderleo/buildkit`
- Local source path: not imported yet

## Environment

Record each run independently:

- host distribution, release, kernel, architecture;
- cgroup version and delegation state;
- rootlesskit version and flags;
- runc version;
- BuildKit commit and build command;
- worker process mode;
- seccomp/AppArmor/SELinux state;
- process subreaper and PID 1 identities;
- whether stdin is open, closed, pipe-backed, or TTY-backed.

## Baseline fixture

Replace the original network-heavy `pip install` with a deterministic process program or shell fixture that:

1. writes its PID, PPID, process-group ID, session ID, PID namespace inode, and cgroup path;
2. installs TERM/INT/HUP traps that append to a durable log;
3. forks one ordinary child and one child that exits immediately to test reaping;
4. keeps stdin open;
5. blocks until killed;
6. writes an exit marker only on graceful trap execution, not on SIGKILL.

The client should:

1. start a solve and wait for the process-ready marker;
2. cancel the exact solve context;
3. record when the client call returns;
4. poll `/proc`, cgroups, runc state, and fixture files;
5. launch the identical solve again and determine whether it starts a new execution or attaches to the old one.

## Mode matrix

| Mode | Process sandbox | Primary discriminator |
|---|---|---|
| rootful | default | general executor control |
| rootful | no-process-sandbox | host PID namespace without rootlesskit |
| rootless | default | isolated PID namespace plus rootless ownership |
| rootless | no-process-sandbox | exact old issue condition |

Run each with:

- no stdin;
- open pipe stdin;
- TTY;
- one `RUN` process;
- gateway `Exec` process where feasible.

## Expected current contract

After cancellation:

- the client receives a cancellation-derived error;
- the in-container process receives SIGKILL;
- the runc monitor remains alive until it reaps its child and exits;
- `procHandle.ended` closes;
- the container is deleted;
- network namespace and mounts are released;
- no fixture PID remains running or zombie;
- a repeated solve starts a new execution unless normal solver deduplication still has another active consumer.

## Hypotheses

### H1: historical issue is repaired

Current `procHandle` and stdin-pipe changes stop and reap all modes. Close the investigation with a retained current-head negative result and link the repairs that changed the mechanism.

### H2: only open-stdin path was left

No-stdin cancellation passes, while open non-file stdin hangs before the 2026 repair and passes at current head. This would classify the old symptom as covered by later work.

### H3: host-PID-namespace mode still escapes ownership

Default process-sandbox mode passes, but no-process-sandbox leaves descendants or zombies. Continue into runc kill semantics, process groups, subreapers, and direct child ancestry.

### H4: execution deduplication is mistaken for process survival

The old command is dead, but a second request attaches to an independently retained solver execution because another consumer still owns it. Separate solver-reference behavior from executor cleanup.

## Results

### Demonstrated by source and history review

- no-process-sandbox currently selects the host PID namespace;
- current cancellation handling intentionally keeps the runc monitor on a background context;
- request cancellation sends SIGKILL to the contained process rather than immediately killing runc;
- current code retries failed kills and waits for runc termination;
- current non-TTY stdin forwarding uses an `os.Pipe` specifically to avoid runc shutdown hangs;
- the old issue predates both the 2023 process-handling repair and the 2026 stdin repair.

### Not yet demonstrated here

- whether current rootless no-process-sandbox passes the old scenario;
- whether descendant processes outside an isolated PID namespace are all killed;
- whether rootlesskit acts as subreaper in the tested topology;
- whether repeated solves attach after the original consumer cancels;
- whether cgroup cleanup catches descendants that change process groups or sessions.

## Interpretation

The issue should remain a high-value lifecycle test, but a patch based directly on the 2022 code path would be unsafe. Current executor logic already encodes the intended ownership model and has changed specifically around zombie prevention.

The next contribution-quality result is a current-head matrix with exact process ancestry. A passing result is useful evidence and may support closing or updating the research record without code. A failing result will identify which current owner—solver, executor, runc, rootlesskit, PID namespace, or cgroup—loses the process.

## Evidence boundary

No BuildKit daemon or container was started. The record does not claim the old issue is fixed or still reproducible. It only establishes that the relevant implementation changed substantially and defines the current discriminating test.

## Next step

Create a current-head fixture that emits process and namespace identity, then execute the four-mode matrix. Retain:

- process trees before cancellation, after client return, and after cleanup deadline;
- runc state and logs;
- cgroup membership and populated events;
- build fixture markers;
- repeated-solve behavior;
- open-stdin and TTY controls.

Only select a code owner after those traces agree.

## Authority

No upstream issue, pull request, comment, email, review, or other external interaction has been authorized or made.