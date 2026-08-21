# systemd-nspawn SIGHUP can bypass unix-export cleanup

## TL;DR

Current `systemd/systemd` main at `9b75d9bc66dc4f64e4fdd33603d199d374c0873b` still gives host-side `SIGTERM` and `SIGINT` explicit event-loop handling while leaving `SIGHUP` outside the blocked/registered signal set. Normal unix-export cleanup is performed after the event loop on the `finish:` path. With the ordinary default SIGHUP disposition, a host-side SIGHUP can therefore terminate nspawn before that cleanup runs.

This matches systemd's own 2024 test-history statement that SIGHUP is not handled by nspawn and can leave container resources around, plus upstream issue #36455 reports where clean shutdown removes the unix-export mount while termination paths can leave it. Exact-current runtime reproduction remains the first incomplete gate.

Internal Fieldwork issue: #572.

## Explain like I'm five

nspawn has a normal exit hallway where it kills/waits for the container and removes temporary mount state.

`SIGTERM` goes through that hallway. Current source leaves `SIGHUP` on the process's ordinary signal behavior, so SIGHUP can end nspawn before it reaches the cleanup call.

Literal sequence:

```text
container running -> unix-export mounted -> host sends SIGHUP -> nspawn exits directly -> finish cleanup never executes
```

## Why care

The surviving state lives under the nspawn runtime directories, including the per-machine `unix-export` mount. A later nspawn invocation can encounter stale mount state, and systemd added `--cleanup` specifically to clear leftovers after unexpectedly terminated invocations.

The interesting question is ownership: explicit cleanup can repair state after the fact, while ordinary signal handling decides whether the state should become stale in the first place.

## Current state

- State: `SCOPING`
- Exact upstream head: `systemd/systemd@9b75d9bc66dc4f64e4fdd33603d199d374c0873b`
- Source owner: `src/nspawn/nspawn.c`
- Latest authoritative evidence: current source + upstream history
- First incomplete step: exact-current runtime SIGTERM/SIGHUP differential
- Cleanup state: source-only work; no local mounts or processes created
- Next safe action: execute disposable privileged nspawn fixture on exact current source
- External-contact state: no upstream contact authorized or made

## Intent and precedent

### Current signal path

Current nspawn registers `SIGINT` and `SIGTERM` with the event loop. When an orderly shutdown signal is received, the callback asks the container PID 1 to halt and keeps the host nspawn process alive for teardown.

The process-level blocked signal set contains:

```text
SIGCHLD, SIGWINCH, SIGTERM, SIGINT, SIGRTMIN+18
```

`SIGHUP` is absent.

### Current cleanup path

Current `run()` reaches a `finish:` label, kills/waits for the child when needed, closes the PTY, then calls:

```c
cleanup_propagation_and_export_directories(runtime_dir);
```

That helper removes the propagation path and lazily unmounts/removes the runtime `unix-export` mount.

The explicit `--cleanup` command resolves the runtime directory and calls the same cleanup helper without starting a container.

### Historical intent

Systemd commit `14265c3360b02191975654981715584227c0650e` changed a test helper from SIGHUP to SIGTERM. Its commit message says SIGHUP is not handled by systemd-nspawn, so the process exits leaving the container scope around; SIGTERM is the defined API for proper resource release.

Systemd commit `c06a630f0c7d2396d47dbde93784c670791805fb` later introduced `--cleanup` because forcibly killed nspawn invocations can leave unix-export state that breaks subsequent starts.

## Question

At exact current main, does host-side SIGHUP bypass the same teardown that SIGTERM reaches, leaving the per-machine unix-export mount present until explicit `--cleanup` is run?

## Source

- Project: `systemd/systemd`
- Requested revision: current default branch at scout start
- Resolved commit: `9b75d9bc66dc4f64e4fdd33603d199d374c0873b`
- Primary file: `src/nspawn/nspawn.c`
- Historical signal commit: `14265c3360b02191975654981715584227c0650e`
- Cleanup-option commit: `c06a630f0c7d2396d47dbde93784c670791805fb`
- Public issue: https://redirect.github.com/systemd/systemd/issues/36455

## Hypothesis or candidate

### Hypothesis

A disposable exact-current fixture should distinguish:

```text
SIGTERM -> nspawn remains in its controlled teardown -> unix-export removed
SIGHUP  -> host nspawn terminates by signal -> unix-export remains
--cleanup after SIGHUP -> leftover unix-export removed
SIGKILL -> leftover is possible and remains outside catchable-signal repair
```

### Candidate boundary

No patch is selected yet.

If exact-current execution matches the hypothesis, the first candidate question is whether SIGHUP should join the same host-side orderly-shutdown signal path as SIGTERM/SIGINT. A candidate must also preserve the meaning of SIGHUP received by the container payload itself; host nspawn signal handling and guest PID-1 signal status are separate contexts.

## Results

### Source review

Established at the pinned head:

- SIGTERM/SIGINT are explicitly integrated into the host nspawn event loop;
- SIGHUP is absent from the host blocked signal set;
- the only `SIGHUP` occurrence found in current `nspawn.c` is interpretation of a container child exit status as reboot, a different owner;
- final unix-export cleanup is on the normal `finish:` path;
- explicit `--cleanup` calls the same cleanup helper.

### Upstream history

Systemd's 2024 test commit independently records the same host-signal distinction. Issue #36455 reports clean shutdown versus termination-path differences, and a later 258.2 report says unix-export leftovers are still reproducible in another execution context.

## Interpretation

The current source keeps two distinct SIGHUP meanings:

1. a SIGHUP status from the container child can mean guest reboot;
2. a SIGHUP delivered to the host-side nspawn process has no event-loop handler in this file.

The second path can bypass the cleanup owner entirely. Runtime evidence is still required because the complete invocation environment can change signal disposition, runtime-directory creation, and whether unix-export is mounted in a particular fixture.

## Evidence boundary

Established:

- exact current signal registration/mask;
- exact current cleanup location;
- systemd's historical statement about SIGHUP bypassing proper nspawn resource release;
- public reports that unix-export cleanup differs by termination context.

Open:

- exact-current runtime mount result;
- PTY versus pipe versus direct invocation;
- machine service versus direct nspawn invocation;
- directory versus image backing;
- whether recent PTY work changes how often SIGHUP is generated even though host-side SIGHUP handling remains absent;
- candidate behavior and test ownership.

## Next step

Build or obtain exact `9b75d9bc66dc4f64e4fdd33603d199d374c0873b` in a disposable privileged runner, create the smallest container root that causes unix-export state to exist, and run identical SIGTERM/SIGHUP cases. Record mount state before signal, after exit, and after explicit `--cleanup`.

## Authority

No upstream issue, pull request, comment, email, review, or patch submission was created or modified. Existing public systemd records were read only.