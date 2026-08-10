# Candidate design: make p11-kit a supervised foreground child

Status: design record only. No upstream patch has been built or executed.

## Decision target

Replace the current detached-daemon ownership contract with a direct-child contract so `flatpak-session-helper` can know when the PKCS#11 server exits, stop publishing stale state, and avoid signaling a stale numeric PID at helper shutdown.

## Compatibility evidence

Flatpak deliberately uses `p11-kit server --sh` as a compatibility gate for p11-kit 0.23.10 or newer. Flatpak commit `11d9b5b0b6483c18cfaa44296314da1a87934433` says earlier p11-kit versions do not daemonize correctly and make `g_spawn_sync()` hang.

The p11-kit commit `f73868b710d4463cc0cff6f8ea2f3a171f86c8e2`, `server: Print envvars even when running in foreground`, landed before the `0.23.10` release commit `f6b7a992e442218a5afdbf8ae1697c53f3f03991`. A commit comparison shows the release is ten commits ahead with `f73868...` as the merge base, so foreground-mode shell environment output is already present in the same minimum release Flatpak expects.

That removes one likely compatibility blocker: a foreground candidate does not inherently require raising Flatpak's p11-kit floor beyond the version its current code already selects.

## Existing Flatpak machinery to reuse

The same `flatpak-session-helper.c` already has a direct-child lifecycle pattern for host commands:

```text
g_spawn_async_with_pipes(... G_SPAWN_DO_NOT_REAP_CHILD ...)
→ GPid
→ g_child_watch_add_full(... child_watch_died ...)
→ remove tracked state when the child exits
```

The p11-kit candidate should reuse that shape rather than introduce detached-process polling.

## Candidate lifecycle

### 1. Start in foreground

Invoke a command shaped like:

```text
p11-kit server --foreground --sh -n <known socket path> --provider p11-kit-trust.so ...
```

Use asynchronous spawn with `G_SPAWN_DO_NOT_REAP_CHILD` and a stdout pipe.

The helper already knows the desired socket pathname before spawn, and asynchronous spawn directly returns the child `GPid`. There is no need to trust a later detached PID as the process identity.

### 2. Use p11-kit output as readiness, not merely process creation

Current p11-kit source creates/listens on the socket before its foreground branch calls `print_environment()` and `fflush(stdout)`. Therefore the initial shell output can serve as a readiness discriminator: seeing valid `P11_KIT_SERVER_ADDRESS` / `P11_KIT_SERVER_PID` output means the known foreground process has reached the serving setup far enough to publish the endpoint.

Do not treat `g_spawn_async_with_pipes()` success by itself as readiness.

Implementation needs a bounded, main-loop-friendly read of the startup lines. Do not wait for EOF because a healthy foreground server intentionally keeps running and keeps the stdout pipe open.

### 3. Publish only ready live state

Only set `p11_kit_server_socket_path` after startup/readiness succeeds.

`handle_request_session()` should continue treating PKCS#11 forwarding as optional. If no ready p11-kit server exists, omit `pkcs11-socket` rather than publishing a known-dead pathname.

### 4. Watch direct child exit

Attach a dedicated `g_child_watch_add_full()` callback for p11-kit.

On exit:

- close/reap the child correctly;
- clear the tracked GPid before any future helper shutdown path can signal it;
- clear/free `p11_kit_server_socket_path`;
- record the exit status for diagnosis;
- choose a bounded recovery policy.

The first candidate can be conservative: clear the optional PKCS#11 property and let later requests run without host trust forwarding. Automatic restart can be a separate policy once failure throttling and readiness are tested.

### 5. Helper shutdown

If a live supervised child remains, terminate that known child during helper shutdown. After the child-watch callback has cleared state, shutdown must not signal the old PID.

The direct-child watch closes the numeric-PID identity hole that exists when the daemon detaches and later disappears without informing the helper.

## Recovery policy options

### Clear-only v1

On p11-kit exit, stop advertising PKCS#11 forwarding for the remaining helper lifetime.

Advantages:

- smallest policy;
- new Flatpak apps can launch instead of failing on a missing bind source;
- no restart loop or failure amplification.

Cost:

- host trust forwarding remains unavailable until helper restart.

This is a strong first behavioral candidate because it converts a session-wide launch outage into degradation of an optional integration.

### Lazy restart v2

When the next `RequestSession` arrives and no p11-kit child is ready, attempt one bounded restart before replying. If restart fails, omit the property.

Advantages:

- recovers functionality automatically.

Extra requirements:

- serialize concurrent requests around one restart;
- define retry/backoff after repeated failures;
- keep startup timeout bounded;
- avoid publishing a path until readiness completes.

### Immediate restart v3

Restart directly from the child-watch path.

This has the highest retry-amplification risk and should not be the first candidate without an explicit backoff policy.

## Required tests

### Startup/readiness

- successful foreground start publishes a socket only after readiness output;
- startup failure leaves property absent;
- a child that starts but never produces readiness does not hang the helper indefinitely;
- existing p11-kit-absent behavior remains optional/successful.

### Independent server death

For `SIGTERM` and `SIGKILL` separately:

```text
ready server
→ terminate server only
→ child watch fires
→ tracked process identity cleared
→ socket property omitted or repaired
→ next Flatpak launch does not receive a dead bind source
```

`SIGTERM` should normally remove the socket through p11-kit cleanup. `SIGKILL` may leave a stale filesystem socket, so liveness must derive from supervised process state, not pathname existence alone.

### Shutdown identity

- helper exits while child is live: only the tracked direct child is terminated;
- child dies first, watch clears state, helper exits later: no signal is sent to the old numeric PID;
- deterministic PID-identity negative control should prove cleanup does not act on a replacement process identity.

### Clean rerun

Start a fresh helper immediately after each failure case and verify no stale socket, watch, child, or state leaks into the new invocation.

## Donuts to avoid

### Supervised but published too early

Direct-child ownership is not sufficient if the helper publishes the socket before p11-kit has created/listened on it.

### Socket exists but server is dead

A `SIGKILL` can leave a socket filesystem node behind. Path existence is not an adequate liveness oracle.

### Child watched but stale PID still signaled

Every exit path must clear the exact state consumed by `do_atexit()` or replace that shutdown logic entirely.

### Restart works but loops forever

Automatic recovery needs serialization and bounded retry behavior.

### New child lifecycle breaks old compatibility

The candidate must still behave correctly with the p11-kit 0.23.10 contract that Flatpak already intentionally selects.

## Evidence boundary

This document maps a source-compatible design. It has not been compiled, executed, or reviewed against Flatpak's complete GLib main-loop/error-handling conventions. Exact function decomposition, ownership types, and startup timeout strategy remain open implementation details.

No upstream submission is authorized.
