# Cloud Hypervisor contract-edge scout — 2026-08-11

## TL;DR

This pass deliberately stayed beside the existing cache, ACPI, shutdown-event, and newly promoted virtio-pci queue-restore work.

Three adjacent seams survived source/history review:

1. **Promote to a bounded API-state investigation:** the HTTP error mapper still turns most VM lifecycle errors into `500 Internal Server Error`. In particular, `VmNotRunning` falls through to 500 on current main. The two live upstream reports expose a real contract split: “there is no VM” and “there is a VM, but this lifecycle operation is invalid now” currently share error vocabulary even though the API contract wants different client-visible outcomes.
2. **Keep warm as a lifecycle-ownership probe:** the VMM event loop still carries explicit TODOs around exit, reset, and guest-exit handling while `VmOwnership::Migration` owns the VM. No current defect is claimed here. The source itself marks the ownership transition unresolved, which makes shutdown/reset during migration a high-value discriminator.
3. **Retain as a reusable testing lesson, not a competing patch:** the public VMDK extent-path bug showed two implementations of one path-resolution contract diverging. The fallback walk rejected traversal while the `openat2` path lacked equivalent confinement. The current upstream PR adds resolver flags and, importantly, tests the implementations side by side. That differential pattern belongs in Fieldwork's bug lens for any “kernel fast path + userspace fallback” pair.

A coordination result also surfaced during the round: another Fieldwork worker created `research/rounds/2026-08-11-cloud-hypervisor-lifecycle-scout/` and promoted `investigations/cloud-hypervisor-virtio-pci-queue-restore/`. This report links that work and avoids duplicating its carrier.

## Exact source boundary

- Upstream repository: `cloud-hypervisor/cloud-hypervisor`
- Upstream branch inspected: `main`
- Exact current head inspected: `a658c9f9fd0c4e0363004361d73ac8733fa24fd0`
- Research date: 2026-08-11
- Execution: source, issue, and pull-request review through the GitHub connector
- Local shell checkout: unavailable because the execution shell could not resolve GitHub; no product conclusion depends on that tooling failure
- Target-native KVM/MSHV execution: none in this round
- External-contact state: **disabled / no upstream contact performed**

## Coordination with the parallel lifecycle scout

Parallel Fieldwork work now exists at:

- `research/rounds/2026-08-11-cloud-hypervisor-lifecycle-scout/README.md`
- `investigations/cloud-hypervisor-virtio-pci-queue-restore/README.md`

That work already owns the inactive/non-ready virtio-pci queue restore question from upstream issue 8693. Its strongest discriminator is the activated multiqueue case with one ready and one non-ready queue.

This report therefore treats that result as a linked neighbour and continues elsewhere.

## 1. HTTP lifecycle status mapping

Upstream issues:

- https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8678
- https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8680

Primary source owner:

- `vmm/src/api/http/mod.rs`, `api_error_status_code()`
- lifecycle errors from `vmm/src/vm.rs`

### Current-main observation

At exact head `a658c9f9fd0c4e0363004361d73ac8733fa24fd0`, HTTP status selection handles a narrow set of VM errors specially:

```text
VmNotCreated / VmMissingConfig / no device / unknown device -> 404
selected validation conflicts -> 409
other validation failures -> 400
everything else -> 500
```

`VmNotRunning` exists as a distinct `VmError` but has no mapping branch, so it reaches the default 500 path.

The key design problem is wider than one missing match arm. The upstream reports describe two different situations that can currently surface through lifecycle errors:

1. **Absent object:** no VM exists for the requested operation.
2. **Existing object, incompatible lifecycle state:** a VM exists, but pause/resume/shutdown/power-button is invalid in the current state.

Those need separate state semantics before the HTTP code can map them faithfully.

### Why care

A management client uses HTTP status to decide whether to create a VM, retry later, change the requested transition, or treat the failure as a server fault. A 500 result for an ordinary lifecycle precondition sends the client down the server-failure path and hides a useful state distinction already known inside the VMM.

