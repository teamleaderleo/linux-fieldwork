# Cloud Hypervisor — migration receive liveness and failure events

Updated: 2026-08-11
State: SCOPING / SOURCE BOUNDARY MAPPED
Owning issue: #580
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@915d359f97475b1a39d8561f8db514da9e692d19`
External-contact state: false; none occurred

## TL;DR

Two receive-side boundaries on current Cloud Hypervisor deserve executable discrimination.

First, the main receive attempt emits `vm.migration-receive-ready`, then performs `ReceiveListener::accept()`. For TLS, that call includes the server-side TLS handshake. Any accept/socket-option/handshake error returns before `vm.migration-receive-started` and before the later `ReceiveMigrationState::Aborted` branch that emits `vm.migration-receive-failed`.

Second, auxiliary memory receive workers poll the local kill event only before reading a request. Once `receive_memory_ranges()` starts consuming a `Command::Memory` payload, explicit cleanup cannot interrupt the blocking read. The source comment states that a sender stopping mid-request can hang the worker forever; cleanup then waits while joining that worker.

Both questions can be tested with local loopback fixtures and no guest.

## Explain like I'm five

A migration receiver has two jobs: say when a migration failed, and stop its helper threads when the migration is cancelled.

Today there are two gaps.

- If the secure connection fails while saying hello, the API gets an error but the receiver can skip the normal “migration failed” event.
- If a helper has started reading a big memory message and the sender simply stops halfway without closing the socket, telling the helper to stop is not enough; it is already blocked somewhere that does not listen for the stop signal.

## Why care

Event-driven orchestration should not have to infer terminal migration failure from an API error when other failure paths emit a lifecycle event. Teardown should also be able to finish after an explicit abort rather than wait indefinitely for a peer that remains connected but stops sending.

## Current state

- State: `SCOPING`
- Exact working head: `915d359f97475b1a39d8561f8db514da9e692d19`
- Latest authoritative gate: current-source review
- First incomplete step: execute no-guest loopback discriminators
- Cleanup state: no runtime resources created
- Next safe action: implement two local test fixtures, event sequence and stalled payload cleanup
- External-contact state: false; no upstream interaction authorized or made

## Intent and precedent

Relevant public context:

- `cloud-hypervisor/cloud-hypervisor#8478` reports a failed TCP/TLS receive that did not produce `vm.migration-receive-failed`.
- `cloud-hypervisor/cloud-hypervisor#8492` asks for testing the receive-migration error case.
- PR 8660 / issue 8470 added `SO_KEEPALIVE` and `TCP_USER_TIMEOUT` to detect dead migration connections. Its scope explicitly excludes live-but-hung peers.

The current source has since added clearer receive-abort state handling, so the original “receiver stuck” report must not be copied wholesale. The current question is narrower: which terminal failures still bypass event emission, and which worker waits still ignore explicit cleanup.

## Question A — pre-protocol failure event

Does a failed main receive attempt emit a terminal `vm.migration-receive-failed` event when the failure occurs during TCP accept, socket setup, or server-side TLS handshake before the migration protocol starts?

### Source path

`vmm/src/migration/transport.rs`:

- `ReceiveListener::accept()` performs `TcpListener::accept()`;
- TCP variants configure keepalive/user-timeout;
- TLS variant then calls `TlsStream::new_server(...)` before returning `SocketStream::Tls`.

`vmm/src/lib.rs`, `Vmm::vm_receive_migration()`:

```text
receive_migration_listener(...)
event("vm", "migration-receive-ready")
listener.accept()?
event("vm", "migration-receive-started")
protocol loop
...
ReceiveMigrationState::Aborted => event("vm", "migration-receive-failed")
```

The `?` at `listener.accept()` is therefore upstream of the only visible failure-event owner in this function.

### First probe

Receiver: TLS enabled on loopback.

Clients:

1. connect and close immediately;
2. connect and send non-TLS bytes;
3. valid TLS handshake then malformed migration request as a control.

Capture API result and event stream.

Expected baseline discriminator:

```text
pre-protocol TLS failure:
  migration-receive-ready = yes
  migration-receive-started = no
  migration-receive-failed = no
  API error = yes

protocol abort control:
  migration-receive-ready = yes
  migration-receive-started = yes
  migration-receive-failed = yes
  API error = yes
```

### Candidate boundary

