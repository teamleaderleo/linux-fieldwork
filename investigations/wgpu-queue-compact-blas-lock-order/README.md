# wgpu queue submission and BLAS compaction lock order

State: `ACTIVE — SOURCE DETECTOR QUEUED`  
Worker or variant: `LF-R02`  
Public contact authorized: `false`

## Bounded question

Does current `wgpu-core` acquire `Device::command_indices` and `Queue::pending_writes` in opposite orders between queue submission and BLAS compaction, and what executable test can prove the deadlock without relying on a vendor GPU?

## Exact identities

| Item | Value |
| --- | --- |
| Public repository | `gfx-rs/wgpu` |
| Exact public base | `7a655581ff7d3fd9f38e4ede2bdd9c16bfcba899` |
| Controlled repository | `teamleaderleo/wgpu` |
| CI base | `ci/wgpu-9981-base@a46d23fb94328a95beae6dff2aec6d1ec30e0d77` |
| Research branch | `research/wgpu-9981-lock-order` |
| Research head | `5fadad5f8283df7530a94e02bf8c89fc79c56a1a` |
| Internal draft PR | `teamleaderleo/wgpu#5` |
| Focused Actions run | `30759780777` |
| Last observed state | queued |
| Public issue | `gfx-rs/wgpu#9981` |
| Equivalent PR found | none by issue-number or source-term search |

## Source observation

Current `wgpu-core/src/device/queue.rs` contains both sides of the cycle:

- `allocate_submission()` acquires `device.command_indices.write()` and returns a `PendingSubmission` retaining that guard;
- the submit path later acquires `pending_writes` before completing the submission;
- `compact_blas()` acquires `pending_writes` first;
- while retaining it, `compact_blas()` later acquires `device.command_indices.write()`.

The declared hierarchy in `wgpu-core/src/lock/rank.rs` places `DEVICE_COMMAND_INDICES` before `QUEUE_PENDING_WRITES`. The compaction path therefore contradicts the repository's own rank order.

The public report describes the concrete interleaving:

```text
submit:       command_indices -> waits for pending_writes
compact_blas: pending_writes  -> waits for command_indices
```

## Materialized detector

The controlled detector reads exact source and asserts:

1. `allocate_submission()` contains `command_indices.write()`;
2. `compact_blas()` acquires `pending_writes.lock()` before `command_indices.write()`;
3. the rank declarations place `DEVICE_COMMAND_INDICES` before `QUEUE_PENDING_WRITES`.

This is a source-order discriminator. It is not yet a threaded target reproduction and does not prove every call reaches the cycle.

Opening the internal research PR also triggered the repository's ordinary pull-request workflows. The connected GitHub tool exposes run inspection and rerun operations but no cancel operation, so those extra controlled-fork runs could not be cancelled directly. No additional CI carriers should be created until queue state changes.

## Required executable reduction

A strong target test should avoid requiring an RTX-class GPU or a full Bevy renderer. Candidate approaches:

- a `wgpu-core` test backend that pauses after each first lock and coordinates two threads with barriers;
- lock-rank validation enabled in a test that reaches both paths and fails before deadlocking;
- extraction of the submission-index allocation into a helper whose guard lifetime can be tested against pending writes;
- a loom-style model of the two lock acquisitions if the concrete queue cannot be constructed without HAL state.

The test must have a timeout and must never leave blocked worker threads behind after failure.

## Design constraints

A correction cannot be selected from lock order alone. It must preserve:

- the `PendingSubmission` invariant that submission indices stay ordered;
- command encoder ownership in `pending_writes`;
- BLAS compaction copy and readback scheduling;
- reverse-order guard destruction already repaired by upstream commit `f9f55b7d510963b7308359dbbf2a7b91c5351ee5`;
- the declared ranked-lock hierarchy;
- concurrent `Queue` methods' public `&self` contract.

Likely variants include acquiring `command_indices` before `pending_writes` in compaction, shortening the `pending_writes` critical section, or allocating the compaction command index before entering the pending encoder. Each variant needs lifecycle and error-path review.

## Stop and promotion rules

Promote after a bounded threaded or ranked-lock test fails on exact base and passes after one order-preserving candidate. Stop duplicate implementation if a current equivalent PR appears. Reclassify as a broader queue-lock investigation if the first safe change exposes another rank cycle.

## Authority

Controlled branches, internal draft PRs, Actions, source detectors, and Fieldwork records are authorized. No public issue, pull request, comment, review, reaction, or email has occurred.
