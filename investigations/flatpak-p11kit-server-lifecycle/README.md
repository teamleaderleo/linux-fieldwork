# Flatpak session helper keeps advertising a dead p11-kit server

## TL;DR

At Flatpak main commit `0baf60c3a11c0de6296dd7b21d5157f35df5cf69`, `flatpak-session-helper` starts `p11-kit server` once, records the daemon PID and socket path, and then treats both as valid for the rest of the helper lifetime. The newly merged `.flatpak-helper` directory `flock()` hardens one cleanup path, but it does not cover independent death of the daemonized p11-kit process.

Flatpak issue `#6341` now contains a direct live-system discriminator: terminating only the p11-kit daemon removes the socket while leaving the helper and `monitor/` alive; the next `flatpak run` fails with the same missing-source-path shape, and the helper continues returning the stale socket until restarted. Exact current source explains that result: `handle_request_session()` publishes the stored path without a liveness/existence check, and the launcher turns it into an unconditional bubblewrap `--ro-bind` source.

This is a lifecycle successor to the directory-cleanup hardening, not evidence that the merged lock is wrong. No Flatpak commit or PR newer than the lock currently repairs p11-kit supervision/recovery. A secondary source-level risk is that the helper also retains the old numeric daemon PID and later sends it `SIGTERM` on helper exit; if that PID has been reused after an independent daemon death, the signal could target an unrelated same-user process. That PID-reuse consequence is plausible from source but not yet runtime-demonstrated here.

## Explain like I'm five

Flatpak has a long-running helper. The helper starts a second little server and writes down two things: “the server is process 1234” and “its socket is here.”

The second server deliberately detaches and runs on its own. If that detached server dies, its socket disappears, but the first helper never erases its note. Every new Flatpak app is then told to mount a socket that no longer exists, so app startup stops before the app can run.

The recent directory lock keeps a cleanup tool from sweeping away the whole helper directory. It cannot keep a separate server process alive.

## Why care

The practical consequence is session-wide launch failure for new Flatpak applications while already-running applications remain unaffected. Users in Flatpak issue `#6341` report that restarting `flatpak-session-helper` restores launches. The latest reproduction narrows the failure owner to the detached p11-kit server lifecycle: only the PKCS#11 socket is removed, `monitor/` remains, and killing the p11-kit daemon is sufficient to reproduce the same launch failure.

There is also a cleanup-identity question. Flatpak retains the daemon's integer PID until the helper exits and calls `kill(pid, SIGTERM)`. Numeric PIDs are reusable. If the p11-kit process has already died, a later process could inherit that number before the helper exits. Current code has no identity token, child handle, pidfd, or cleared state that distinguishes the original daemon from a reused PID. This is retained as an open consequence requiring its own discriminator.

## Current state

- State: `EXECUTING`
- Flatpak exact source head: `0baf60c3a11c0de6296dd7b21d5157f35df5cf69`
- p11-kit source read: `120050e353e8f43d7c40bbcc047f667f903f4de5`
- Upstream public reproduction: Flatpak issue `#6341`, latest comment `5244793833`
- Latest authoritative Fieldwork gate: exact source/history cross-check against the public live-system discriminator
- First incomplete step: execute an owned/disposable lifecycle fixture against a built Flatpak session helper and p11-kit server
- Cleanup state: no local processes, sockets, namespaces, or user services modified in this pass
- Next safe action: construct a focused process-lifecycle test that kills only the p11-kit server, checks the next `RequestSession`, then exercises recovery and helper shutdown; separately test stale-PID cleanup identity
- External-contact state: not authorized; no upstream issue, PR, comment, review, or email created by Fieldwork

## Question

Does `flatpak-session-helper` preserve a valid PKCS#11 server contract for its complete lifetime when the daemonized `p11-kit server` exits independently, and what is the smallest owner that can recover without advertising or signaling stale process identity?

## Source

### Flatpak

- Project: `flatpak/flatpak`
- Requested revision: current main at this pass
- Resolved commit: `0baf60c3a11c0de6296dd7b21d5157f35df5cf69`
- Relevant file: `session-helper/flatpak-session-helper.c`
- Consumer: `common/flatpak-run.c`
- Related issue: https://github.com/flatpak/flatpak/issues/6341
- Related hardening PR: https://github.com/flatpak/flatpak/pull/6754

### p11-kit

