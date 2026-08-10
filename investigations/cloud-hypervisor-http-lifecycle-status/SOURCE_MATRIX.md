# Cloud Hypervisor HTTP lifecycle source matrix

Updated: 2026-08-11

Upstream issues:

- https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8678
- https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8680
- historical intent: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/7774
- accepted predecessor: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8320

Current upstream head reviewed: `915d359f97475b1a39d8561f8db514da9e692d19`

Relevant source blobs are unchanged from the previous Fieldwork boundary:

- `vmm/src/lib.rs`: `efdf9826f2c8503d394f15a627acec7a929176b1`
- `vmm/src/api/http/mod.rs`: `839a49379d89d3120693eabb82010bf98662a259`
- `vmm/src/vm.rs`: `dbd3ab104aa8745420cf3f2243e0a70563cb58bd`

Execution state: **source matrix refined; runtime matrix still pending**
External-contact state: **disabled / no contact performed**

## TL;DR

The current source already knows the difference between these two API-visible states:

```text
no VM            = VmOwnership::None + vm_config=None
created/unbooted  = VmOwnership::None + vm_config=Some
```

`vm_info()` exposes the second state as `VmState::Created`.

Several lifecycle methods discard that distinction because they match only on `VmOwnership`. `pause`, `resume`, `shutdown`, and `power-button` return `VmNotRunning` for both states. `reboot` returns `VmNotCreated` for both states. Therefore a HTTP-only mapping cannot produce both a missing-object response and a lifecycle-conflict response correctly.

The accepted predecessor PR gives a strong policy signal: its reviewed and merged rationale says state conflicts such as `VmNotRunning` and `VmAlreadyCreated` should map to **409 Conflict**. At that time `micro_http::StatusCode` lacked `Conflict`. Current Cloud Hypervisor already uses `StatusCode::Conflict` for duplicate configuration errors, so that blocker has disappeared.

The leading repair boundary is now two-layered:

1. preserve the existing no-VM vs created/unbooted distinction at the `RequestHandler` lifecycle boundary;
2. map typed state conflicts to 409 while leaving real operation failures at 500.

The current OpenAPI 405 entries should be reconciled to the selected 409 contract unless new project evidence overturns the accepted predecessor's intent.

## Canonical VMM state identity

Current `vm_info()` provides the useful oracle:

| VMM ownership | config | API-visible state |
|---|---|---|
| `None` | none | no VM / `VmNotCreated` |
| `None` | present | `VmState::Created` |
| `Owned(vm)` | present | `vm.get_state()` |
| `Migration` | present | saved `VmInfoResponse` from migration start |

This means `VmOwnership::None` alone is insufficient to classify a lifecycle request.

## Source matrix

### No VM vs created/unbooted

| action | no VM today | created/unbooted today | source owner |
|---|---|---|---|
| pause | `VmNotRunning` | `VmNotRunning` | `Vmm::vm_pause()` |
| resume | `VmNotRunning` | `VmNotRunning` | `Vmm::vm_resume()` |
| shutdown | `VmNotRunning` | `VmNotRunning` | `take_owned_or()` call in `Vmm::vm_shutdown()` |
| reboot | `VmNotCreated` | `VmNotCreated` | `take_owned_or()` call in `Vmm::vm_reboot()` |
| power-button | `VmNotRunning` | `VmNotRunning` | `Vmm::vm_power_button()` |
| snapshot | `VmNotRunning` | `VmNotRunning` | `Vmm::vm_snapshot()` |
| coredump | `VmNotRunning` | `VmNotRunning` | `Vmm::vm_coredump()` when enabled |

The HTTP layer receives these through endpoint-specific `ApiError` wrappers whose immediate source is the `VmError`, so the lost state distinction cannot be recovered there without endpoint/string heuristics.

### Migration

`VmOwnership::Migration` is already explicit. Direct lifecycle methods return `VmMigrating`, and `take_owned_or()` restores the migration ownership value before returning that error. This state does not need to be inferred from text.

### Owned VM, incompatible state

The error quality varies by operation:

- `Vm::pause()` asks `VmState::valid_transition(Paused)`, but converts the typed transition failure into `MigratableError::Pause(anyhow!("Invalid transition: {e:?}"))`.
- `Vm::resume()` does the equivalent conversion for `Running`.
- `Vm::snapshot()` returns a textual `MigratableError::Snapshot` when the VM is not paused.
- coredump has its own running/paused check and textual failure.
- `Vm::shutdown()` calls `valid_transition(Shutdown)` directly and therefore retains a typed `VmError::InvalidStateTransition` when that path fails.

This is important for the HTTP repair: mapping the outer `VmError::Pause`, `VmError::Resume`, or `VmError::Snapshot` wholesale to 409 would misclassify genuine pause/resume/snapshot failures that deserve 500.

## Historical contract evidence

Issue 7774 proposed semantically useful client status codes, including 409 for state conflicts. A maintainer endorsed the direction.

