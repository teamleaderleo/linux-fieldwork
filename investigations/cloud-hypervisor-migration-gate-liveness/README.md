# Cloud Hypervisor migration Gate enqueue + cleanup liveness

Updated: 2026-08-12
Owning issues: #603 (Gate enqueue), #581 (cleanup terminal condition)
Worker/variant: LF-R603E
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Final execution head: `7766a35682179757e06ac72a8f1b3f3b30d4c7e0`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; Cloud Hypervisor upstream remained read-only

## Disposition

**#603: PROVEN / CANDIDATE READY FOR INDEPENDENT REVIEW.**

**#581: PROVEN at product `SendAdditionalConnections` level / selected channel-close candidate composes cleanly with #603.**

The two defects occur consecutively in one failed-migration request:

```text
full bounded work queue + worker failure
-> current wait_for_pending_data blocks publishing Gate (#603)
-> nonblocking Gate repair reaches cleanup
-> current cleanup can lose Disconnect while queue is full and hang joining a survivor (#581)
```

The final selected composition uses the independently validated #603 nonblocking Gate candidate followed by the independently validated #581 channel-close cleanup candidate. This carrier proves those two selected candidates work together.

## Exact losing discriminators

### #603 baseline

The real `SendAdditionalConnections::wait_for_pending_data()` is called with a capacity-one queue already holding `Memory`, `worker_error=true`, and a receiver kept alive without capacity to accept Gate. Current `SyncSender::send(Gate)` blocks until the harness kills the test:

```text
GATE_BASELINE_RC=124
```

A healthy-worker control begins with the same full queue, drains the queued Memory, receives Gate, notifies the main thread, and completes normally.

### #581 after only #603 is repaired

The stacked test uses one failed worker and one surviving worker. With the #603 Gate candidate applied, the main thread observes `worker_error` and reaches the unmodified product `cleanup()`.

Current cleanup calls `try_send(Disconnect).ok()` while the bounded queue is full. A Disconnect is lost; the survivor later drains the queued Memory and then blocks on `recv()` while the sender remains alive. The join therefore reaches the harness deadline:

```text
GATE_ONLY_SURVIVOR_RC=124
```

This promotes #581 beyond its earlier reduced channel proof: the product `SendAdditionalConnections` failure path itself can strand a surviving worker after #603's earlier block is removed.

## Selected candidates

### Commit boundary A — #603 Gate enqueue

Replace blocking Gate publication with the same progress discipline already used by `send_chunk()`:

```text
retain unsent Gate
-> check worker_error
-> try_send(Gate)
-> Full: short sleep and retry
-> Disconnected: open Gate, cleanup, return error
```

Any previously delivered Gate is opened before error cleanup, so workers already waiting at the synchronization point can leave it.

Product-only diff digest:

```text
sha256:5c1bb18138a3cfc542b698830f15b2ca5ab97bf4611173fe2690a57f3423b553
```

Product-only size: `+23/-4`, one file.

### Commit boundary B — #581 cleanup terminal condition

The selected #581 candidate closes the original work channel instead of trying to fit terminal `Disconnect` messages into the bounded queue:

```text
replace self.message_tx with an already-disconnected placeholder
-> drop original sender
-> workers drain already-queued work
-> recv() channel disconnect becomes normal cleanup completion
-> join workers
```

Mutex poisoning remains an error. Ordinary channel disconnection is treated as successful worker termination only after the shared receiver lock was acquired.

Product-only diff digest in this composition:

```text
sha256:98f86a493e8f451af3f9af9aed25450e0da75bae2fc36df318f3374a3f89fe1d
```

Product-only size: `+14/-16`, one file.

Combined selected product diff:

```text
sha256:a94eafd97e0163723df2d1474e1dbc7fb6e84fc910f4c74b1d836b624064c995
```

Combined product-only size: `+37/-20`, exactly `vmm/src/migration/transport.rs`.

A retry-Disconnect cleanup experiment was also executed and made the focused tests pass, but the channel-close design has the stronger ownership rule: cleanup termination no longer competes for bounded work-queue capacity. The retry variant is superseded by the selected channel-close composition.

## Final execution receipt

Final run / job:

```text
31569805768 / 94029154261
```

Artifact:

```text
9130890641
sha256:f11dbeb75e4855a14e5ece7db11cbed809f9ce1efddcaea9b18324b838b946bc
```

Exact source was refreshed after completion and remains:

```text
1af93ac7035cda77cd87b0c18b1134ebb0928052
```

Rust: `1.89.0`.

Passed in the final composition run:

```text
exact source pin
probe application / test discovery
baseline full-queue healthy-worker control
baseline #603 expected timeout: RC 124
#603 Gate candidate application
#603 focused candidate behavior
Gate-only #581 product-level expected timeout: RC 124
#581 channel-close candidate application
combined three-cell focused convergence matrix
hosted /dev/kvm permission gate
cargo test --locked -p vmm --features kvm --lib
  -> 106 passed; 0 failed
cargo clippy --locked -p vmm --features kvm --lib --tests --
  -D warnings -A unfulfilled-lint-expectations
cargo fmt --all -- --check
git diff --check
complete product-only diff review
```

The earlier broad-test failure on this carrier was runner-only: `/dev/kvm` existed as `root:kvm 0660`, while the hosted test process lacked access. Granting the runner read/write permission made the same candidate bytes pass all 106 tests.

## Review / packaging recommendation

Keep the product changes as two stacked commits even if they travel in one PR:

1. #603: make Gate enqueue observe worker failure under bounded-queue backpressure;
2. #581: make cleanup terminate workers by closing the work channel independent of queue capacity.

Each commit has an independent losing discriminator, and the final stacked test proves the actual failed-migration request converges only after both boundaries are repaired.

No network guest migration is required to prove these channel owners. Network-stalled worker I/O remains a separate timeout/liveness concern tracked by existing migration transport work.
