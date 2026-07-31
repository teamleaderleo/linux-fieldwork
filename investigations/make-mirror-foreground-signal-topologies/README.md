# make_mirror foreground signal topology comparison

State: `stopped`

## TL;DR

The accepted top-level proxy lifecycle and focused `update_cache()` repair make eventual signal status, cleanup, and proxy ownership correct. PID-only cancellation can still wait behind an unowned foreground descendant.

Comparative execution shows that prompt cancellation is technically possible, but not with one small shell repair:

- worker-only and owner-only TERM are deferred in the current topology;
- caller process-group TERM is prompt, but the repository does not guarantee an isolated caller group;
- worker-child ownership fixes only worker-only delivery;
- tracking only the final PID of an internal pipeline fails because upstream stages survive and `wait "$!"` remains blocked;
- a composed source repair needs parent-worker ownership, simple-command ownership, fallback ownership, and output-capturing pipeline-group ownership;
- isolated `setsid` groups preserve the tested output/status contracts, but add process-group policy and external utility dependencies not declared by the primary test dependency block.

The remaining issue is cancellation latency under selected PID-only delivery topologies. Its occurrence frequency and maximum real APT delay are unknown. The accepted repairs already prevent false success, cross-owner proxy termination, duplicate cleanup, leaked proxy state, and later worker continuation after the worker trap runs.

The investigation therefore stops without a source patch. Reopen only on measured harmful latency, a documented isolated-supervisor contract, an explicit dependency decision, or contradictory real-workload evidence.

## In simple words

A manager owns a worker, and the worker uses tools.

The current repair makes everyone eventually report “stopped” and clean only their own things. A stop message sent only to the manager or worker can still wait until the currently active tool finishes.

Making every stop immediate is possible, but it requires the manager to track the worker, the worker to track simple tools, and a separate mechanism to track every tool in a pipeline. That is a much larger machine for a delay that has not been measured as harmful.

## Canonical records

- owning issue: #263;
- merged top-level lifecycle: PR #224, merge commit `386f5c8dbb01e5de1af45ac0eb325ee8567722e3`;
- focused worker lifecycle: PR #259 at `d270f558fa7c32569ea380fd614c34edaf60b3b3`;
- imported source blob: `6c4be092edcf23b56b63a3befe238c099c45f590`;
- `COMMAND_INVENTORY.md`: exact worker command grammar;
- `CALLER_TOPOLOGY.md`: documented invocation and process-group authority;
- `OUTPUT_PIPELINE.md`: final-PID failure and isolated-group semantics;
- `tests/test_make_mirror_foreground_signal_topologies.py`;
- `tests/test_make_mirror_pipeline_worker_identity.py`;
- `tests/test_make_mirror_output_capture_pipeline_ownership.py`;
- `tests/test_make_mirror_output_capture_pipeline_contract.py`;
- `tests/test_make_mirror_fallback_command_ownership.py`.

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

Neither PR #224 nor PR #259 introduces a pipeline-worker PID, foreground-command PID, or internal process group. Shell traps can therefore remain deferred while unowned foreground commands run.

## Executed comparison

### Current worker-only TERM

With the foreground child held, the worker signal remains pending. After release:

- child later work exists;
- worker later work is absent;
- final status is 143;
- worker cleanup once, parent cleanup once, proxy gone.

### Current owner-only TERM

With the worker and child held, the owner signal remains pending. After release:

- child and worker later work exist;
- owner later work is absent;
- final status is 143;
- both cleanups once, proxy gone.

### Whole process-group TERM

An isolated group signal is prompt, leaves no later markers, exits 143, cleans each owner once, and leaves no proxy.

### Explicit simple ownership chain

Worker-owned foreground child makes worker-only TERM prompt. Parent-owned pipeline worker plus worker-owned child makes owner-only TERM prompt.

### Parent background-pipeline identity

For both one-line and heredoc producers:

- `$!` equals the final worker PID;
- complete input reaches the worker;
- explicit wait preserves worker status 7.

### Naive output-pipeline ownership

Killing the stored final-stage PID does not complete cancellation:

- final stage exits;
- producer and middle stages remain alive;
- `wait "$!"` remains blocked on the pipeline job;
- cleanup completes only after upstream stages are separately terminated.

