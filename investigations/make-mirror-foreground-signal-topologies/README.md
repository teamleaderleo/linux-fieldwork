# make_mirror foreground signal topology comparison

State: `comparative-evaluation-active`

## TL;DR

The accepted top-level proxy lifecycle and the focused `update_cache()` worker repair make status, cleanup, and proxy ownership correct. They do not make every signal-delivery topology prompt while `update_cache()` or the top-level shell waits for a foreground descendant.

A real `/bin/sh` comparison shows:

- worker-only TERM waits for the foreground command, then exits 143 before worker later work;
- owner-only TERM waits for the complete worker and permits worker later work before exiting 143;
- whole-process-group TERM stops promptly;
- explicit worker ownership of its foreground child makes worker-only TERM prompt;
- composed parent ownership of the pipeline worker plus worker ownership of the foreground child makes owner-only TERM prompt.

The current candidates remain valid for their stated eventual status and cleanup contracts. This investigation owns the separate promptness and descendant-ownership layer.

## Explain like I'm five

A manager owns a worker, and the worker uses a tool.

The current repair makes everyone report the right stop result and clean only their own things. But if only the manager hears “stop,” the worker and tool can finish their current job before the manager acts. If only the worker hears it, the tool can finish first.

One approach is to stop the whole group. Another is to make the manager track the worker and the worker track the tool, so cancellation can travel down the ownership chain.

## Why care

A long foreground APT command can continue after a stop request even though the eventual result is correctly reported as cancellation. Parent-only delivery can also allow later commands inside the worker to run before the top-level trap executes.

This is an operational cancellation-latency and descendant-ownership question. It is not evidence that PR #259 returns success, leaks the proxy, or violates its written cleanup contract.

## Canonical records

- owning issue: #263;
- merged top-level lifecycle: PR #224, merge commit `386f5c8dbb01e5de1af45ac0eb325ee8567722e3`;
- focused worker lifecycle: PR #259 at `d270f558fa7c32569ea380fd614c34edaf60b3b3`;
- imported source blob: `6c4be092edcf23b56b63a3befe238c099c45f590`;
- comparison regression: `tests/test_make_mirror_foreground_signal_topologies.py`;
- branch: `investigation/make-mirror-foreground-signal-topologies`.

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

The retained PR #224 patch does not introduce a tracked pipeline-worker PID. The retained PR #259 patch does not introduce a tracked foreground-command PID. Shell traps can therefore remain deferred while those unowned foreground commands run.

## Executed model

The test builds disposable real-shell owners with:

- a top-level owner using signal-derived status and proxy cleanup;
- a pipeline worker using PR #259-style EXIT/INT/QUIT/TERM cleanup;
- a foreground child held at a deterministic release point;
- child, worker, and owner later-work markers;
- worker and owner cleanup logs;
- proxy-disappearance checks.

The model uses a held child rather than elapsed-time thresholds to distinguish pending from prompt cancellation.

### Current worker-only delivery

TERM is sent only to the worker while its foreground child is held.

Observed:

- the owner remains running;
- the child remains alive;
- after child release, child later work exists;
- worker later work is absent;
- final owner status is 143;
- worker cleanup once, owner cleanup once, proxy gone.

Interpretation: PR #259 gives eventual status correctness and stops worker continuation, but the signal cannot interrupt an unowned foreground child.

### Current owner-only delivery

TERM is sent only to the top-level owner while the worker and its child are active.

Observed:

- the owner remains running;
- the child remains alive;
- after child release, child later work exists;
- worker later work also exists;
- owner later work is absent;
- final owner status is 143;
- both cleanups once, proxy gone.

Interpretation: the top-level shell does not own the synchronous pipeline worker, so its trap remains deferred until that worker returns.

### Whole process-group delivery

TERM is sent to the isolated process group.

Observed:

- prompt status 143;
- no child, worker, or owner later markers;
- both cleanups once;
- proxy gone.

Interpretation: group delivery is effective when the caller already owns a safe isolated group. It is a caller-policy contract, not an owner-PID-only source guarantee.

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

## Alternatives under comparison

### A. Caller-owned process group

Require supervisors to launch the mirror in an isolated process group and signal the group.

