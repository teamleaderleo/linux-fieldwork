# coverage.py complete backend process-group ownership

State: `fixture-repair-ready`

Tracking: issue #306 and PR #313.

## TL;DR

The merged parent-SIGINT repair changes a cancelled coverage matrix from status 0 to 130, but it still terminates only the immediate backend wrapper PID.

The exact null, QEMU-wrapper, and sudo topologies contain additional shells, pipelines, log followers, privileged commands, and foreground operations. Under parent-PID-only SIGINT those processes can remain alive after both `coverage.py` and the wrapper return.

The selected candidate gives every backend invocation a dedicated session/process group and terminates that complete owned group before returning 130.

The first multi-backend hosted gate, CI 885, did not execute a lifecycle assertion. It failed while the three new modules tried to build the historical status-only comparison using the old PR #204 patch under a stricter `--fuzz=0` rule. The historical test immediately before them applied the same patch under its original policy and passed.

The repaired packet now materializes that historical status-only predecessor through an exact pinned one-occurrence replacement. The new process-group product patch remains the only patch applied with zero fuzz.

## Explain like I'm five

The driver stopped the manager and reported the right cancellation number, but the manager's workers kept going.

The repair puts the manager and workers in one labelled room and stops the room. The first hosted test failed before opening any room because the test copied an old comparison with a stricter ruler than the original comparison used. The repair fixes the copied comparison, not the room mechanism.

## Canonical records

- owning issue: #306;
- canonical PR: #313;
- imported `coverage.py` blob: `9a522484aef05deae514a98e4b6adf5feb6c886d`;
- imported `run_null.sh` blob: `e0a8c106f9d3d636baea286d2ab33834748dffc9`;
- merged status-only history: PR #204 and `investigations/mmdebstrap-coverage-parent-sigint`;
- strict historical-fixture patch: `0000-materialize-status-only.patch`;
- candidate patch: `0001-own-backend-process-group.patch`;
- null regression: `tests/test_mmdebstrap_coverage_process_group.py`;
- QEMU-wrapper regression: `tests/test_mmdebstrap_coverage_qemu_process_group.py`;
- sudo regression: `tests/test_mmdebstrap_coverage_sudo_process_group.py`;
- reusable note: `notes/processes/callers-must-own-complete-backend-process-groups.md`.

## Exact caller boundary

The imported driver uses:

```python
proc = subprocess.Popen(argv)
try:
    proc.wait()
except KeyboardInterrupt:
    proc.terminate()
    proc.wait()
    break
```

The merged status-only repair replaces `break` with a diagnostic and `SystemExit(130)`. It keeps immediate-wrapper `terminate()`.

The group-owned candidate uses:

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

## Three-way result

For parent-PID-only SIGINT:

| Variant | Parent status | Live backend work | Later work |
| --- | ---: | ---: | --- |
| imported baseline | 0 | yes | yes after release |
| merged status-only semantics | 130 | yes | yes after release |
| caller-owned group | 130 | no | no |

Correct status and complete operation cleanup are distinct requirements.

## Foreground-group boundary

The imported null topology is already clean when SIGINT reaches the complete foreground group:

```text
wrapper status: -2
live group members: 0
later work: absent
```

The defect is supervisor-targeted parent-only delivery, not ordinary terminal group delivery.

## Backend evidence

### Exact null backend

The exact `run_null.sh` pipeline includes nested shells, `tee`, the status reader, and generated `test.sh`. Immediate-wrapper TERM leaves the pipeline alive and reparented; group TERM stops it.

### Exact QEMU wrapper model

The fixture retains exact `run_qemu.sh`, including its background output follower, cleanup, and guest-result path. Only `timeout --foreground debvm-run ...` is replaced by a held disposable worker.

Baseline and status-only variants leave the foreground operation alive. The group candidate stops it. Unsignaled guest-status success remains 0.

### Actual passwordless sudo path

`Needs-Root: true` selects exact `run_null.sh SUDO`. When `sudo -n true` is available, the regression uses actual sudo, requires UID 0, and requires the wrapper, sudo command, and root worker to share the observed group.

A local Sudo 1.9.16p2/use_pty negative control had seven members in the operation group. Killing only the wrapper left six alive; after FIFO release the root test performed later work.

The repository test skips only when passwordless sudo is unavailable. A hosted group escape is a test failure.

## Terminal compatibility

A pseudo-terminal comparison found:

- a `start_new_session=True` child retained inherited terminal-file-descriptor input/output but had no controlling-terminal association;
- a same-session background process group stopped on terminal input.

The dedicated session is the stronger tested isolation boundary. Direct `/dev/tty` behavior remains outside scope.

## CI 885 failure classification

Run `30628112270` / 885 failed in `setUpClass` for all three new modules.

The first failing operation was construction of the historical status-only variant:

```text
patch --fuzz=0 -p1 -i 0001-fail-after-parent-sigint.patch
```

No null, QEMU-wrapper, or sudo lifecycle assertion executed. The product mechanism was not contradicted.

The existing historical `test_mmdebstrap_coverage_parent_sigint` immediately before the new modules applied the retained PR #204 patch under its original patch policy and passed.

## Fixture repair

The historical comparison input is now built from the pinned imported source through one exact block replacement:

```python
old = """except KeyboardInterrupt:
    proc.terminate()
    proc.wait()
    break
"""
new = """except KeyboardInterrupt:
    proc.terminate()
    proc.wait()
    print("interrupted by SIGINT", file=sys.stderr)
    raise SystemExit(130)
"""
```

The null module requires `source.count(old) == 1` before replacement.

QEMU and sudo modules use the test-only zero-context `0000-materialize-status-only.patch`, which changes only the pinned `break` line into the same two status-only lines.

The candidate `0001-own-backend-process-group.patch` still applies with `--fuzz=0`. Historical PR #204 files remain unchanged.

## Regression cleanup discipline

All three modules:

- use file-backed logs so escaped descendants cannot hold assertion pipes open;
- account through Linux `/proc` and distinguish live processes from zombies;
- preserve negative-control survivors until later work is recorded;
- register cleanup for the driver session and every discovered backend group;
- permit TERM-to-KILL escalation only inside fixture teardown;
- avoid imported `TestCase` duplication;
- compile all source variants;
- retain unsignaled successful execution.

## Compatibility and limits

The process group does not own descendants that call `setsid()` or create another group. TERM-ignoring work can still block product `wait()`. Product escalation, remote supervisors, real QEMU/debvm, mounts, network, package operations, and `/dev/tty`-specific debug behavior remain outside scope.

The QEMU model proves wrapper/group inheritance, not real QEMU argument behavior. The sudo model records the available sudo configuration rather than assuming every sudoers policy is identical.

## Next transition

Create one clean current-main nine-file source generation, run repository CI, and classify the first failing owner if any. A green unchanged gate permits review-ready promotion. No source conclusion is promoted from CI 885.

Internal Linux Fieldwork work only. External contact authorized: `false`.