This rejects a final-PID-only output-capture helper.

### Isolated output-pipeline group

An isolated session/process group stops every held stage, removes partial capture, exits 143, and reruns cleanly. The retained contract matrix also preserves:

- empty, unterminated, internally multiline, and multiply terminated output;
- command-substitution trailing-newline stripping;
- final-stage failure status 7;
- rejection of partial output after failure;
- the target shell's existing rule that upstream failure is masked when the final stage succeeds.

### Fallback chain

The isolated active-command model preserves:

- first success skips fallback;
- first ordinary failure runs fallback;
- second-attempt status is authoritative;
- cancellation during the first attempt exits 143 and never starts fallback;
- immediate rerun succeeds cleanly.

## Alternatives and dispositions

### Caller-owned process group — not selected

The documented invocation is direct `./make_mirror.sh`. Repository search found no `setsid` wrapper or isolated-group cancellation contract. Interactive and noninteractive callers may group processes differently. Group delivery remains useful operational guidance for controlled wrappers, not a repository guarantee.

### Worker-child ownership only — rejected as complete answer

It makes worker-only delivery prompt but leaves owner-only delivery deferred and does not own the output pipeline.

### Final pipeline PID only — rejected by execution

Upstream stages survive and shell wait remains blocked.

### Internal isolated process groups — technically viable, not retained

This is the smallest executed source-level mechanism that can own complete pipelines. It still requires several primitives:

1. parent ownership of every `update_cache` pipeline worker;
2. worker ownership of simple commands and fallback attempts;
3. worker ownership of output-capturing pipeline groups;
4. first-signal retention and launch/PID registration at each layer;
5. capture publication and cleanup precedence.

It also relies on `setsid` and group-aware external `kill` behavior. The primary autopkgtest dependency block does not explicitly declare those utilities; `util-linux` and `procps` appear only in the separate trigger-hint context.

### Dedicated all-stage supervisor — not justified

A Python or other helper could explicitly spawn, signal, wait, and capture every stage. Python is already used by the mirror tooling, but a new supervisor file and API would still enlarge packaging, source, and compatibility surfaces. No measured impact currently justifies that expansion.

### Retain eventual correctness — selected stop outcome

PR #224 and PR #259 address the observed correctness defects. The remaining question is promptness for selected delivery topology. A broad supervision mechanism is disproportionate without evidence that the delay is frequent, long, or operationally harmful.

## Evidence summary

Retained local records report 18 controls:

- topology/source matrix: 6;
- parent pipeline PID/input/status: 2;
- output pipeline negative/group ownership: 2;
- output-capture contract: 4;
- fallback ownership: 4.

All successful cancellation models retain once-only worker cleanup, once-only owner cleanup, no accepted partial capture, and no surviving proxy or owned stage. The negative final-PID control deliberately terminates its surviving upstream controls before completion.

A fresh local rerun in the current assistant container could not begin because that container could not resolve GitHub. This is a retrieval/setup limitation, not contradictory execution evidence. Hosted CI remains queued for the retained exact head.

## Evidence boundary

Not proved:

- actual APT signal response or real delay distribution;
- complete mirror, network, QEMU, package, or privileged execution;
- availability contract for `setsid` and external group-aware `kill` across supported hosts;
- INT/QUIT and competing first signals in proposed group helpers;
- multiple sequential group registrations in the full loop;
- timeout and TERM-to-KILL escalation.

## Reopening triggers

Reopen this finding only when at least one occurs:

1. a real or faithful APT workload demonstrates materially harmful PID-only cancellation latency;
2. a supported caller/supervisor contract guarantees a safe isolated group and needs documentation or tests;
3. the project explicitly accepts `setsid`/group-kill dependencies for this script;
4. another source change already introduces an all-stage supervisor, reducing marginal complexity;
5. contradictory evidence shows the accepted #224/#259 lifecycle leaks state, reports the wrong final status, or permits post-trap worker continuation.

## Current disposition

- State: `stopped`
- Review result: `HOLD` source expansion; retain negative and comparative evidence
- Implementation: none
- Current accepted behavior: eventual cancellation correctness from #224/#259
- User decision requested: none
- Public upstream interaction: none; unauthorized
