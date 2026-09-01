# runc parent sync liveness after `procRun`

## TL;DR

At exact runc commit `0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`, the parent-side init path can enter a blocking `parseSync()` read after sending `procRun`. `syncSocket.ReadPacket()` waits in `recvfrom()` with no timeout or process-liveness input, while error cleanup and process termination occur only after `parseSync()` returns.

Normal init closes the sync socket before waiting on the exec FIFO, so ordinary execution reaches EOF. The unresolved question is abnormal failure after `procRun` but before that close—especially a late seccomp action that kills the thread performing a sync write. The next step is an exact bounded reproduction with a pidfd/process-state control, not a speculative source patch.

## Explain like I'm five

The parent tells the child, “go ahead,” then listens for one last message or for the phone line to close.

```text
parent sends procRun
→ child fails before closing the line normally
→ parent waits in a blocking receive
→ cleanup cannot begin until that receive returns
```

The investigation asks whether the parent also needs to watch the child itself, not only the phone line.

## Why care

A stuck `runc create` or `runc run` can retain a zombie or partially created container, hold state and cgroup resources, and block higher-level container management indefinitely. A bounded error is recoverable; an unbounded bootstrap wait is not.

## Current state

- State: `SCOPING`
- Exact source head: `0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`
- Latest authoritative result: complete source path from socket creation through `procRun`, late seccomp, normal close, and parent cleanup
- First incomplete step: execute an abnormal-post-`procRun` reproduction with a hard outer timeout and retained process-state evidence
- Cleanup state: source read only; no process or container created
- Next safe action: controlled-fork integration test in a disposable Linux runner
- External-contact state: unauthorized and not made

## Question

Can runc's parent block indefinitely in `parseSync()` when the final init process fails after receiving `procRun` but before closing the sync socket normally, and what is the narrowest liveness signal that breaks the wait without racing valid late sync messages?

## Source map

### Socket ownership

`libcontainer/process_linux.go:newProcessComm()` creates a `SOCK_SEQPACKET` pair. The parent keeps `syncSockParent`; the init side receives `syncSockChild` through `ExtraFiles`. After `cmd.Start()`, the parent closes its child-side handle.

### Blocking read

`libcontainer/sync.go:parseSync()` repeatedly calls `ReadPacket()` until EOF.

`libcontainer/sync_unix.go:ReadPacket()` first calls blocking `recvfrom(MSG_TRUNC|MSG_PEEK)`. It returns EOF only when the peer side is observed closed. There is no timeout, context, pidfd, or process-state check in this read.

### Parent state after `procRun`

`libcontainer/process_linux.go:initProcess.start()`:

1. resolves the final child PID and updates `p.cmd.Process` to that process;
2. sends configuration;
3. enters `parseSync()`;
4. on `procReady`, stores container state and writes `procRun`;
5. remains in `parseSync()` for later messages or EOF;
6. performs socket shutdown and error cleanup only after `parseSync()` returns.

### Valid messages after `procRun`

The parent cannot simply shut down its write side immediately after `procRun`. In `standard_init_linux.go`, a `NoNewPrivileges` seccomp profile may be installed after `syncParentReady()` returns. That path can still send `procSeccomp` and require the parent to return `procSeccompDone` after `procRun`.

### Normal completion

`standard_init_linux.go` explicitly closes the sync pipe before waiting on the exec FIFO. That close gives the parent's `parseSync()` its normal EOF.

### Existing liveness precedent

`libcontainer/container_linux.go:waitForFifoReady()` already combines an I/O wait with init-process liveness using `pidfd_open` and `poll`, with a polling fallback. That is precedent for a bounded socket-or-process wait, not proof that the same design is correct here.

## Competing hypotheses

1. **No defect:** every relevant abnormal process exit closes the final peer reference, so `ReadPacket()` always returns EOF.
2. **Thread-level seccomp failure:** a late seccomp action kills the thread performing a sync write while another runtime thread retains the process and socket, so the peer never closes and the parent blocks.
3. **Inherited descriptor:** another process or thread retains a peer descriptor across the abnormal path.
4. **Reap/state mismatch:** the final process becomes dead or zombie while the socket state remains insufficient to wake `recvfrom()`.
5. **Harness artifact:** an apparent hang belongs to the reproducer, timeout wrapper, or process observation rather than runc.

The probe must distinguish these outcomes rather than assuming one.

## Probe design

Use the controlled fork and runc's integration harness on a disposable Ubuntu runner.

Create a container configuration with:

- `noNewPrivileges: true`;
- a seccomp rule that permits bootstrap and `procReady` but terminates the init path on the late sync `write` after `procRun`;
- a hard outer timeout around `runc create`;
- a unique state directory and container ID;
- trap-based `runc delete --force`, process cleanup, and directory removal.

Retain:

- parent exit status and elapsed time;
- `ps` state for runc parent, stage processes, and final init;
- `/proc/<pid>/fd` socket ownership while blocked;
- pidfd or `kill -0` liveness result;
- state directory and cgroup presence before cleanup;
- strace limited to `recvfrom`, `sendto/write`, `shutdown`, `close`, `poll`, `wait4`, and process signals if available;
- cleanup result and survivor scan.

Controls:

1. same container without the terminating seccomp rule;
2. early failure before `procReady`;
3. ordinary process exit after the sync socket closes;
4. forced whole-process kill rather than thread kill;
5. a synthetic `SOCK_SEQPACKET` peer that exits normally;
6. the same synthetic peer with one thread killed while another retains the descriptor.

## Candidate directions

No implementation is selected yet.

### A. Liveness-aware packet wait

Poll the sync socket and a pidfd for the final init process. If the process exits before another packet or EOF, return a classified init-death error and enter existing cleanup.

Risk: process exit and a final valid packet can race. The implementation must drain or prioritize socket state deliberately.

### B. Dedicated sync-reader goroutine plus process wait

Read packets in one goroutine and select against process liveness or context cancellation.

Risk: goroutine cancellation does not unblock a raw blocking receive unless the socket is shut down or closed, which can interfere with valid protocol completion.

### C. Protocol-level terminal acknowledgement

Replace EOF-as-success with an explicit terminal sync message and a bounded liveness watch.

Risk: wider protocol change and compatibility burden.

### D. Narrow abnormal-path descriptor correction

If the probe finds an unintended retained peer descriptor, close only that descriptor at the correct ownership transition.

Risk: source reading alone has not yet identified such a descriptor.

## Evidence boundary

Established:

- the parent performs an unbounded socket read after `procRun`;
- late valid sync traffic can occur after `procRun`;
- cleanup is downstream of the blocking parse loop;
- normal init closes the socket explicitly;
- runc has pidfd-based I/O/liveness precedent elsewhere.

Not established:

- that current main reproduces an indefinite hang;
- which process or thread retains the peer descriptor;
- whether the failure is thread-level or process-level;
- the correct race semantics between process exit and a final packet;
- a safe source change.

## Next step

Materialize the integration probe on a separate controlled-fork branch. First prove or disprove the hang with exact process and descriptor evidence. Only then prepare a candidate around the demonstrated owner: socket ownership, process liveness, protocol termination, or harness behavior.

## Authority

No upstream issue, pull request, comment, review, reaction, patch submission, email, or other external interaction has been authorized or created.
