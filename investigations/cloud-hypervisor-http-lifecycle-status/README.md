# Cloud Hypervisor HTTP lifecycle status drift

Updated: 2026-08-11

Upstream issues:

- https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8678
- https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8680

Research round: `research/rounds/2026-08-11-cloud-hypervisor-contract-edges/README.md`

Canonical source under investigation: `cloud-hypervisor/cloud-hypervisor` `main`
Exact source head: `a658c9f9fd0c4e0363004361d73ac8733fa24fd0`
Primary owners: `vmm/src/api/http/mod.rs`, `vmm/src/vm.rs`, `vmm/src/api/openapi/cloud-hypervisor.yaml`
Current state: **source-confirmed contract drift; execution/state matrix pending**
Upstream-contact state: **disabled / no contact performed**

## TL;DR

Cloud Hypervisor's OpenAPI document distinguishes two lifecycle failure classes for pause/resume/shutdown/reboot/power-button:

- `404` when the relevant VM object has not been created;
- `405` when the VM exists but the requested lifecycle operation is invalid in its current state.

Current HTTP translation does not implement that second branch. `api_error_status_code()` special-cases a small set of missing-object and validation errors, then maps every other `ApiError` to 500. `VmNotRunning`, `VmMigrating`, `InvalidStateTransition`, and other lifecycle errors therefore have no dedicated HTTP mapping.

The bounded question is:

> Which internal VM-state distinctions should be made explicit so the HTTP API can distinguish absent VM, incompatible lifecycle state, migration/restoration conflicts, and genuine server failures without hiding them behind 500?

Do **not** start by adding `VmNotRunning => 405`. The same error vocabulary can represent different state situations, and HTTP 405 itself deserves contract review.

## Explain like I'm five

The API has a rulebook saying:

```text
no VM exists        -> one kind of answer
VM exists, wrong time to do this -> another kind of answer
server broke        -> another kind of answer
```

The current code only recognizes a few of those cases. Many ordinary “wrong time” answers fall into the same bucket as “server broke.”

The investigation first makes a table of what the server actually knows in each state. Then a patch can give each state the right public answer.

## Why care

Management software makes decisions from status codes. A missing VM can trigger create/reconcile logic. A lifecycle conflict can trigger a different transition or a wait. A true 500 can trigger server-failure handling.

Collapsing those into 500 makes ordinary state-machine behavior look like a VMM failure and prevents callers from reacting precisely.

The OpenAPI document is also executable documentation for client generation and integration. A documented status the server never emits is a cross-layer contract drift even when every individual layer behaves consistently with its own local assumptions.

## Exact current-source observations

### HTTP mapper

At exact head `a658c9f9fd0c4e0363004361d73ac8733fa24fd0`, `api_error_status_code()` maps:

```text
VmNotCreated
VmMissingConfig
NoDeviceToRemove
UnknownDeviceId
    -> 404

IdentifierNotUnique
DuplicateDevicePath
    -> 409

other ConfigValidation
    -> 400

everything else
    -> 500
```

There is no lifecycle-state branch.

### VM error vocabulary

`vmm/src/vm.rs` currently contains distinct variants including:

```text
VmNotCreated
VmAlreadyCreated
VmNotRunning
VmMigrating
VmRestoring
InvalidStateTransition(from, to)
```

Those variants give the lower layer some state vocabulary, but the HTTP mapper currently only consumes `VmNotCreated` from this group.

### OpenAPI contract

The current OpenAPI file advertises:

| endpoint | absent/not-created response | wrong lifecycle state response |
|---|---:|---:|
| `vm.pause` | 404 | 405 |
| `vm.resume` | 404 | 405 |
| `vm.shutdown` | 404 | 405 |
| `vm.reboot` | 404 | 405 |
| `vm.power-button` | 404 | 405 |

Examples from the descriptions distinguish “not created” from “not booted”, “not paused”, or “not started”.

So the public description already expresses a state distinction that the generic HTTP error mapper cannot currently preserve.

## Core invariant

A client-visible lifecycle response should preserve the operation owner's state distinction:

```text
resource absent
resource present + transition invalid
operation temporarily blocked by migration/restore
request/config invalid
genuine internal failure
```

Those classes should not collapse solely because they travel through `ApiError`.

## State matrix to execute

Exercise the same endpoint set from controlled VM states and record the complete source chain plus HTTP result.

| VM/VMM state | create | boot | pause | resume | shutdown | reboot | power-button |
|---|---|---|---|---|---|---|---|
| no VM | observe | observe | observe | observe | observe | observe | observe |
| created, never booted | observe | control | observe | observe | observe | observe | observe |
| running | observe | observe | control | observe | control | control | control |
| paused | observe | observe | observe | control | observe | observe | observe |
| migrating | observe | observe | observe | observe | observe | observe | observe |
| restoring, where controllable | observe | observe | observe | observe | observe | observe | observe |

For every cell capture:

1. request endpoint/method;
2. starting VM state;
3. internal `VmError` source chain;
4. HTTP status;
5. JSON error body;
6. OpenAPI-listed statuses;
7. post-request VM state;
8. whether retrying the same request can become valid without another lifecycle transition.

## Primary discriminators

### Discriminator A — no VM vs created-but-stopped

For `pause`, `shutdown`, `reboot`, and `power-button`:

- no VM should preserve the missing-object class;
- created-but-never-booted should preserve the existing-object/wrong-state class.

If both paths currently return the same `VmError`, the lower lifecycle API owns the missing distinction and an HTTP-only patch is too late.

### Discriminator B — paused vs running

`pause` and `resume` should trade control/invalid-state roles as the VM moves between running and paused.

This checks whether the error source already carries enough transition context through `InvalidStateTransition` or whether endpoint wrappers reduce it to a broader error.

### Discriminator C — migration

A migration-owned VM already has `VmMigrating` vocabulary. Determine whether lifecycle endpoints preserve that variant, wrap it, or turn it into another broad state error.

This links to the separate migration lifecycle scout without claiming the same owner.

## Candidate repair boundaries

Keep several possibilities alive until the matrix runs.

### Candidate A — improve lower-layer state errors

Use distinct VM errors for:

```text
no VM object
VM exists but is not running
invalid explicit state transition
migration/restore conflict
```

Then make HTTP mapping a simple translation of already-correct semantics.

This leads if the matrix shows the same lower error being used for semantically different states.

### Candidate B — map existing distinct errors

If current endpoint paths already preserve distinct variants, add narrow HTTP mappings and matching tests.

This is the smallest product change when lower-layer vocabulary is already sufficient.

### Candidate C — reconcile OpenAPI instead of emitting 405

HTTP 405 conventionally describes a method disallowed for a resource and is associated with an `Allow` header. A lifecycle conflict may fit 409 more naturally, or Cloud Hypervisor may intentionally use 405 as its API convention.

If project history or surrounding endpoints show that the OpenAPI status table is stale, repair the public contract instead of forcing implementation toward a questionable code.

The investigation should select this with project evidence, not generic HTTP taste.

## Negative controls

A candidate must preserve unrelated mappings:

1. unknown device ID -> existing 404 behavior;
2. duplicate identifier/path -> existing 409 behavior;
3. malformed JSON -> 400;
4. ordinary config validation -> 400 unless a currently documented special case applies;
5. a genuine device/VMM internal error -> 500;
6. rate-limit/pending-removal path -> existing 429 where applicable.

## Adjacent contexts

### D-Bus API

Cloud Hypervisor also exposes D-Bus lifecycle operations. D-Bus has different public error semantics, so do not force HTTP status design into that layer. Use it only to see whether the operation owner returns richer state information before protocol translation.

### `ch-remote`

Record how the CLI renders each HTTP status/body. A server-side repair should improve machine-readable state without creating misleading CLI prose or losing the internal error chain.

### Event-monitor lifecycle work

Current upstream main includes the shutdown-event gating work that recently landed. Those tests establish reliable completion points for shutdown/delete/create/boot sequences and can make lifecycle matrix fixtures less timing-sensitive.

Reuse the event gate; do not reopen that landed test lane.

## Evidence boundary

Established here:

- exact current HTTP mapper has no lifecycle-state mapping;
- `VmNotRunning` and other state-oriented errors exist in current VM error vocabulary;
- current OpenAPI advertises separate 404 and 405 lifecycle cases for five endpoints;
- upstream issues 8678 and 8680 describe the observed mismatch;
- current upstream main is `a658c9f9fd0c4e0363004361d73ac8733fa24fd0` for this source pass.

Still unproven here:

- exact runtime error chain for every state/endpoint matrix cell;
- whether 405 remains the intended public status after protocol review;
- whether the smallest repair belongs in VM lifecycle errors, endpoint wrappers, HTTP translation, OpenAPI, or a combination;
- runtime parity across HTTP and D-Bus callers;
- current integration-test results for a candidate.

## Stop condition

Select a repair boundary only after:

1. no-VM and created-but-stopped states have been executed for the affected endpoints;
2. running/paused controls establish transition-specific behavior;
3. at least one migration conflict path is inspected if reachable without widening the harness excessively;
4. the internal error owner for each differing state is known;
5. the intended public status convention is supported by current project evidence;
6. unrelated 400/404/409/429/500 controls remain stable.

## Reopening trigger

Reopen broader API design only if:

- the same lower error genuinely needs several public meanings and endpoint context is required to disambiguate it;
- HTTP and D-Bus require incompatible operation-owner semantics;
- migration/restoration introduces a state class the existing VM state machine cannot represent cleanly;
- upstream changes the OpenAPI lifecycle contract or error hierarchy before execution.

## Next safe action

Create the smallest integration/unit harness that can put the VMM into no-VM, created, running, and paused states and record the source error + HTTP response for `pause`, `resume`, `shutdown`, `reboot`, and `power-button`. Use the landed shutdown event gate for deterministic lifecycle completion. Preserve the baseline matrix before touching product code.
