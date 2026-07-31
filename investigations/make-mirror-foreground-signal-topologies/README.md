# make_mirror foreground signal topology comparison

State: `comparative-evaluation-active`

## TL;DR

The accepted top-level proxy lifecycle and the focused `update_cache()` worker repair make status, cleanup, and proxy ownership correct. They do not make every signal-delivery topology prompt while a shell waits for an unowned foreground descendant.

Executed real-`/bin/sh` controls now establish:

- worker-only TERM waits for the foreground command, then exits 143 before worker later work;
- owner-only TERM waits for the complete worker and permits worker later work before exiting 143;
- whole-process-group TERM stops promptly;
- explicit worker ownership of its foreground child makes worker-only TERM prompt;
- composed parent ownership of the pipeline worker plus worker ownership of the foreground child makes owner-only TERM prompt;
- for both the one-line and heredoc parent call shapes, a background pipeline's `$!` is the final worker PID on the target shell, and explicit `wait` preserves input plus worker status.

The current candidates remain valid for their stated eventual status and cleanup contracts. This investigation owns the separate promptness and descendant-ownership layer.

## Canonical records

- owning issue: #263;
- merged top-level lifecycle: PR #224, merge commit `386f5c8dbb01e5de1af45ac0eb325ee8567722e3`;
- focused worker lifecycle: PR #259 at `d270f558fa7c32569ea380fd614c34edaf60b3b3`;
- imported source blob: `6c4be092edcf23b56b63a3befe238c099c45f590`;
- topology regression: `tests/test_make_mirror_foreground_signal_topologies.py`;
- parent pipeline identity regression: `tests/test_make_mirror_pipeline_worker_identity.py`;
- exact command inventory: `COMMAND_INVENTORY.md`;
- branch: `investigation/make-mirror-foreground-signal-topologies`.

## Explain like I'm five

A manager owns a worker, and the worker uses a tool.

The current repair makes everyone report the right stop result and clean only their own things. But if only the manager hears “stop,” the worker and tool can finish their current job before the manager acts. If only the worker hears it, the tool can finish first.

One approach is to stop the whole group. Another is to make the manager track the worker and the worker track the tool, so cancellation can travel down the ownership chain.

## Why care

A long foreground APT command can continue after a stop request even though the eventual result is correctly reported as cancellation. Parent-only delivery can also allow later commands inside the worker to run before the top-level trap executes.

This is an operational cancellation-latency and descendant-ownership question. It is not evidence that PR #259 returns success, leaks the proxy, or violates its written cleanup contract.

## Exact source boundary

The imported source invokes `update_cache()` synchronously as the last pipeline command:

```sh
echo "deb ..." | update_cache "$dist" "$nativearch"
cat <<END | update_cache "$dist" "$nativearch"
```

Inside the worker it runs foreground operations including:

```sh
APT_CONFIG=... apt-get update --error-on=any
APT_CONFIG=... apt-get --yes install ...
```

It also contains an output-capturing command-substitution pipeline and a fallback install chain. The full grammar is classified in `COMMAND_INVENTORY.md`.

The retained PR #224 patch does not introduce a tracked pipeline-worker PID. The retained PR #259 patch does not introduce a tracked foreground-command PID. Shell traps can therefore remain deferred while those unowned foreground commands run.

## Executed topology model

The topology regression builds disposable real-shell owners with:

- a top-level owner using signal-derived status and proxy cleanup;
- a pipeline worker using PR #259-style EXIT/INT/QUIT/TERM cleanup;
- a foreground child held at a deterministic release point;
- child, worker, and owner later-work markers;
- worker and owner cleanup logs;
- proxy-disappearance checks.

A held child rather than elapsed-time thresholds distinguishes pending from prompt cancellation.

### Current worker-only delivery

TERM is sent only to the worker while its foreground child is held.

Observed:

- owner remains running and child remains alive;
- after child release, child later work exists;
- worker later work is absent;
- final status is 143;
- worker cleanup once, owner cleanup once, proxy gone.

Interpretation: PR #259 gives eventual status correctness and stops worker continuation, but cannot interrupt an unowned foreground child.

### Current owner-only delivery

TERM is sent only to the top-level owner while the worker and child are active.

Observed:

- owner remains running and child remains alive;
- after child release, child later work exists;
- worker later work also exists;
- owner later work is absent;
- final status is 143;
- both cleanups once, proxy gone.

Interpretation: the top-level shell does not own the synchronous pipeline worker, so its trap remains deferred until that worker returns.

### Whole process-group delivery

TERM is sent to the isolated process group.

Observed:

- prompt status 143;
- no child, worker, or owner later markers;
- both cleanups once;
- proxy gone.

Interpretation: group delivery is effective when the caller owns a safe isolated group. It is a caller-policy contract, not an owner-PID-only source guarantee.

### Worker-owned foreground child

The worker launches the foreground operation asynchronously, stores its PID, waits explicitly, and stops/waits it during signal cleanup.

Observed for worker-only TERM:

- prompt status 143 without releasing the child;
- no child or worker later marker;
- both cleanups once;
- proxy gone.

Interpretation: explicit worker-child ownership resolves worker-only promptness.

### Composed parent-worker and worker-child ownership

The parent launches the pipeline worker asynchronously, stores the final worker PID, waits explicitly, and stops/waits it during owner cleanup. The worker separately owns its foreground child.

