# Terminal receive failure finalization

Updated: 2026-08-11
Owning issue: #580
Cloud Hypervisor source: `915d359f97475b1a39d8561f8db514da9e692d19`
External-contact state: false; none occurred

## TL;DR

`ReceiveMigrationState::Aborted` is not the common terminal error path for receive migration.

`vm_receive_migration()` converts errors returned by `vm_receive_migration_step()` into the `Aborted` state, writes an error response, and eventually reaches the finalizer that emits `vm.migration-receive-failed`, clears `self.vm`, and clears `self.vm_config`.

Transport errors outside the step function use `?` directly. In particular, request reads and response writes can return from `vm_receive_migration()` before that finalizer. The API layer only wraps the returned error; it does not repair state.

Because `vm_receive_config()` installs `self.vm_config` before the migration protocol is complete, a disconnect after configuration can return an API error while leaving partial receive state installed.

## Explain like I'm five

The receiver has a cleanup door marked “migration failed.” If an ordinary protocol command goes wrong, the code walks through that door and cleans the room.

If the network connection itself breaks while reading the next command or writing a reply, the code can take a side exit. That side exit reports an error but skips the cleanup door.

By then the receiver may already have copied the incoming VM configuration into its own state.

## Exact control flow

The main receive loop contains:

```text
while !state.finished() {
    req = Request::read_from(&mut socket)?

    (response, new_state) = match vm_receive_migration_step(...) {
        Ok(next) => (OK, next)
        Err(_)   => (ERROR, Aborted)
    }

    state = new_state
    response.write_to(&mut socket)?
}

match state {
    Aborted => {
        event migration-receive-failed
        self.vm = None
        self.vm_config = None
        return Err(...)
    }
    Completed => event migration-receive-finished
}
```

The `?` on request read and response write bypasses the final `match`.

The initial `listener.accept()?` is an even earlier example: TCP accept, socket-option setup, or TLS handshake failure returns before the protocol loop and before the same finalizer.

## No outer cleanup owner

`VmReceiveMigration` in `vmm/src/api/mod.rs` performs:

```text
vmm.vm_receive_migration(data)
    .map_err(ApiError::VmReceiveMigration)
```

and sends that response. It does not clear receive state or emit a migration failure event.

Therefore cleanup must be owned inside the VMM receive operation or an explicit guard it creates.

## Partial-state reachability

`vm_receive_config()` parses the incoming configuration and then executes:

```text
self.vm_config = Some(vm_migration_config.vm_config)
```

before subsequent receive protocol completion.

A concrete sequence is therefore:

```text
Start succeeds
Config payload succeeds
vm_receive_config installs self.vm_config
receiver sends Config response OR waits for next request
peer disconnects / write fails / next read fails
vm_receive_migration returns via ?
Aborted finalizer is skipped
self.vm_config remains present
```

Later state receipt can materialize additional VM state before the final Complete/CompletePaused command, so the same finalization boundary should be tested at more than one protocol phase.

## Why care

A failed incoming migration should have one externally coherent terminal result:

- a failure event;
- no half-installed incoming VM/config state unless a documented recovery mode explicitly keeps it;
- a predictable ability to retry or perform another VM lifecycle operation.

Direct transport errors currently have a separate exit from protocol-step failures.

## First executable matrix

No guest workload is required for the early rows.

### A. Pre-protocol TLS failure

- receiver emits ready;
- client sends invalid TLS or closes;
- API returns error;
- inspect failure event and post-call VM/config state.

### B. Disconnect before Config

- Start succeeds;
- peer disconnects before next request;
- request read fails directly.

Expected cleanup requirement: failed event once; no VM/config retained.

### C. Disconnect after Config

- Start succeeds;
- Config succeeds and is acknowledged if needed;
- peer closes before the next command.

This is the strongest small partial-state discriminator because `self.vm_config` is already installed.

After the API call returns, query `vm_info()` or otherwise inspect `vm_config` through a controlled unit seam. Baseline source predicts config remains visible because the finalizer was skipped.

### D. Protocol-step error control

Send an invalid command for the current state while keeping the connection alive long enough to receive the error response.

This should use the current `Aborted` path, emit the failure event, and clear state.

### E. Error-response write failure

Cause `vm_receive_migration_step()` to return an error, then close/reset before the receiver writes `Response::error()`.

The state variable is assigned `Aborted`, but `response.write_to()?` can still return before the final `match`. This distinguishes “state says Aborted” from “finalizer actually ran.”

## Candidate boundary

The repair should establish one terminal finalization owner for the whole receive attempt, not only protocol-step failures.

Properties:

1. successful completion emits `migration-receive-finished` once and retains the completed VM;
2. any terminal error emits `migration-receive-failed` once;
3. failed incoming partial state is cleared consistently;
4. cleanup of auxiliary connections is not skipped;
5. an error while sending the peer's error response cannot suppress local cleanup;
6. the original failure remains the returned diagnostic, with cleanup failures recorded without replacing it unless project policy says otherwise.

A small scope/guard around the receive attempt is preferable to duplicating cleanup beside every `?`.

## Relation to zero-progress and cancellation findings

The truncated-memory `Ok(0)` loop recorded in `ZERO_PROGRESS.md` can prevent the function from reaching *any* terminal finalization until forward-progress handling is fixed.

The connected-but-idle auxiliary worker cancellation problem can similarly delay connection cleanup. Those are execution/liveness prerequisites around the same terminal-state contract, but they should remain independently testable.

## Evidence boundary

This finding is established from exact current control flow and the API caller. It has not yet been executed in a Cloud Hypervisor binary by Fieldwork.

The post-Config residual-state consequence follows from the observed assignment to `self.vm_config` plus the direct `?` exit. Runtime/unit confirmation remains required before proposing product code.

## Next step

Build the five-row local receive matrix and assert both event sequence and post-call VMM state. Promote a common finalizer candidate only after the baseline shows which rows currently bypass it.

## Authority

No upstream issue, pull request, comment, review, email, reaction, or other interaction is authorized or performed by this investigation.
