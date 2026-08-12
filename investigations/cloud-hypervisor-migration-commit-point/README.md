# Cloud Hypervisor — migration remote commit / source rollback boundary

Updated: 2026-08-12
State: SOURCE-CONFIRMED / EXECUTION DESIGN PENDING
Owning issue: #606
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; none occurred

## TL;DR

Cloud Hypervisor currently has no explicit representation of the point after which source rollback is unsafe.

The receiver handles `Complete` by resuming the destination **before** it writes the `OK` response. If that response is lost, the source sees an ordinary migration error and generic error recovery can resume the source too.

Even when the source does receive the `OK`, several source-local cleanup steps remain fallible. Those errors are also returned as ordinary migration failures and select the same source-resume recovery.

The protocol therefore conflates at least three outcomes:

```text
not committed remotely
committed remotely
commit outcome unknown
```

All three currently collapse into `Result<(), MigratableError>` at the migration-worker boundary.

## Explain like I'm five

Moving a VM is like handing over the only key to a running machine.

The destination says “I have it” only after it has already started the machine. If that message gets lost, the source thinks the handoff failed and can start its copy again.

Now there can be two machines running when there should only be one.

The fix needs a real handoff state, not just “success” or “error.”

## Why care

A live migration must end with one authoritative VM owner.

After the destination has resumed, bringing the source back because a final acknowledgement or cleanup step failed can create two runnable instances with the same guest identity and shared external resources.

Fieldwork already has narrower consequences in the same recovery window:

- #583 — source disk locks are not reacquired before failed-migration resume;
- #584 — vhost-user backend teardown is not reconstructed before source resume.

This investigation owns the broader question: **when is source rollback no longer legal at all?**

## Current state

- State: `SOURCE-CONFIRMED`
- Exact source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
- Primary owners: `vmm/src/lib.rs`, `vmm/src/migration/worker.rs`, `vm-migration/src/protocol.rs`
- First incomplete step: executable lost-Complete-ACK discriminator
- Cleanup state: no runtime resources created
- External-contact state: false; none occurred

## Receiver commit ordering

`ReceiveMigrationState::StateReceived` handles `Command::Complete` by resuming the VM and then returning `Completed`:

```text
vm.resume()?
Ok(Completed)
```

The outer receive loop only afterward does:

```text
state = new_state
Response::ok().write_to(socket)?
```

Therefore:

```text
destination resume
happens-before
Complete OK reaches source
```

If the response write fails, destination execution has already crossed the guest-running boundary.

## Source interpretation

The sender uses:

```text
send_request_expect_ok(Complete)?
```

A missing response, socket failure, or error response is returned as an ordinary migration `Err`.

`MigrationWorkerResult` contains:

```text
vm
migration_result: Result<(), MigratableError>
initial_vm_state
preserve_source
```

It does not carry whether `Complete` was sent, acknowledged, remotely applied, or outcome-unknown.

`Vmm::check_migration()` handles `Err` by attempting to restore source operation:

```text
if source began Running and local VM is Paused:
    vm.resume()
stop_dirty_log() best effort
self.vm = Owned(vm)
```

That policy is valid only before remote commit is possible.

## Lost-ack failure sequence

The highest-value discriminator is:

```text
source sends Complete
receiver processes Complete
receiver resumes destination
receiver cannot deliver OK / connection dies
source receives no success response
source worker returns Err
source error recovery resumes local VM
```

At the point the source sees the transport error, remote state is ambiguous:

```text
receiver might not have received Complete
receiver might have received but not resumed
receiver might already be Running
```

Current source assumes the first family and rolls back locally.

## Post-ack cleanup failures

Even a successful Complete acknowledgement does not end fallibility on the source.

After `send_request_expect_ok(Complete)` succeeds, current source can still fail in:

- `vm.stop_dirty_log()` for precopy;
- postcopy serve-thread join/result propagation;
- `vm.complete_migration()` / component completion.

Those failures are also returned as migration `Err` and trigger generic source recovery.

This means the unsafe region is not only “ACK lost”; it extends through source-local post-commit cleanup.

## Existing `Abandon` mechanism and why it stops helping here

The protocol defines `Command::Abandon`, and the receiver handles it through the clean `Aborted` terminal state.

That is useful **before** remote commit for source-local failures while the control connection still works.

It is not sufficient after `Complete` has been sent because the receiver may already have resumed. Sending or inferring `Abandon` after an uncertain Complete would itself need transaction ordering.

## Required state model

The worker outcome needs at least this semantic distinction:

```text
PRE_COMMIT_FAILURE
REMOTE_COMMITTED
REMOTE_COMMIT_UNKNOWN
```

Names may differ, but one `Result<(), Error>` is not expressive enough for safe source ownership recovery.

### Pre-commit failure

Source rollback/resume can be valid. Best-effort `Abandon` should let the receiver clean up explicitly when the control socket is healthy.

### Remote committed

Source must not be resumed as a rollback. Source cleanup failure remains an operational error, but ownership has moved.

### Commit unknown

Safety and availability conflict. With the current one-round-trip commit protocol, blindly resuming the source is unsafe because destination execution may already have begun.

## Candidate design families

### A — safety-first with current protocol

Once the source has successfully transmitted `Complete`, treat a missing acknowledgement as non-rollbackable/unknown. Do not resume the source automatically.

This can prevent split brain without changing the wire protocol, at the cost of requiring operator/orchestrator reconciliation for an uncertain handoff.

### B — explicit two-phase handover

Separate readiness from execution:

```text
receiver restored and ready
source acknowledges handover decision
receiver resumes
receiver confirms committed
```

This still needs failure policy between phases, but it can place the irreversible step at an explicit protocol boundary.

### C — transaction identity + reconciliation

Give migration a durable transaction identity and allow source/orchestrator to query receiver outcome before deciding rollback after connection loss.

This is broader but gives a principled answer to uncertain commit state.

## First executable discriminator

Use a controlled source/receiver fixture where the receiver can deliberately close after processing Complete but before the response is delivered.

Capture:

- receiver VM state at close;
- whether destination emitted resume/finished events;
- source `send_request_expect_ok` result;
- source migration worker result;
- source post-error VM state / resume action.

Required baseline evidence:

```text
destination crossed Running
source classified migration Err
source selected rollback/resume
```

A fake/test VM state owner is preferable if it can exercise the real migration worker decision without KVM. Otherwise use the existing live-migration integration harness with a controlled receiver fault.

## Evidence boundary

Established from exact current source:

- receiver resumes before writing Complete `OK`;
- response write is fallible;
- sender treats missing Complete response as ordinary error;
- migration worker result has no commit-state field;
- all errors feed generic source recovery;
- source-local fallible cleanup remains after acknowledged Complete.

Not yet executed:

- lost-ACK end-to-end state observation;
- post-ACK injected cleanup failure;
- candidate state representation;
- protocol compatibility analysis.

No claim is made that a public/untrusted network can reach the migration endpoint. The current claim is a correctness and ownership-safety property of the migration protocol under ordinary transport failure.

## Next step

Build the lost-Complete-ACK discriminator first. Do not start with post-ACK cleanup injection: the lost-ACK window is more fundamental and determines whether the current protocol can safely support automatic source rollback at all.

## Authority

No upstream issue, pull request, comment, review, reaction, email, or other external interaction is authorized or performed.
