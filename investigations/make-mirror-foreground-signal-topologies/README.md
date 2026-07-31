# make_mirror foreground signal topology comparison

State: `comparative-evaluation-active`

## TL;DR

The accepted top-level proxy lifecycle and focused `update_cache()` worker repair make eventual signal status, cleanup, and proxy ownership correct. They do not make every PID-only cancellation topology prompt while a shell waits for an unowned foreground descendant.

The retained comparison now establishes four layers:

1. current worker-only and owner-only signals can remain deferred behind foreground work;
2. explicit parent-worker plus worker-child ownership can make those two paths prompt in a simple chain;
3. background parent pipelines preserve final-worker PID, input, and status for both one-line and heredoc producers;
4. the worker's output-capturing internal pipeline cannot be owned by its final PID alone—upstream stages survive and `wait "$!"` remains blocked. An isolated `setsid` group can stop all stages and preserve output/status semantics, but adds dependencies and group policy.

No source direction is selected yet. The simple shell-only composed approach is eliminated; the remaining comparison is between bounded internal process groups, a dedicated all-stage supervisor, and deliberately retaining eventual cancellation because the documented operational impact is limited.

## Canonical records

- issue: #263;
- merged top-level lifecycle: PR #224, merge commit `386f5c8dbb01e5de1af45ac0eb325ee8567722e3`;
- focused worker lifecycle: PR #259 at `d270f558fa7c32569ea380fd614c34edaf60b3b3`;
- imported source blob: `6c4be092edcf23b56b63a3befe238c099c45f590`;
- `COMMAND_INVENTORY.md`: exact worker command grammar;
- `CALLER_TOPOLOGY.md`: documented invocation and process-group authority;
- `OUTPUT_PIPELINE.md`: final-PID failure and isolated-group semantics;
- `tests/test_make_mirror_foreground_signal_topologies.py`;
- `tests/test_make_mirror_pipeline_worker_identity.py`;
- `tests/test_make_mirror_output_capture_pipeline_ownership.py`;
- `tests/test_make_mirror_output_capture_semantics.py`.

## In simple words

A manager owns a worker, and the worker uses tools.

The current repair makes everyone eventually report “stopped” and clean only their own things. But if only the manager hears “stop,” the worker and tool can finish first. If only the worker hears it, the active tool can finish first.

Tracking the worker and tool works for one simple chain. The real worker also has a three-tool pipeline. Tracking only the last tool does not work because the first two can survive and keep the worker waiting. Stopping an isolated group works, but the script does not currently create or promise those groups.

## Exact source boundary

The source calls `update_cache()` synchronously through two parent pipeline shapes:

```sh
echo "deb ..." | update_cache "$dist" "$nativearch"
cat <<END | update_cache "$dist" "$nativearch"
```

Inside `update_cache()` it has:

- direct foreground APT commands;
- an install fallback chain;
- source-filter pipelines whose no-match status is deliberately ignored;
- an output-capturing command-substitution pipeline used to build `pkgs`.

Neither PR #224 nor PR #259 introduces a pipeline-worker PID, foreground-command PID, or internal process group.

## Executed findings

### Current worker-only TERM

With the foreground child held, the worker signal remains pending. After release:

- child later work exists;
- worker later work is absent;
- final status is 143;
- worker cleanup once, parent cleanup once, proxy gone.

### Current owner-only TERM

With the worker and child held, the owner signal remains pending. After release:

- child later work exists;
- worker later work also exists;
- owner later work is absent;
- final status is 143;
- both cleanups once, proxy gone.

### Whole process-group TERM

An isolated group signal is prompt, leaves no later markers, exits 143, cleans each owner once, and leaves no proxy.

### Explicit simple ownership chain

Worker-owned foreground child makes worker-only TERM prompt. Parent-owned pipeline worker plus worker-owned child makes owner-only TERM prompt.

### Parent background-pipeline identity

For both one-line and heredoc producers:

- `$!` equals the final worker's actual PID;
- complete input reaches the worker;
- explicit wait preserves worker status 7.

### Output-capturing pipeline final PID

Killing the stored final-stage PID does not complete cancellation:

- final stage exits;
- producer and middle remain alive;
- shell `wait "$!"` remains blocked on the pipeline job;
- status 143 and cleanup complete only after upstream stages are separately terminated.

This rejects final-PID-only ownership for the internal package-list pipeline.

### Isolated output pipeline group

`setsid /bin/sh -c PIPELINE` plus external negative-group `kill` stops all held stages, removes partial capture, and exits 143. Ordinary controls preserve:

- command-substitution trailing-newline stripping;
- final-stage failure status 7 and rejection of partial output;
- the target shell's existing last-stage pipeline-status rule.

## Caller topology result

The retained README documents direct `./make_mirror.sh` invocation. Repository search found no `setsid` wrapper or isolated-group cancellation contract.

Therefore caller-owned group delivery is a useful mitigation for controlled wrappers, not the canonical repository answer. Interactive and noninteractive callers can provide different grouping arrangements.

## Alternatives

### A. Rely on caller process groups

**Disposition:** not selected as the repository answer.

The repository does not establish a safe isolated group. Owner-PID-only behavior would remain deferred.

### B. Track worker foreground children only

**Disposition:** rejected as a complete answer.

It fixes worker-only delivery but leaves owner-only delivery deferred and cannot by itself own the output-capturing pipeline.

### C. Track only final pipeline PIDs

**Disposition:** rejected by executed control.

Upstream stages survive and `wait "$!"` remains blocked.

### D. Internal isolated process groups

**State:** still viable.

Use explicit isolated groups for active worker commands/pipelines and track group leaders through parent and worker ownership.

**Costs and unknowns:** `setsid` and external group-aware `kill` dependencies, first-signal retention, launch registration, direct-command/fallback integration, group-leader status, and portability.

### E. Dedicated all-stage supervisor

**State:** unexecuted alternative.

A helper could explicitly spawn, signal, and wait every stage while capturing output. It avoids shell job assumptions but adds a helper-language/API boundary and more code.

### F. Retain eventual correctness and stop

**State:** viable outcome.

The script is a manually invoked mirror/test-cache helper; common interactive interruption often reaches a foreground job group, while the problematic PID-only path has unknown frequency. The accepted repairs already prevent false success, cross-owner proxy cleanup, duplicate cleanup, and leaks. A broad supervisor may cost more than the bounded remaining latency issue justifies.

## Evidence summary

Local retained matrices currently cover:

- topology/source comparison: 6 tests;
- parent pipeline PID/input/status: 2 tests;
- output pipeline ownership: 2 tests;
- grouped output/status semantics: 3 tests.

Total: 13 passing local controls on the current retained head before hosted CI.

## Boundaries

Not proved:

- actual APT signal response;
- exact availability contract for `setsid` and external `kill` in every host environment;
- cancellation-time heredoc producer cleanup beyond the held model;
- multiple sequential worker/group registrations;
- INT/QUIT and competing first signals in proposed group helpers;
- full mirror, network, QEMU, package, or privileged execution;
- timeout and TERM-to-KILL escalation.

## Next transition

Run hosted CI on the retained exact head. In parallel, inspect declared host/test dependencies for `setsid` and external group kill. If those dependencies are not explicit or the source mechanism requires broad helper code, select `stopped` with eventual correctness retained and reopening triggers for measured PID-only latency or a documented supervisor contract. If dependencies and a small common primitive are supported, prepare a separate design candidate rather than modifying PR #259.

No human design decision is requested yet.

Internal Linux Fieldwork work only. External contact authorized: `false`.