A terminal receive attempt should have one failure-event owner. Avoid adding ad-hoc event calls to every transport error site if a small wrapper around the attempt can emit once on any terminal error while preserving current success/abort events.

## Question B — explicit cleanup during a partial memory payload

Can receiver cleanup interrupt an auxiliary memory worker that has already read a valid `Command::Memory` request header/table but is blocked waiting for the remaining payload bytes?

### Source path

`ReceiveAdditionalConnections::worker_receive_memory()`:

```text
wait_for_readable(socket, kill_evt)
Request::read_from(socket)
receive_memory_ranges(..., socket)
Response::ok().write_to(socket)
```

The source comment is explicit:

```text
We only check whether we should abort when waiting for a new request.
If the sender stops sending data mid-request, we will hang forever.
```

`ReceiveAdditionalConnections::cleanup()` writes the kill event and joins the accept thread. The accept thread joins all memory workers before returning. Therefore a payload read that cannot observe `kill_evt` can also prevent cleanup from returning.

### First probe

Construct one additional receive connection locally:

1. send `ConnectionRole::PrecopyMemory`;
2. send a syntactically valid memory request declaring N bytes;
3. send fewer than N payload bytes;
4. keep the peer socket open and idle;
5. signal the receive-side kill/cleanup path;
6. bound the observation with a test harness deadline rather than allowing the test itself to hang indefinitely.

Controls:

- idle before request header + cleanup -> should stop through `wait_for_readable`;
- close mid-payload -> blocking read should return EOF/error and worker should exit;
- complete payload -> response and normal cleanup;
- open/idle mid-payload -> suspected liveness failure.

### Candidate boundary

The required property is **explicit local teardown can interrupt the receive worker**. That is different from detecting a dead network peer.

Do not default to a short global read timeout; a legitimate slow migration can have long payload gaps. Candidate directions to compare after baseline execution:

- abort-aware chunked/polled reads that watch both socket and kill event while consuming the declared payload;
- a transport cancellation mechanism that causes the worker socket read to unblock when cleanup begins;
- a separately justified migration inactivity deadline, only if project policy wants one.

## Adjacent contexts

1. **Main protocol socket vs auxiliary memory sockets.** The main migration loop may have different cancellation ownership; do not generalize before checking it.
2. **TCP vs TLS.** TLS buffering may change exactly where a stalled read blocks, but explicit cleanup must remain observable through both transports if both are supported.
3. **Dead vs live-but-idle peer.** Keepalive/user-timeout coverage is a negative control, not proof that explicit abort is interruptible.
4. **Fault connection.** Postcopy fault traffic has request/response semantics and separate disconnect handling; widen only if it shares the same uninterruptible cleanup problem.

## Results

Established by source review:

- TLS server handshake occurs inside `ReceiveListener::accept()`.
- `Vmm::vm_receive_migration()` emits `migration-receive-ready` before `accept()` and `migration-receive-started` only after it succeeds.
- `migration-receive-failed` is emitted in the later `ReceiveMigrationState::Aborted` branch.
- Auxiliary workers poll `kill_evt` before a request but not during the memory payload read.
- Cleanup writes `kill_evt` and joins threads.
- Current source explicitly documents the mid-request infinite-hang condition.

Not yet executed:

- current-main TLS event sequence;
- current-main stalled-payload cleanup behavior;
- any candidate;
- rustfmt/Clippy/unit/backend gates.

## Evidence boundary

This is source/history mapping only. It does not claim a reproduced current-main hang yet. The TLS event omission is a control-flow consequence visible in source; runtime can still close it if another event owner exists outside the reviewed function, which is why the event-stream probe is required.

The mid-payload liveness issue is explicitly acknowledged by a current source comment, but its practical teardown consequence still needs a bounded executable fixture.

## Stop / split conditions

- Close Question A as a negative result if an external event owner demonstrably emits `migration-receive-failed` on the handshake-failure fixture.
- Narrow Question B if existing socket options or TLS behavior cause the partial-read fixture to unwind on a bounded schedule.
- Once either question has executable proof and a product candidate, split it into its own carrier rather than coupling event semantics to read cancellation.

## Next step

Build the two no-guest fixtures on a controlled Cloud Hypervisor fork branch at the exact current source. Record the exact event sequence and cleanup deadline result before changing product code.

## Authority

No upstream issue, pull request, comment, review, email, reaction, or other interaction is authorized or performed by this investigation.
