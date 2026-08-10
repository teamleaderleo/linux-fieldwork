# runc sd-notify barrier descriptor lifetime

## TL;DR

At upstream runc commit `0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`, the successful `sdNotifyBarrier` path explicitly closes the write end of its synchronization pipe, while the read end and the descriptor returned by `UnixConn.File()` have no explicit success-path close. A reduced executable probe that copies this ownership sequence leaves exactly two extra descriptors open when garbage collection is disabled.

This matches a defect family runc has recently cared about: finalizers can make descriptor leaks disappear before a test observes them. The next step is a focused `notify_socket_test.go` regression test with GC disabled, then explicit ownership closes on the smallest successful path.

## Explain like I'm five

To ask systemd "did you receive my readiness message?", runc creates a pipe and sends one end to systemd. It also asks Go for a file object representing the Unix socket.

After systemd acknowledges the barrier, runc is done with both local helper descriptors. Today they are left for Go's garbage collector to eventually clean up.

Literal reduced result:

```text
open fds before barrier: 8
open fds after barrier:  10
change: +2
```

## Why care

Descriptor ownership should end deterministically when the barrier completes. In a long-lived attached runc process, retaining helper descriptors until finalization consumes process resources and makes lifetime dependent on garbage collection. Repeated notification paths or future reuse can amplify that cost.

## Current state

- State: `SCOPING`
- Exact working head: upstream runc `0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`; owned fork matches
- Latest authoritative gate or artifact: reduced fd-ownership probe with GC disabled, 2026-08-11
- First incomplete step: reproduce with `notifyHost` / `sdNotifyBarrier` inside the full runc test package
- Cleanup state: reduced probe closed its received SCM_RIGHTS fd, socket endpoints, and temporary directory; process exit cleaned the deliberately retained local descriptors
- Next safe action: add an fd-count regression test around successful barrier completion with GC disabled
- External-contact state: none authorized or made

## Intent and precedent

[runc PR 3291](https://redirect.github.com/opencontainers/runc/pull/3291) introduced the sd_notify barrier and its unit test. The barrier's intended lifecycle is simple: create a synchronization pipe, send the write end to systemd, close the local write end, read EOF once systemd closes its copy, then return.

Current `sdNotifyBarrier` also calls `client.File()`. Go's Unix connection API returns a separate file descriptor for that file object; ownership therefore belongs to the caller and needs an explicit close when the helper is finished.

A later runc change, [PR 5243](https://redirect.github.com/opencontainers/runc/pull/5243), disabled GC during fd-leak testing specifically because finalizers could otherwise close leaked descriptors before inspection. That precedent makes deterministic close behavior the useful contract to test here.

## Question

Does a successful `sdNotifyBarrier` retain the pipe read descriptor and the duplicated Unix-socket descriptor until garbage collection instead of closing them when the barrier finishes?

## Source

- Project: opencontainers/runc
- Requested revision: current upstream `main` during this scout
- Resolved commit: `0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`
- Candidate source commit: none yet
- Relevant paths: `notify_socket.go`, `notify_socket_test.go`
- Owned fork: `teamleaderleo/runc`, `main` at the same resolved commit
- Historical carriers:
  - [runc PR 3291](https://redirect.github.com/opencontainers/runc/pull/3291)
  - [runc PR 5243](https://redirect.github.com/opencontainers/runc/pull/5243)

## Environment

Reduced source-level probe:

- Platform: Linux amd64 execution sandbox
- Go: `go1.23.2 linux/amd64`
- GC: disabled with `debug.SetGCPercent(-1)` during descriptor measurement
- Full runc test suite: not yet executed

## Baseline behavior

The current success path has these ownership events:

```text
os.Pipe()           -> pipeR + pipeW
client.File()       -> duplicated clientFd
send pipeW via SCM_RIGHTS
pipeW.Close()
read EOF on pipeR
return success
```

The error-only deferred cleanup closes `pipeR` and `pipeW` only when the named return error is non-nil. The success path has no explicit `pipeR.Close()` or `clientFd.Close()`.

A standalone Go probe copied that sequence, used a Unix datagram peer to receive and close the SCM_RIGHTS descriptor, disabled GC, and counted `/proc/self/fd` around one successful barrier.

Observed output:

```text
fd-count before=8 after=10 delta=+2 (GC disabled)
```

The count matches the two locally unclosed descriptors predicted by source inspection.

## Hypothesis or candidate

The candidate should make success-path ownership explicit:

- close `pipeR` on all returns after creation;
- close the file returned by `client.File()` on all returns after creation;
- preserve the deliberate early close of `pipeW` after sending it to systemd;
- preserve current error reporting and barrier timeout behavior.

A small implementation can use immediate defers for the read end and duplicated socket file while retaining the explicit write-end close.

## Reproduction

Reduced probe requirements:

1. create a Unix datagram server/client pair;
2. disable GC;
3. count `/proc/self/fd`;
4. execute the current barrier ownership sequence;
5. have the server receive and close the passed SCM_RIGHTS fd so the client reads EOF;
6. count `/proc/self/fd` again.

Current result is `+2`.

## Results

Demonstrated in the reduced probe:

- successful barrier completion can occur while two local helper descriptors remain open;
- disabling GC keeps the ownership error observable;
- the number of retained descriptors matches `pipeR` plus the `client.File()` duplicate.

## Interpretation

This is a high-confidence resource-lifetime candidate. The relevant ownership is entirely local to `sdNotifyBarrier`; both helper descriptors cease to have a purpose when the function returns.

The useful test should assert deterministic closure rather than relying on a later GC cycle. That aligns with runc's own recent fd-leak test hardening.

## Evidence boundary

The reduced probe reproduces the same standard-library resource ownership sequence and the same successful SCM_RIGHTS/EOF lifecycle. It has not yet executed the full runc implementation or its repository tests.

The practical impact of two descriptors per successful barrier depends on process lifetime and call frequency. This record establishes retained ownership, not an exhaustion scenario.

No current runc issue or pull request specific to `sdNotifyBarrier` descriptor lifetime was found during the 2026-08-11 scout. Refresh overlap immediately before any publication decision.

## Next step

Extend `notify_socket_test.go` in the owned fork with a successful barrier fd-count test that disables GC, closes the server-received SCM_RIGHTS fd, and requires the caller's fd set to return to baseline. Then apply explicit closes and rerun the existing barrier test plus the new leak test.

## Authority

No upstream contact is authorized or made. All work remains local or in `teamleaderleo/*` repositories unless a human explicitly authorizes publication.