- Project: `p11-glue/p11-kit`
- Source revision read: `120050e353e8f43d7c40bbcc047f667f903f4de5`
- Relevant file: `p11-kit/server.c`

## Intent and precedent

Flatpak added host certificate forwarding in 2018 by starting a p11-kit server from the session helper. A later 2018 compatibility change deliberately invokes `p11-kit server --sh` through `g_spawn_sync()`: p11-kit versions before the known-good daemonizing behavior left the pipe open and caused Flatpak to hang. The present design therefore depends on p11-kit daemonizing successfully and returning a daemon PID in shell-formatted output.

The August 2026 hardening in PR `#6754` protects `$XDG_RUNTIME_DIR/.flatpak-helper` from age-based `systemd-tmpfiles` cleanup by keeping a directory fd open and holding a shared `flock()` for the helper lifetime. Review explicitly questioned whether tmpfiles was the real cause of `#6341`, and the merged change was retained as useful hardening even if another owner caused the reported deletion.

After merge, the reporter on Debian 13 demonstrated that stock `systemd-tmpfiles --clean` did not delete the directory and then produced a more specific discriminator: terminate the detached p11-kit server, observe only the socket disappear, and reproduce the exact Flatpak launch failure. No later Flatpak commit was present at this pass, and targeted p11-kit/session-helper PR search found no successor repair.

## Current Flatpak lifecycle

### Startup

`start_p11_kit_server()` builds:

```text
$XDG_RUNTIME_DIR/.flatpak-helper/pkcs11-flatpak-<flatpak-session-helper PID>
```

It synchronously launches roughly:

```text
p11-kit server --sh -n <socket-path> --provider p11-kit-trust.so ...
```

It parses `P11_KIT_SERVER_PID=<daemon pid>` from stdout. If a non-zero PID is found, Flatpak stores both:

- `p11_kit_server_pid`
- `p11_kit_server_socket_path`

No ongoing watch is attached to that daemon.

### Publication

`handle_request_session()` checks only whether `p11_kit_server_socket_path` is non-NULL. If so, it returns that value as the `pkcs11-socket` property.

`common/flatpak-run.c` consumes that property and, after writing the client-module configuration, appends:

```text
--ro-bind <published host socket path> /run/flatpak/p11-kit/pkcs11
```

Bubblewrap therefore sees a missing source path as a launch-fatal setup error.

### Shutdown

`do_atexit()` checks only whether `p11_kit_server_pid != 0`, then calls:

```c
kill (p11_kit_server_pid, SIGTERM);
```

The stored PID is never cleared after independent server death because the server is daemonized and no supervision callback updates the helper state.

## p11-kit behavior

Current p11-kit source confirms the lifecycle assumed by Flatpak:

- `p11-kit server` has a `--foreground` option;
- without it, `server_loop()` forks;
- the parent prints environment data containing the daemon PID and exits;
- the daemon calls `setsid()` and serves independently;
- `SIGTERM`/`SIGINT` cause the serving loop to terminate;
- on exit, the server removes its socket path.

That mechanism directly explains why killing only the detached daemon leaves Flatpak's helper alive while making its stored path invalid.

## Reproduction evidence

### Upstream public live-system discriminator

The latest `#6341` report states:

```text
kill -TERM <p11-kit-server pid>
→ PKCS#11 socket disappears; .flatpak-helper/monitor remains

flatpak run ...
→ bwrap: Can't find source path .../pkcs11-flatpak-<helper pid>: No such file or directory

flatpak-session-helper remains alive
→ future requests keep returning the dead path

restart flatpak-session-helper
→ launch behavior recovers
```

This is third-party upstream evidence, not a Fieldwork-owned runtime execution. Fieldwork independently traced the pinned current source and found the exact state transitions required for that transcript.

### Negative control from the directory-lock path

The same upstream report observed that `monitor/` remains present and the directory itself was not removed. That separates the p11-kit-daemon-death path from recursive directory cleanup. The new `flock()` can remain correct and useful while this successor lifecycle failure persists.

## Interpretation

**Demonstrated upstream behavior:** independent p11-kit daemon termination is sufficient on an affected live setup to reproduce the missing PKCS#11 source path while the Flatpak session helper remains alive.

**Demonstrated current source mechanism:** Flatpak publishes the stored path without validating server/socket state, and its launcher passes the path to bubblewrap as an unconditional read-only bind source.

