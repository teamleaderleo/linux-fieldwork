# coverage.py complete backend process-group ownership

State: `delivery-gate-ready`

Tracking: issue #306 and PR #313.  
Exact candidate head: `e90fc438f530f7bd78ffd6fd1ba24c665bd96913`.  
Exact CI receipt: run `30632491641`, job `91161937871`, success.

## In simple words

The coverage driver starts one backend wrapper for each selected test. The wrapper may own nested shells, pipelines, log followers, a QEMU-style foreground operation, or a privileged worker through sudo.

The earlier status repair made parent-only SIGINT return 130, but it still terminated only the immediate wrapper. Backend work could survive.

The selected candidate creates a dedicated session/process group for every backend invocation, sends TERM to that owned group, waits for the wrapper, and then returns 130.

## Exact caller boundary

Imported source:

```python
proc = subprocess.Popen(argv)
try:
    proc.wait()
except KeyboardInterrupt:
    proc.terminate()
    proc.wait()
    break
```

Merged status-only behavior replaces `break` with a diagnostic and `SystemExit(130)`. It retains immediate-wrapper termination.

Selected candidate:

```python
proc = subprocess.Popen(argv, start_new_session=True)
try:
    proc.wait()
except KeyboardInterrupt:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    proc.wait()
    print("interrupted by SIGINT", file=sys.stderr)
    raise SystemExit(130)
```

The caller chooses the backend and creates one operation identity before the backend executable runs. This avoids backend-specific descendant discovery while descendants remain in the selected group.

## Three-way lifecycle result

Under parent-PID-only SIGINT:

| Variant | Final driver status | State before negative-control release | Later work |
| --- | ---: | --- | --- |
| imported baseline | 0 | backend remains live | yes after release |
| merged status-only semantics | 130 | backend remains live | yes after release |
| caller-owned group | 130 | no live in-group backend | no |

For the QEMU negative controls, the coverage driver remains blocked in `proc.wait()` while the foreground operation survives. The fixture records that live state, releases the operation, and then observes final status 0 or 130. The candidate exits 130 without a release because the complete modeled operation has already stopped.

Correct status, bounded driver settlement, and complete backend cleanup are separate requirements.

## Backend evidence

### Exact null backend

The exact `run_null.sh` topology includes nested shells, `tee`, the status reader, and generated `test.sh`.

- imported baseline: final status 0 after the surviving pipeline is released;
- status-only predecessor: final status 130 after release;
- group candidate: status 130, no live pipeline, no later work;
- ordinary candidate run: status 0 and clean group teardown.

A separate foreground-group Ctrl-C control is already clean on the imported null topology. The defect is supervisor-targeted parent-only delivery.

### QEMU wrapper model

The fixture retains exact `run_qemu.sh`, including its output follower, cleanup, and guest-result path. Only the expensive `timeout --foreground debvm-run ...` payload is replaced with a held disposable worker.

- baseline and status-only variants leave the foreground operation live and keep the coverage driver blocked until release;
- the candidate stops the wrapper operation and exits 130;
- the unsignaled candidate preserves guest-status success and complete cleanup.

This proves wrapper/group inheritance for the modeled operation. It does not execute real QEMU or debvm.

### Actual passwordless sudo path

When `sudo -n true` succeeds, the repository regression uses exact `run_null.sh SUDO` and actual sudo. It requires the wrapper, sudo command, and UID-0 worker to remain in the observed operation group.

- baseline and status-only variants leave privileged work alive until release;
- the candidate returns 130 with no live in-group privileged work;
- the unsignaled candidate succeeds and cleans the group;
- a hosted group escape fails the test rather than silently upgrading the claim.

The module skips only when passwordless sudo is unavailable.

## Exact repository gate

Linux Fieldwork CI `30632491641`, job `91161937871`, passed on exact head `e90fc438f530f7bd78ffd6fd1ba24c665bd96913`:

- validated two retained patch files and three hunks;
- compiled Python tools and tests;
- ran 359 tests in 167.224 seconds;
- all 359 passed;
- null baseline, status-only, candidate, foreground-group, and unsignaled controls passed;
- QEMU baseline, status-only, candidate, and unsignaled controls passed;
- sudo baseline, status-only, candidate, and unsignaled controls passed;
- shell syntax and command-help checks passed.

## Carrier repair history

Three earlier CI generations failed before or around the new controls:

- CI 885: historical status-only fixture used an incompatible strict patch policy;
- CI 906: candidate patch declared incorrect hunk counts;
- CI 921: corrected counts still retained stale source context;
- CI 927: all candidate positive controls passed, while QEMU negative controls deadlocked because the fixture waited for the driver before releasing the deliberately surviving operation.

Those carrier defects were repaired without changing the product mechanism or expected lifecycle outcomes. CI 931 is the first complete green repository receipt.

## Regression discipline

The three modules:

- use file-backed logs so escaped descendants cannot hold assertion pipes open;
- inspect Linux `/proc` and distinguish live members from zombies;
- retain negative-control survivors until their state and later work are recorded;
- register teardown for the driver session and discovered backend group;
- permit TERM-to-KILL escalation only in fixture teardown;
- compile every source variant;
- retain unsignaled successful execution.

## Compatibility and limits

The selected group does not own descendants that call `setsid()`, create another group, or delegate to a remote supervisor. TERM-ignoring descendants can still block product `wait()`. Product escalation, real QEMU/debvm, mounts, network, package operations, other operating systems, and `/dev/tty`-specific behavior remain outside scope.

The dedicated session retained inherited terminal file-descriptor I/O in the focused PTY comparison. Direct controlling-terminal behavior remains separate.

## Exact next transition

Complete-diff review the nine-file generation and obtain one eligible independent acceptance. The green receipt supports `delivery-gate-ready`; it does not authorize merge, release, deployment, credentials, private-data access, spending, or public upstream interaction.

Internal Linux Fieldwork work only. External contact authorized: `false`.