The merged predecessor PR 8320 then implemented the first slice, 404 for `VmNotCreated` / `VmMissingConfig`. Its rationale explicitly records that `VmNotRunning` / `VmAlreadyCreated` should ideally be 409, with one blocker: the then-current `micro_http::StatusCode` had no `Conflict` variant.

Current source now uses `StatusCode::Conflict` for `IdentifierNotUnique` and `DuplicateDevicePath`. The original technical blocker no longer exists.

This is stronger project-specific evidence for 409 than the stale OpenAPI 405 entries.

## Why an HTTP-only patch loses

### `VmNotRunning => 409`

This would correctly classify a created/unbooted pause, but it would also turn a pause against an absent VM into 409 even though the API already treats missing VM objects as 404.

### `VmNotCreated => 404`

This mapping already exists. It makes the current created/unbooted reboot path look like an absent VM because `vm_reboot()` drops the config distinction before the HTTP layer sees the error.

### `VmError::Pause | Resume | Snapshot => 409`

These wrappers contain both lifecycle-precondition failures and real operational failures. A blanket mapping would hide server/device/hypervisor errors behind a client-state status.

## Leading candidate boundary

### Part 1 — classify `VmOwnership::None` with config state

Use the facts already present in `Vmm`:

```text
ownership None + no config  -> VmNotCreated
ownership None + config     -> VmNotRunning (state conflict)
```

Apply the same classification consistently to lifecycle operations that currently only inspect ownership. A small helper may be justified if it avoids seven copies while keeping the call sites obvious.

Reboot needs particular care because its current fallback error is `VmNotCreated`; created/unbooted reboot should remain an existing-object lifecycle conflict.

### Part 2 — map direct state errors to 409

Strong candidates for direct 409 mapping after Part 1:

- `VmNotRunning`
- `VmAlreadyCreated`
- `VmMigrating`
- `VmRestoring`

`VmMigrating` / `VmRestoring` may deserve a narrower policy decision if callers are expected to retry after external progress. 409 is still the leading family because the resource exists and current state prevents the operation.

### Part 3 — preserve typed transition failures

Pause/resume/snapshot/coredump need a typed way to distinguish state-precondition failure from operational failure before their outer wrappers can map safely.

Candidate to test: retain `InvalidStateTransition` as an error source instead of formatting it into an `anyhow` string, then teach the HTTP classifier to find that typed cause through the chain. Do not select this until a focused unit test proves the source chain is preserved exactly as intended.

A second option is a dedicated typed lifecycle-conflict error at the VMM/request boundary. Prefer whichever produces the smaller, clearer diff without duplicating the VM state machine.

## OpenAPI direction

The current 405 descriptions are describing VM state, while the HTTP request dispatcher itself returns 400 for an unsupported HTTP method.

Project history points to 409 for VM state conflicts. The likely public-contract cleanup is therefore:

```text
404 = VM object/config absent
409 = VM exists but current lifecycle state blocks the operation
500 = genuine VMM/device/hypervisor failure
```

A separate future HTTP-method cleanup can decide whether unsupported verbs should become 405 with an `Allow` header. That concern should not force VM-state conflicts into 405.

## Test plan without guest hardware

The repository already contains a useful seam in `fuzz/fuzz_targets/http_api.rs`: it drives the real HTTP routes against a stub `RequestHandler`.

A focused status test can reuse the same idea with a configurable stub returning exact `VmError` values. This can verify:

- absent VM error -> 404;
- direct state conflict -> 409;
- validation conflict -> existing 409;
- malformed request -> 400;
- real internal error -> 500;
- unsupported method -> current 400 control.

The ownership/config classification itself belongs in `vmm/src/lib.rs` tests or a small helper test. Running/paused transition coverage can remain a focused VM/integration gate where needed.

## Runtime matrix still required

Source reading selects the likely owner, but retain these runtime cells before proposing an upstream packet:

1. no VM: pause/resume/shutdown/reboot/power-button;
2. created/unbooted: same five operations;
3. running: repeated resume and repeated boot controls;
4. paused: repeated pause plus valid resume;
5. one migration-owned lifecycle request;
6. snapshot from running vs paused where practical.

Record internal error chain, HTTP status/body, and post-request VM state.

## Evidence boundary

Established:

- current upstream head is `915d359f...` and relevant VMM/API blobs are unchanged from the prior Fieldwork source pass;
- `vm_info()` distinguishes no VM from created/unbooted using `vm_config`;
- lifecycle methods currently discard that distinction in several paths;
- migration has a distinct typed ownership error already;
- pause/resume state-transition failures are converted into textual `anyhow` payloads;
- the merged predecessor explicitly selected 409 as the desired state-conflict family once library support existed;
- current source has `StatusCode::Conflict` support.

Pending:

- executable baseline matrix on current main;
- exact type-preserving design for nested transition failures;
- candidate diff and tests;
- any KVM/MSHV integration result;
- maintainer decision on final OpenAPI wording.

## Next safe action

Implement the smallest local candidate on a controlled fork branch only after refreshing the fork head: first fix `None + vm_config` classification and add no-guest HTTP classifier tests. Keep transition-chain preservation as a second commit or competing variant so the reviewer can see which complexity is actually required.