**Demonstrated ownership mismatch:** Flatpak records a daemon PID and socket for helper-lifetime use but does not supervise the daemon after startup because p11-kit intentionally detaches.

**Plausible secondary consequence:** if the detached daemon dies and its numeric PID is reused before the helper exits, `do_atexit()` can address the reused PID with `SIGTERM`. This is a same-user lifecycle/correctness problem, not a privilege escalation claim. No PID-reuse runtime fixture has been executed in this investigation yet.

## Candidate directions

No candidate is validated yet. The design needs to make server lifetime and published state belong to one clear owner.

### A. Supervise p11-kit as a foreground direct child

p11-kit supports `--foreground`. Flatpak could spawn it asynchronously as a real child, consume the initial environment/readiness output, attach a child watch, and clear or restart state if it exits.

Potential advantages:

- direct child identity instead of a detached numeric PID;
- reliable exit notification;
- no stale `do_atexit()` PID;
- one owner for restart and publication.

Open compatibility/workflow questions:

- minimum p11-kit version where `--foreground` plus required shell output behaves as needed;
- pipe/readiness handling without recreating the historical `g_spawn_sync()` hang;
- whether automatic restart is desirable or whether the helper should temporarily omit PKCS#11 forwarding after failure.

### B. Validate and repair lazily before publication

Before returning `pkcs11-socket`, the helper could verify usable server state; on failure it could clear stale PID/path and attempt a bounded restart or omit the optional property.

This is smaller but has race/identity limits. A pathname existence check alone does not prove the server is alive, and `kill(pid, 0)` alone is unsafe against PID reuse. Any lazy repair must avoid retaining the stale PID once the original daemon identity is lost.

### C. Fail the helper when its auxiliary server dies

If supervision becomes possible, exiting the session helper on p11-kit death would let D-Bus activation create a fresh helper/server pair on the next request. This may be simpler than in-process restart but would reset other helper-owned state and needs lifecycle review.

## Adjacent contexts to test

1. **Server SIGTERM:** expected public reproducer; socket removed cleanly.
2. **Server SIGKILL/crash:** determine whether socket can remain stale even though no server owns it.
3. **Helper exit after server death:** distinguish harmless `ESRCH` from PID-reuse wrong-process signaling.
4. **Restart race:** server dies while a `RequestSession` is being serviced.
5. **p11-kit unavailable/old:** preserve current optional behavior where Flatpak runs without host PKCS#11 forwarding.
6. **Clean rerun:** after failure/recovery, launch twice and verify no stale socket/PID state survives.

Stop when one lifecycle design can distinguish the original server from any later process, does not publish a dead endpoint, preserves optional no-p11-kit operation, and has a reproducible recovery story.

## Evidence boundary

This pass did not build Flatpak, run `flatpak-session-helper`, terminate a local p11-kit daemon, manipulate a user D-Bus service, or force PID reuse. The main runtime reproduction is pre-existing public issue evidence and is clearly separated from the exact-source confirmation performed here.

No claim is made about what killed the reporter's original daemon. Suspend/resume timing mentioned upstream is context only. No security severity claim is made. The PID-reuse signal consequence remains an unexecuted, source-derived hypothesis.

The p11-kit revision read is current upstream source, not necessarily the exact packaged version in the Debian reproduction. The core daemonization/socket-removal behavior is used only to explain the current source contract; packaged-version execution remains part of a future runtime matrix.

## Next step

Create an owned process-lifecycle fixture with the exact Flatpak helper/source revision where possible:

1. start helper + p11-kit server and capture exact helper/server identities;
2. prove a normal `RequestSession` returns a live socket;
3. terminate only p11-kit and preserve helper state;
4. prove the next request still publishes the stale path on baseline;
5. compare candidate recovery behavior;
6. exercise SIGTERM and SIGKILL separately;
7. for the PID-identity lane, use a controlled PID-namespace fixture or another deterministic mechanism rather than trying to churn host PIDs blindly;
8. cleanly stop all owned processes and immediately rerun.

If runtime execution remains unavailable, the next useful source task is to prototype the smallest foreground-child or lazy-clear candidate as a non-submission patch with focused unit/process tests.

## Authority

No upstream issue, pull request, comment, review, email, or other contact was created by Fieldwork. Existing Flatpak issue and PR material were read as public evidence. Upstream contact remains unauthorized.
