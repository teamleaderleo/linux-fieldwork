# Cloud Hypervisor migration Gate enqueue liveness

Updated: 2026-08-12
Owning issue: #603
Worker/variant: LF-R603E
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; Cloud Hypervisor upstream remains read-only

## Question

Can `SendAdditionalConnections::wait_for_pending_data()` block forever while enqueueing a Gate after a sender worker has already failed and the bounded work queue is full?

The earlier #603 carrier proved this with the real method and a five-second harness timeout. Its candidate never executed because rustfmt rejected the generated expression. This carrier independently reruns the baseline and repairs that first failure owner.

## Baseline discriminator

The test fills a capacity-one work queue with a Memory message, sets `worker_error=true`, keeps the receiver alive without draining it, and gives the object a joinable worker returning an injected migration error.

Current blocking `SyncSender::send(Gate)` cannot observe `worker_error`; the test should hit the outer timeout.

A separate healthy-worker control starts with the same full queue, drains Memory, receives Gate, notifies the main thread, and waits on the Gate. It must complete on both baseline and candidate.

## Candidate

Replace blocking Gate enqueue with the same bounded `try_send` progress pattern already used by `send_chunk()`:

```text
while Gate is unsent:
    check worker_error
    try_send(Gate)
    Full -> short sleep + retry
    Disconnected -> open any already-published Gate and cleanup/error
```

If `worker_error` is observed, open the Gate first in case earlier Gate messages were already delivered, then enter existing cleanup.

This candidate deliberately leaves #581 unchanged. `cleanup()` can separately lose Disconnect messages on a full queue. #603 owns the earlier requirement that Gate enqueue itself must remain interruptible by worker failure.

## Gates

- exact-current baseline healthy-full-queue control;
- exact-current baseline worker-error/full-queue timeout;
- candidate worker-error test returns the injected error instead of timing out;
- candidate healthy-full-queue control remains green;
- full `vmm` library tests with KVM feature;
- focused Clippy with warnings denied, suppressing only the known base `unfulfilled-lint-expectations` condition if required by current tree;
- rustfmt and `git diff --check`;
- complete candidate-only diff retained.

## Disposition rule

`CANDIDATE READY FOR INDEPENDENT REVIEW` only if the baseline timeout reproduces, the candidate returns through cleanup/error, the healthy control stays green, and all focused/broad gates pass.
