# Cloud Hypervisor — migration sender cleanup termination delivery

Updated: 2026-08-11
State: SCOPING / SOURCE BOUNDARY MAPPED
Owning issue: #581
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@915d359f97475b1a39d8561f8db514da9e692d19`
External-contact state: false; none occurred

## TL;DR

`SendAdditionalConnections` distributes memory work through a bounded Rust `sync_channel`. Its error cleanup tries to enqueue one `Disconnect` per worker with `try_send()` and discards any `Full`/`Disconnected` result before joining every thread.

That is not a guaranteed shutdown protocol. If cleanup starts while the work queue is full, some disconnect messages can be lost. A surviving worker can later drain queued work and block in `recv()` because the sender is still alive; cleanup then waits forever in `join()`.

The next step is a deterministic reduced fixture followed by the real worker ownership shape. Do not change product code before proving the full-queue cleanup discriminator.

## Explain like I'm five

The sender has a mailbox shared by its worker threads. During normal work the mailbox can intentionally fill up.

To stop the workers, cleanup tries to put one “go home” note per worker into that same mailbox. But if the mailbox is full, cleanup throws the failed note away and immediately waits for every worker to go home.

A worker that never got a note can finish the old jobs, look at the still-open mailbox, and wait for another job forever. Cleanup is waiting for that worker, so both sides are stuck.

## Why care

This is a migration failure-path convergence problem. Backpressure is an expected state of the bounded queue. Error cleanup must still terminate deterministically when backpressure exists.

## Current state

- State: `SCOPING`
- Exact working head: `915d359f97475b1a39d8561f8db514da9e692d19`
- Latest authoritative gate: current-source review
- First incomplete step: deterministic full-queue cleanup fixture
- Cleanup state: no runtime resources created
- Next safe action: reproduce current shutdown algorithm with bounded queue and worker joins under a harness deadline
- External-contact state: false; no upstream interaction authorized or made

## Question

Can `SendAdditionalConnections::cleanup()` guarantee that all remaining sender workers receive a terminal condition when the bounded work channel is full at the moment error cleanup begins?

## Source

Project: Cloud Hypervisor

Primary path: `vmm/src/migration/transport.rs`

### Queue construction

```text
BUFFERED_REQUESTS_PER_THREAD = 64
buffer_size = BUFFERED_REQUESTS_PER_THREAD * configured_connections
(message_tx, message_rx) = sync_channel(buffer_size)
message_rx is shared by all workers behind Arc<Mutex<_>>
```

The bounded channel is intentional. `send_chunk()` uses `try_send()` and treats `TrySendError::Full` as ordinary backpressure so the main thread can keep checking `worker_error` rather than block indefinitely.

### Worker termination

Each worker loops on:

```text
message_rx.lock()?.recv()?
```

and exits normally only after receiving `SendMemoryThreadMessage::Disconnect` (or after an independent error).

### Cleanup

Current cleanup does:

```text
for _ in 0..self.threads.len() {
    self.message_tx.try_send(Disconnect).ok();
}

for thread in self.threads.drain(..) {
    thread.join();
}
```

There is no retry, no queue-close step, and no independent cancellation signal. `message_tx` remains alive while the joins occur.

## Baseline mechanism

A reachable schedule is:

1. multiple workers exist;
2. the bounded work queue is full of `Memory`/`Gate` messages;
3. one worker errors and the main thread chooses cleanup;
4. at least one `try_send(Disconnect)` returns `Full` and is ignored;
5. nonfailed workers continue processing queued messages;
6. the queue eventually empties;
7. fewer termination messages exist than surviving workers;
8. at least one worker blocks in `recv()` because the channel remains connected;
9. cleanup blocks in `join()`.

The key invariant is not that `try_send` can fail—that is explicit API behavior. It is that cleanup ignores the failure while subsequently assuming all workers can terminate.

## First probe

### Reduced deterministic model

Mirror only the ownership relevant to the bug:

- N worker threads;
- one shared bounded receiver behind a mutex;
- sender retained by the cleanup owner;
- nonterminal work items plus terminal disconnect items;
- joins performed immediately after best-effort terminal sends.

Use barriers so the queue is known-full at cleanup entry. Do not let the fixture itself hang forever; run the join path under a parent deadline and report blocked worker count.

Expected rows:

```text
empty queue + N disconnects       -> complete
full queue + current try_send     -> terminal sends can be lost; suspected blocked join
full queue + channel closed       -> workers drain then recv() returns disconnected
worker already dead control       -> cleanup must not block trying to send a terminal message
```

### Product-level promotion

If the model confirms the mechanism, use the real `SendAdditionalConnections` with synthetic/loopback sockets. Force one worker to fail while enough queued work remains to make the channel full. Observe whether current cleanup returns within a bounded deadline.

## Candidate boundary

Required property:

> Once migration sender cleanup starts, every worker must have a guaranteed way to stop even if the work queue is full and some workers have already failed.

Do not replace `try_send` with unconditional blocking `send()`. If all receivers have died or stopped consuming, that can move the deadlock from `join()` to the send itself.

Potential directions to compare after reproduction:

1. make channel closure the terminal condition and treat disconnected receive as successful shutdown during cleanup;
2. add an independent cancellation primitive that workers observe separately from work delivery;
3. use a bounded retry/progress protocol that observes worker liveness, only if it remains simpler than channel closure.

Preserve normal backpressure behavior and worker error reporting.

## Adjacent contexts

- Constructor spawn failure uses blocking `message_tx.send(Disconnect).ok()` for already-created workers before joining. That path has different queue occupancy and should be checked separately rather than assumed equivalent.
- Normal successful cleanup usually follows `wait_for_pending_data()`, which can leave the queue drained; passing happy-path cleanup does not disprove the error-path bug.
- Network send hangs are a different owner. Closing the work channel will not necessarily interrupt a worker already blocked in socket I/O; TCP liveness remains a separate boundary.

## Results

Established by source review:

- the work queue is bounded by design;
- `Full` is an expected send result handled elsewhere;
- cleanup discards `try_send` results;
- worker normal termination depends on receiving `Disconnect` or channel/error failure;
- cleanup retains the sender while joining.

Not yet executed:

- deterministic reduced hang;
- real product worker hang;
- candidate design;
- any compile/test/CI gates.

## Evidence boundary

This is a source-level concurrency/liveness claim. Thread scheduling determines whether a particular run hits the bad state, so the first execution must force queue occupancy and worker progress with barriers rather than depend on timing luck.

No claim is made yet that a production migration has been observed hanging through this exact mechanism.

## Stop conditions

Close as a negative result if a faithful ownership model proves another guaranteed termination path exists before join. If the reduced model reproduces but the product architecture has an independent terminal owner, narrow the claim to the model mismatch and retain that evidence.

## Next step

Execute the reduced full-queue cleanup model, then promote to a product fixture only if the model distinguishes current behavior.

## Authority

No upstream issue, pull request, review, comment, email, reaction, or other external interaction is authorized or performed by this investigation.