The API description also advertises lifecycle-state responses that the implementation does not currently emit, so generated clients and handwritten callers can follow a contract the server never satisfies.

### Candidate state matrix

Build a single table across the lifecycle endpoints under at least these server states:

| server/VM state | create | boot | pause | resume | shutdown | power-button |
|---|---|---|---|---|---|---|
| no VM object | observe | observe | observe | observe | observe | observe |
| created, never booted | observe | control | observe | observe | observe | observe |
| running | observe | observe | control | observe | control | control |
| paused | observe | observe | observe | control | observe | observe |
| migrating | observe | observe | observe | observe | observe | observe |

For every cell preserve:

- internal `VmError` variant and source chain;
- HTTP status;
- response body;
- OpenAPI-advertised status;
- whether the operation changed state;
- whether a retry with the same method can ever become valid without another transition.

The point is to classify the state boundary before choosing 404/409/405 or changing the API description.

### Important semantic question

Upstream issue 8680 calls out documented `405 Method Not Allowed` cases. HTTP 405 conventionally describes a method disallowed for the target resource and carries an `Allow` header. A VM lifecycle conflict may instead belong in a state-conflict response such as 409, or the current API description may intentionally define a different convention.

Fieldwork should resolve this from the project's intended public contract and existing endpoint practice rather than mechanically making implementation match a possibly stale status table.

### Negative controls

1. Unknown device ID should stay in the existing 404 family.
2. Duplicate identifiers should keep their existing validation-conflict mapping.
3. Malformed request JSON should remain 400.
4. A genuine internal device/VMM failure should remain 500.

These controls keep a lifecycle repair from turning all API errors into client errors.

### Promotion decision

**Promote.** This has current-source evidence, two live upstream reports, a compact state matrix, and a clear ownership boundary between VM-state errors and HTTP translation.

The first investigation should map behavior only. Product code comes after the matrix distinguishes missing-object state from incompatible-lifecycle state.

## 2. Exit/reset/guest-exit while migration owns the VM

Primary source owner:

- `vmm/src/lib.rs`, main epoll dispatch loop
- `VmOwnership::Migration`

### Current-main observation

The current event loop contains explicit follow-up TODOs immediately before all three lifecycle actions:

```text
Exit      -> vmm_shutdown()
Reset     -> vm_reboot()
GuestExit -> vm_shutdown() or vmm_shutdown()
```

Each TODO says lifecycle handling while migrating still needs resolution.

The same event loop separately understands `VmOwnership::Migration` for pending virtio activation: it upgrades the migration-held `DeviceManager` and operates through that migration-owned object instead of an ordinarily owned `Vm`.

That contrast is the useful source signal. Migration changes who owns the live objects, while asynchronous lifecycle events can still arrive through the common event loop.

### Claim boundary

This round does **not** claim a reproduced migration bug.

The established fact is narrower: current source explicitly marks exit/reset/guest-exit handling during migration as unresolved, and a bounded search did not surface an open issue dedicated to that interaction.

### First discriminator

Exercise each event at controlled points in the migration lifecycle:

1. before migration ownership transfer;
2. while the source VMM holds `VmOwnership::Migration`;
3. after successful handoff / completion;
4. during an intentionally failed or cancelled migration.

For each point, try:

- guest clean shutdown;
- guest reboot/reset;
- host/API VMM shutdown where applicable.

Observe:

- which side owns and destroys the VM/device manager;
- whether the migration channel completes, cancels, or hangs;
- whether the source VMM exits;
- whether the destination becomes runnable;
- event-monitor output;
- API responsiveness;
- thread/process cleanup;
- any double-shutdown, stale ownership, or leaked resource symptom.

### Negative control

Run the same lifecycle events with migration disabled and preserve the expected event/cleanup sequence from current main.

### Stop rule

