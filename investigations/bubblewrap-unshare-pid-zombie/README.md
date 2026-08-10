# Bubblewrap `--unshare-pid` monitor / namespace-init zombie

## TL;DR

Current Bubblewrap main (`2f55bae38468d0c50cf5df87b1e481e882b63acb`) contains the process ordering reported in upstream issue #697: the outer monitor returns as soon as sandbox PID 1 reports that the initial command exited, while sandbox PID 1 deliberately remains alive until every process in the PID namespace is gone. If the outer monitor exits first, PID 1 is orphaned; a host init or subreaper that does not reap adopted children can retain it as a zombie after PID 1 exits.

A synthetic Linux subreaper model reproduced that ordering consequence locally and observed the delayed inner init in `Z` state. Exact-current Bubblewrap binary execution remains the first incomplete gate. The prepared probe has `--as-pid-1` and no-PID-namespace controls.

The tempting repair, blocking in the outer monitor until sandbox PID 1 exits, changes an old Bubblewrap behavior: PID 1 is intentionally allowed to outlive the initial process so it can reap background or daemonized children. Candidate work therefore needs an explicit lifetime-policy decision or a narrower mechanism that preserves the desired initial-process exit contract.

Internal Fieldwork issue: #553.

## Explain like I'm five

Bubblewrap creates a small helper as process 1 inside a new PID namespace. That helper watches the program the user actually asked to run.

Literal example:

```text
input:  bwrap --unshare-pid --dev-bind / / -- /bin/true
action: /bin/true exits; sandbox PID 1 sends its exit code to outer bwrap
result: outer bwrap can exit before sandbox PID 1 finishes its own final wait/exit
```

If another process adopts the helper and never calls `wait()` for it, the helper can finish and remain as a zombie entry.

## Why care

The surviving object is a Bubblewrap helper process. Upstream #697 reports `[bwrap]` remaining as a zombie after a short `--unshare-pid` invocation and gives a no-`--unshare-pid` negative control. A later report on the same issue names Firefox/Glycin use of `--unshare-all`, which implies `--unshare-pid`, so the lifecycle edge reaches ordinary desktop callers as well as minimal containers.

The repair boundary also affects process semantics. Bubblewrap has historically allowed sandbox PID 1 to keep reaping descendants after the initial process exits because the initial process might merely be a launcher that forks the real application. Waiting for PID 1 in the outer monitor can make `bwrap` stay alive until those descendants finish.

## Current state

- State: `EXECUTING`
- Exact working head: `containers/bubblewrap@2f55bae38468d0c50cf5df87b1e481e882b63acb`
- Fieldwork branch base: `teamleaderleo/linux-fieldwork@bcb922d8934abb91a498b8b48115d58ae585cb6b`
- Probe commit: `d9ecd93c8cee76951f39fe0f8654f9a9ed38e4bd`
- Latest authoritative gate or artifact: local synthetic model passed and observed `state_after_outer_exit=Z`
- First incomplete step: run the prepared probe against a binary built from exact upstream head `2f55bae38468d0c50cf5df87b1e481e882b63acb`
- Cleanup state: synthetic adopted zombie was explicitly reaped; no retained child from the model
- Next safe action: exact-current runtime probe, then background-child discriminator before any product patch
- External-contact state: no upstream contact authorized or made

## Intent and precedent

### Observation: current source deliberately has two lifetimes

At the exact source head, `event_fd` is created when `--unshare-pid` is active and `--as-pid-1` is absent. The raw clone enters the new PID namespace. Later, Bubblewrap forks once more: the parent of that fork becomes sandbox PID 1 and runs `do_init()`, while the child execs the requested command as PID 2.

`do_init()` waits for children. When the initial command exits, it records that exit status and writes `initial_exit_status + 1` to `event_fd`. It then continues its wait loop. Only `ECHILD` ends the loop and lets sandbox PID 1 exit.

The outer `monitor_child()` polls both the eventfd and a SIGCHLD signalfd. Its comment explicitly says the eventfd is read first to preserve the real PID 2 exit status when PID 1 also exits around the same time. When an eventfd value is available, `monitor_child()` reports the command exit status and returns immediately. The later SIGCHLD/waitpid path is skipped in that iteration.

Primary source:

- https://redirect.github.com/containers/bubblewrap/commit/2f55bae38468d0c50cf5df87b1e481e882b63acb
- `bubblewrap.c::monitor_child()`
- `bubblewrap.c::do_init()`

### Observation: upstream report matches this owner

Upstream issue #697 reports Bubblewrap 0.11.0 leaving a `[bwrap]` zombie after:

```sh
bwrap --unshare-pid --dev-bind / / -- echo hi
```

inside a privileged Alpine Docker container whose PID 1 is `sleep`. The reporter says the same command without `--unshare-pid` cleans up. The issue remains open.

- https://redirect.github.com/containers/bubblewrap/issues/697

### Observation: waiting for PID 1 has a compatibility cost

An older lifecycle issue asked Bubblewrap to kill background processes when the foreground process exits. Alexander Larsson explained that Flatpak-originated behavior cannot in general know whether the initial process is the application or a launcher that forks one; with `--unshare-pid`, PID 1 could optionally exit when the initial process exits, but doing so is a distinct feature choice.

- https://redirect.github.com/containers/bubblewrap/issues/105

This history is evidence against treating `waitpid(child_pid)` as a mechanical cleanup fix. A blocking wait couples outer-bwrap lifetime to every remaining process in the namespace. Exiting PID 1 at the initial command boundary instead kills the remaining PID namespace by kernel semantics. Both choices alter existing behavior.

## Question

At exact current Bubblewrap main, does the eventfd-first monitor path leave the sandbox PID 1 helper as an adopted zombie when the caller is a non-reaping subreaper/init, with `--as-pid-1` and no PID namespace distinguishing the helper path?

## Source

- Project: `containers/bubblewrap`
- Requested revision or package version: current default branch at investigation start
- Resolved commit: `2f55bae38468d0c50cf5df87b1e481e882b63acb`
- Candidate source commit: none
- Local source path: none; exact source read through the GitHub connector
- Import metadata: source files and history fetched by exact Git ref; no upstream fork or branch created

## Environment

Synthetic model execution environment:

- Distribution and release: Debian GNU/Linux 13 (trixie)
- Kernel and architecture: Linux 6.18.35, x86_64
- Shell: bash for invocation; Python 3.13.5 for fixture
- Privileges: uid 0 in the disposable runner
- Container, virtual machine, or host context: disposable container runner
- Relevant tool versions: Python 3.13.5
- Bubblewrap runtime: absent in this runner, so exact-current product execution is pending

## Baseline behavior

The current source sequence is:

1. `--unshare-pid` without `--as-pid-1` creates `event_fd`.
2. `raw_clone()` creates the sandbox-side process in the new PID namespace.
3. After setup, that process forks the command. The parent becomes the namespace reaper and runs `do_init()`.
4. The command exits.
5. `do_init()` reaps the command and writes its exit status to `event_fd`.
6. `do_init()` continues waiting for any other children until `wait()` returns `ECHILD`.
7. The outer monitor reads `event_fd` before servicing SIGCHLD and immediately returns the command exit status.
8. If namespace PID 1 is still alive at step 7, the outer monitor exits while its direct child remains.
9. Namespace PID 1 is adopted by the nearest host subreaper/init. When it exits, a non-reaping adopter can retain it in zombie state.

The source already supplies two useful controls:

- without `--unshare-pid`, there is no sandbox PID 1 helper path;
- with `--unshare-pid --as-pid-1`, Bubblewrap does not create the exit-status eventfd and does not fork the `do_init()` helper, so the outer monitor's SIGCHLD path owns the command directly.

## Hypothesis or candidate

### Hypothesis

The #697 zombie is an ownership/lifetime race produced by the eventfd-first return boundary, rather than a mount-namespace or Docker-specific failure.

Predicted exact-current result under a subreaper harness:

```text
--unshare-pid                 -> outer bwrap returns; adopted bwrap PID 1 can become Z
--unshare-pid --as-pid-1      -> no adopted helper zombie
(no --unshare-pid)            -> no adopted helper zombie
```

### Candidate boundary

No product candidate is selected yet.

Any repair must state which lifetime it promises after the initial command exits:

- outer bwrap returns immediately while descendant processes may continue;
- outer bwrap waits for namespace PID 1 and therefore for remaining descendants;
- namespace PID 1 exits at the initial-command boundary, terminating the rest of the PID namespace;
- another ownership mechanism reaps the helper while preserving immediate outer return.

The last option would preserve the most existing behavior, but this investigation has not established a viable implementation yet.

## Reproduction

Tracked probe:

```sh
python3 investigations/bubblewrap-unshare-pid-zombie/repro_subreaper_zombie.py --model
```

Observed locally before recording the probe:

```text
model: init_pid=539 state_after_outer_exit=Z
```

The model sets itself as a Linux child subreaper, creates an outer-monitor process, creates an inner-init process, lets inner init reap a short command and signal the outer monitor, then delays inner-init exit slightly. The outer monitor exits on the signal. The original subreaper adopts inner init and observes it in `Z` state after inner init exits. The fixture then explicitly reaps it.