Observed for owner-only TERM:

- prompt status 143 without releasing the child;
- no child, worker, or owner later marker;
- both cleanups once;
- proxy gone.

Interpretation: an explicit ownership chain resolves owner-only promptness in the model.

## Parent pipeline identity controls

A second regression exercises the two exact parent producer shapes with a worker that captures stdin and exits 7.

For both one-line and heredoc pipelines:

- the stored `$!` equals the worker's actual `$$`;
- the complete input reaches the worker unchanged;
- explicit `wait` returns worker status 7;
- the owner itself exits 0 after recording that status.

This removes one shell-portability uncertainty from the parent-worker half of the composed direction. It does not yet prove cancellation-time producer cleanup or multiple sequential worker ownership.

## Command inventory result

One generic child helper cannot preserve the exact worker grammar.

At least three source primitives would be required:

1. parent pipeline-worker ownership for one-line and heredoc calls;
2. worker simple-child ownership for direct APT commands and fallback attempts;
3. worker output-capturing pipeline ownership for `pkgs=$(...)`.

The command-substitution pipeline is the hardest boundary because asynchronous execution cannot directly assign its output to the parent worker shell. A capture artifact or controlled pipe is required, along with exact output, trailing-newline, pipeline-status, cancellation, and partial-output controls.

## Alternatives under comparison

### A. Caller-owned process group

Require supervisors to launch the mirror in an isolated process group and signal the group.

**Benefit:** prompt in the current topology with no source expansion.

**Risk:** caller policy may not provide an isolated group; group delivery may include unrelated processes; owner-PID-only semantics remain deferred.

**Evidence still needed:** actual invocation/session topology and a safe group boundary.

### B. Worker owns each foreground command

Introduce worker-local ownership for active commands.

**Benefit:** worker-only cancellation becomes prompt.

**Risk:** parent-only delivery remains deferred. One generic helper also loses on the output-capturing pipeline grammar.

**Current result:** loses as a complete answer; may remain one component of option C.

### C. Composed parent-worker and worker-child ownership

Track each pipeline worker in the parent and active command or command pipeline in the worker.

**Benefit:** both worker-only and owner-only cancellation become prompt in the executed model. Parent `$!` identity and ordinary input/status are now positively controlled for both call shapes.

**Risk:** largest source change. The worker needs separate simple-command and output-capture primitives; first-signal and launch-registration ownership repeat at two levels.

**Evidence still needed:** cancellation-time heredoc producer behavior, multiple sequential workers, fallback status, command-substitution output/status, first-signal competition, and complete composition with PR #224/#259.

## Current comparison

| Direction | Worker-only prompt | Owner-only prompt | Source change | Current evidence |
| --- | --- | --- | --- | --- |
| A. Process group | yes | yes through group rather than owner PID | none | model-executed; invocation boundary unknown |
| B. Worker child ownership | yes | no | medium | model-executed; incomplete answer |
| C. Parent-worker plus worker-child ownership | yes | yes | largest | model-executed; parent pipeline identity positive; worker grammar incomplete |

Option A remains viable only if caller group isolation is an actual supported contract.

Option C remains the only source-level direction demonstrated to make both owner-only and worker-only delivery prompt. It is not selected because the command-substitution and cancellation-time producer boundaries remain unresolved.

## Edge cases covered

| Case | Result |
| --- | --- |
| Exact source retains synchronous worker pipelines and foreground APT commands | asserted |
| Current worker-only TERM while child held | pending until release; child later work; final 143; no worker later work |
| Current owner-only TERM while child held | pending until release; child and worker later work; final 143 |
| Isolated process-group TERM | prompt 143; no later work |
| Worker-owned child, worker-only TERM | prompt 143; no later work |
| Composed ownership, owner-only TERM | prompt 143; no later work |
| One-line background pipeline `$!` | final worker PID; input preserved; status 7 preserved |
| Heredoc background pipeline `$!` | final worker PID; input preserved; status 7 preserved |
| All completed topology cases | worker cleanup once, owner cleanup once, proxy gone |

## Deferred or unproved

- real APT signal behavior;
- cancellation-time heredoc/input producer cleanup;
- output-capturing command-substitution pipeline;
- fallback install cancellation and result precedence;
- multiple sequential workers and PID clearing;
- INT/QUIT and competing signals in proposed helpers;
- launch/PID-registration windows at worker and parent levels;
- process-group isolation in actual callers;
- full mirror, network, QEMU, package, and privilege execution;
- timeout and TERM-to-KILL escalation.

## Exact execution

Local commands:

```text
python3 tests/test_make_mirror_foreground_signal_topologies.py -v
python3 tests/test_make_mirror_pipeline_worker_identity.py -v
```

Results:

- topology/source matrix: 6/6 passed;
- parent pipeline identity/input/status matrix: 2/2 passed.

Hosted execution on the retained exact head remains the next evidence gate.

## Next action

Prototype the output-capturing pipeline as the strongest discriminator for option C. Require exact output bytes, command-substitution trailing-newline behavior, ordinary final-stage failure, upstream-stage failure behavior under the target shell, worker-only cancellation, cleanup of partial capture, and immediate rerun. In parallel, recover actual caller/session topology for option A.

No human design decision is requested. Continue autonomous comparison.

Internal Linux Fieldwork work only. External contact authorized: `false`.