**Benefit:** prompt in the current topology with no product-source change.

**Risk:** caller policy may not provide an isolated group; group delivery may include unrelated processes; owner-PID-only semantics remain deferred.

**Evidence still needed:** actual invocation/session topology and proof that the group contains only the intended mirror tree.

### B. Worker owns each foreground command

Introduce one worker-local helper that launches a command asynchronously, closes the launch/PID-registration window, waits, preserves ordinary status, and lets worker signal handlers stop/wait the active child.

**Benefit:** worker-only cancellation becomes prompt.

**Risk:** `update_cache()` contains simple commands, command substitutions, fallback commands, and internal pipelines. One helper may not preserve every shell grammar and status rule. Parent-only delivery remains deferred.

**Evidence still needed:** complete command inventory, ordinary/fallback/pipeline status matrices, first-signal retention, launch-window controls, cleanup failure, and rerun.

### C. Composed parent-worker and worker-child ownership

In addition to option B, run each `update_cache` pipeline asynchronously, retain the final pipeline-worker PID, and stop/wait it from top-level owner cleanup.

**Benefit:** both worker-only and owner-only cancellation become prompt in the executed model.

**Risk:** broadest source change. Pipeline `$!` identity, heredoc/input-producer behavior, first-signal retention, loop continuation, and ordinary result precedence need exact target-shell proof.

**Evidence still needed:** both call shapes, pipeline PID identity, producer completion, worker launch registration, multiple sequential workers, first-signal competition, and composition with PR #224/#259.

## Current comparison

| Direction | Worker-only prompt | Owner-only prompt | Source change | Current evidence |
| --- | --- | --- | --- | --- |
| A. Process group | yes | yes through group rather than owner PID | none | model-executed; invocation boundary unknown |
| B. Worker child ownership | yes | no | medium | model-executed for one foreground command |
| C. Parent-worker plus worker-child ownership | yes | yes | largest | model-executed for one pipeline/child chain |

Option B loses as a complete answer because it leaves owner-only delivery deferred. It may remain a useful component of option C.

Option A is viable only when caller group isolation is already guaranteed. It cannot be selected as the source contract without recovering that invocation authority.

Option C is the only source-level direction currently demonstrated to make both owner-only and worker-only delivery prompt, but its compatibility surface is not yet bounded enough to select.

## Edge cases covered

| Case | Result |
| --- | --- |
| Exact source retains synchronous `update_cache` pipelines and foreground APT commands | asserted |
| Current worker-only TERM while child held | pending until release; child later work; final 143; no worker later work |
| Current owner-only TERM while child held | pending until release; child and worker later work; final 143 |
| Isolated process-group TERM | prompt 143; no later work |
| Worker-owned child, worker-only TERM | prompt 143; no later work |
| Composed ownership, owner-only TERM | prompt 143; no later work |
| All completed cases | worker cleanup once, owner cleanup once, proxy gone |

## Deferred or unproved

- real APT signal behavior and whether individual commands handle TERM promptly;
- pipelines inside command substitution and fallback `apt-get` execution;
- heredoc producer lifetime when the last pipeline worker is backgrounded;
- multiple sequential `update_cache` calls and PID clearing;
- INT/QUIT and competing signals in proposed ownership helpers;
- launch/PID-registration windows at worker and parent levels;
- process-group isolation in actual callers;
- full mirror, network, QEMU, package, and privilege execution;
- timeout and TERM-to-KILL escalation.

## Exact execution

Local command:

```text
python3 tests/test_make_mirror_foreground_signal_topologies.py -v
```

Result: 6/6 tests passed in the disposable local model, including the exact source-boundary assertion and five topology controls.

Hosted execution on the retained branch remains the next evidence gate.

## Next action

Inventory every foreground command, internal pipeline, fallback, and command substitution inside `update_cache()`. Prototype the smallest reusable worker-child helper and test whether shell grammar or status preservation makes option C lose. In parallel, recover the actual caller/session topology to determine whether option A is a real supported contract or merely a convenient test topology.

No human design decision is requested. Continue autonomous comparison.

Internal Linux Fieldwork work only. External contact authorized: `false`.