Keep this as a research lane if every transition either completes or rejects cleanly and ownership remains singular.

Promote only after a current-main run produces a concrete contradiction such as a hang, double action, lost lifecycle event, source/destination disagreement, leaked process/resource, or a state claim that conflicts with the actual owner.

## 3. VMDK extent resolver equivalence

Upstream issue:

- https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8713

Active upstream PR:

- https://github.com/cloud-hypervisor/cloud-hypervisor/pull/8714

Primary source owner:

- `block/src/formats/vmdk/flat.rs`

### Current public finding

The VMDK extent opener has two ways to resolve paths:

- Linux `openat2`;
- a userspace fallback walk.

The public bug report established that relative extent containment differed between them: the fallback rejected parent traversal while the `openat2` path lacked equivalent confinement.

The active PR adds `RESOLVE_NO_MAGICLINKS` and `RESOLVE_BENEATH` for relative extent names and adds tests that deliberately run both resolution implementations against the same cases.

### Fieldwork lesson

The reusable result is the **backend-equivalence discriminator**:

> When two implementations serve one logical contract, run the same adversarial and ordinary corpus through both implementations and compare acceptance, rejection, result identity, and error class.

This catches a class of bugs that happy-path tests miss: each backend can look internally reasonable while the feature's effective policy changes according to kernel capability or fallback selection.

Useful places to reuse this lens include:

- syscall-backed path resolution vs manual fallback;
- io_uring vs synchronous I/O;
- KVM vs MSHV backend policy;
- accelerated vs software parsing/validation paths;
- host feature present vs compatibility fallback.

### Scope decision

Keep this as a reusable note/result while upstream PR 8714 is active. Creating a competing product patch from Fieldwork would add little value today.

A future Fieldwork lane becomes useful if another pair of Cloud Hypervisor backends lacks an equivalence harness or if the upstream fix leaves a demonstrated semantic delta.

### Safety boundary

This is a public-source, already-public defect. The report preserves only the public failure class and source-level repair/test lesson. No live target, private path, credential, or external system was touched.

## 4. Current-main / Fieldwork reconciliation

The exact upstream head used here is newer than the parallel lifecycle scout's recorded `a18a2b3f66f7a3cec7f62d07605945beda8eb5d3` boundary.

Current upstream main at this pass is:

`a658c9f9fd0c4e0363004361d73ac8733fa24fd0`

That head includes the shutdown lifecycle test work previously listed in `CURRENT_FIELDWORK.md` as upstream review pending. The ACPI error-propagation work is also already merged upstream, as the parallel lifecycle scout records.

`CURRENT_FIELDWORK.md` therefore contains stale submission dispositions for those two Cloud Hypervisor items. Refreshing the large live board should be done as its own coordinated edit because other workers are actively changing the repository during this round.

No board overwrite was attempted here.

## Ranked next actions

1. **API state matrix:** create a focused investigation for issues 8678/8680 and capture the internal-error/HTTP/OpenAPI matrix before editing status mappings.
2. **Virtio restore execution:** continue the already-promoted queue-restore investigation; do not fork a duplicate carrier.
3. **Migration lifecycle probe:** add a bounded synthetic/integration probe only after identifying the smallest controllable migration phase hooks already present in tests.
4. **VMDK equivalence lens:** retain the dual-backend test pattern as a reusable note and watch the active upstream PR only through public read-only review.
5. **Board refresh:** reconcile merged shutdown-event and ACPI dispositions in `CURRENT_FIELDWORK.md` with current upstream main when a worker holds the edit.

## Reopening triggers

Reopen this broad round only when one of these happens:

- the API state matrix identifies a smaller error-owner boundary than `VmNotRunning`;
- migration execution produces a concrete failure sequence;
- the VMDK upstream patch lands or changes its resolver contract materially;
- current upstream main changes the HTTP mapper or migration ownership model;
- a new parallel Fieldwork record supersedes one of these lanes.