Exact-current Bubblewrap probe, prepared and still pending:

```sh
python3 investigations/bubblewrap-unshare-pid-zombie/repro_subreaper_zombie.py \
  --bwrap /path/to/bubblewrap-built-from-2f55bae38468d0c50cf5df87b1e481e882b63acb
```

The probe runs three cases:

```text
pid-helper          --unshare-pid
as-pid-1-control    --unshare-pid --as-pid-1
no-pidns-control    no PID namespace option
```

It becomes a subreaper, waits for the outer Bubblewrap process, inspects adopted children through `/proc`, reports zombie state, and reaps retained children before moving to the next case.

## Results

### Exact-current source review

Established:

- the helper PID 1 exists only on the relevant `--unshare-pid` / non-`--as-pid-1` path;
- PID 1 writes the initial command status before its own `ECHILD` termination condition;
- `monitor_child()` explicitly prioritizes the eventfd and returns immediately after reading it;
- the SIGCHLD branch is the branch that calls `waitpid()` on the outer monitor's child;
- therefore the eventfd branch can bypass reaping of sandbox PID 1 when the two exits are ordered command first, PID 1 second.

### Synthetic execution

The standalone ownership model produced:

```text
model: init_pid=539 state_after_outer_exit=Z
```

The retained zombie was reaped by the fixture after observation.

### Upstream runtime evidence

Issue #697 independently reports the corresponding product symptom on Bubblewrap 0.11.0 with a no-`--unshare-pid` control. That evidence predates the exact source head used here, so it supports the mechanism while leaving exact-current runtime status open.

### Test-suite review

Current `tests/test-run.sh` exercises `--die-with-parent` with and without `--unshare-pid` and checks that a lock is released after the caller shell dies. It does not place a short `--unshare-pid` invocation under a non-reaping subreaper and inspect the helper after normal command exit.

## Interpretation

The source-level owner is `monitor_child()` / `do_init()` lifetime coordination.

The key distinction is between **command completion** and **helper reap completion**. Bubblewrap currently uses the first boundary as the outer process's return point, while the helper uses the second boundary as its own return point. On a conventional host init that promptly reaps orphans, the difference is usually invisible. Under a caller/container/subreaper that adopts the helper and fails to reap it, the difference becomes a persistent zombie record.

The synthetic model proves the Linux process-ordering consequence. Upstream #697 proves that a Bubblewrap release has exhibited the symptom. Exact-current binary execution is still needed to join those two evidence classes into one current-runtime claim.

The straightforward blocking-wait repair remains unselected because it changes descendant lifetime behavior documented by long-standing Bubblewrap discussion. This is a lifecycle contract problem as well as a missing reap.

## Evidence boundary

This record establishes current-source control flow and a generic Linux subreaper consequence. It does not yet establish the symptom by executing a binary built from `2f55bae38468d0c50cf5df87b1e481e882b63acb`.

Limits:

- no exact-current Bubblewrap build/run in this runner;
- no alternate kernel or architecture execution;
- no Flatpak, Glycin, Firefox, Steam, or desktop integration execution;
- no test of real daemonizing/background-child workloads under a candidate;
- no product patch;
- no claim that every host retains the helper as a zombie; the observable consequence depends on who adopts and reaps the orphan;
- no upstream interaction.

Reopen or widen after the exact-current probe if any of these occur:

- `pid-helper` does not produce an adopted helper zombie under the synthetic subreaper;
- either control produces the same zombie;
- the helper is already reaped through a path missed in source review;
- a candidate alters initial-command exit timing or background-child lifetime.

## Next step

1. Build exact `containers/bubblewrap@2f55bae38468d0c50cf5df87b1e481e882b63acb` on a disposable Linux runner with PID namespaces available.
2. Run the tracked `--bwrap` probe twice and retain exact stdout, kernel, build configuration, and binary identity.
3. Add a second discriminator where the initial command forks a longer-lived child. Measure whether baseline outer bwrap returns at initial-command exit while sandbox PID 1 persists.
4. Only after those two gates, compare candidate policies. A candidate that fixes the zombie while silently changing the background-child case is a regression candidate, not a completed repair.

If the exact-current runtime probe matches the hypothesis, promote #553 from source-level diagnosis to a reproducible current defect and prepare a focused candidate/test branch for human design review.

## Authority

No upstream issue, pull request, email, comment, review, or patch submission was created by this investigation. Existing upstream issues were read only. External contact remains unauthorized pending an explicit human decision.
