# Cloud Hypervisor offload snapshot publication

Updated: 2026-08-11
Owning Fieldwork issue: #555
Upstream design thread: https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8277
Canonical upstream repository: `cloud-hypervisor/cloud-hypervisor`
Exact upstream source head inspected: `a18a2b3f66f7a3cec7f62d07605945beda8eb5d3`
Fieldwork head refreshed before promotion: `a4bd790a6a68e0b60b17664032609f75924b0a1c`
Primary owner: `offload_daemon/src/main.rs`
Current state: **SOURCE-CONFIRMED PUBLICATION CANDIDATE / EXECUTION PENDING**
External-contact state: `false; none occurred`

## TL;DR

The reference Cloud Hypervisor `offload_daemon` writes one logical snapshot as several ordinary files in a caller-provided directory. It accepts an existing directory, writes the new configuration and device state before completion, and writes the new `memory-*` files only after it receives `Complete` / `CompletePaused`.

A second snapshot into a directory already containing snapshot A can therefore expose snapshot B's `migration_config.json` and `state.json` while snapshot A's `memory-*` files remain. `Abandon`, connection loss, process death, or an error before memory dumping can leave that mixed generation behind. Restore then reads the filenames as one snapshot; current source has no completion marker or generation identity connecting them.

The first executable discriminator is deliberately small: seed snapshot A, drive snapshot B through `Start -> MemoryFd(s) -> Config(B) -> State(B) -> Abandon`, then inspect the residue and feed it to the restore-side artifact reader.

The first sparse-copy suspicion was eliminated. Individual memory destinations are fresh or truncated. The surviving owner is publication of the snapshot directory as a multi-file unit.

## Explain like I'm five

Imagine a saved VM is a box with three cards:

```text
settings
machine state
memory
```

There is already an old box, A.

Cloud Hypervisor's example offload program starts making box B in the same place. It replaces the settings card and machine-state card first. Before it replaces the memory card, the operation gets cancelled.

The directory now says:

```text
settings      = B
machine state = B
memory        = A
```

Restore has no label saying which generation each card belongs to. It can pick up all three and treat them as one VM snapshot.

## Why care

Snapshot/restore is an all-or-one-generation operation. CPU/device state and guest RAM describe the same instant. Mixing generations can create a restored VM whose machine state refers to memory contents from a different instant or a different configuration.

The reference daemon is upstream code intended to be maintained and used as the working example for offload implementations. The original design discussion explicitly says a reference implementation would live upstream and be actively maintained. This makes publication semantics useful beyond one demo command: daemon authors can copy the lifecycle demonstrated here.

## Exact source boundary

Source reviewed at upstream head:

`a18a2b3f66f7a3cec7f62d07605945beda8eb5d3`

Primary files:

- `offload_daemon/src/main.rs`
  - https://github.com/cloud-hypervisor/cloud-hypervisor/blob/a18a2b3f66f7a3cec7f62d07605945beda8eb5d3/offload_daemon/src/main.rs
- `docs/snapshot_restore.md`
  - https://github.com/cloud-hypervisor/cloud-hypervisor/blob/a18a2b3f66f7a3cec7f62d07605945beda8eb5d3/docs/snapshot_restore.md
- `vmm/src/sparse.rs`
  - https://github.com/cloud-hypervisor/cloud-hypervisor/blob/a18a2b3f66f7a3cec7f62d07605945beda8eb5d3/vmm/src/sparse.rs
- `vmm/src/memory_manager.rs`
  - https://github.com/cloud-hypervisor/cloud-hypervisor/blob/a18a2b3f66f7a3cec7f62d07605945beda8eb5d3/vmm/src/memory_manager.rs
- `vm-migration/src/protocol.rs`
  - https://github.com/cloud-hypervisor/cloud-hypervisor/blob/a18a2b3f66f7a3cec7f62d07605945beda8eb5d3/vm-migration/src/protocol.rs

Historical offload commits inspected:

- `4992fabd158f5208f134ed12efaed770016e94da` — reference implementation;
- `df5d2d6003606f76bf59be1edca61a06765288aa` — shared sparse helpers;
- `28b6b5d46743803e4c3bf2583bdf6932720a0bee` — sparse snapshot/restore;
- `60398f11ffb5c4ce1211aaf05f7d324918ce4a32` — on-demand restore;
- `17b5deeaede5e1def80029bd64bec6866d56070a` — preserve source after snapshot.

## Invariant

A snapshot directory accepted by restore must identify one completed snapshot generation.

For an attempted replacement A -> B, interruption should produce one of these outcomes:

1. A remains the published snapshot;
2. B becomes the published snapshot only after all B artifacts are complete;
3. an incomplete artifact exists but restore rejects it deterministically.

A directory silently combining A and B violates the invariant.

## Operation owner

The relevant owner is the reference daemon's snapshot-directory publication boundary, not the VMM's per-file sparse copier.

The daemon chooses:

- when names become visible in the final output directory;
- when old names are overwritten;
- when each protocol stage is ACKed;
- what residue survives `Abandon` or local failure;
- what restore considers a complete local snapshot.

## Current snapshot sequence

`run_snapshot()` begins with:

```text
create_dir_all(output_dir)
```

so the caller may point it at an existing directory. There is no empty-directory requirement at this boundary.

The protocol then behaves as follows.

### MemoryFd

Each `MemoryFd` is received and retained in the daemon's `memory_slots` vector. No `memory-*` file is written yet.

### Config

The daemon reads the payload and immediately writes:

```text
output_dir/migration_config.json
```

using `fs::write()`, then ACKs Config.

### State

The daemon reads the payload and immediately writes:

```text
output_dir/state.json
```

using `fs::write()`, then ACKs State.

### Complete / CompletePaused

Only here does the daemon call `dump_memory_slots()`.

For every slot, `dump_fd_to_path()` opens the final path with:

```text
create(true)
truncate(true)
write(true)
```

sets its length, copies guest memory, and calls `sync_all()`.

After all memory slots finish, the daemon ACKs the completion command and logs that the snapshot was persisted.

### Abandon

The daemon ACKs `Abandon` and returns `Error::Abandoned`. It has no rollback step for Config or State already written into the final directory.

Connection loss, daemon termination, or another local error after Config/State has the same publication concern: visible final names have already changed.

## Current restore sequence

`run_restore()` reads final paths directly from `input_dir`:

```text
migration_config.json
state.json
memory-<slot>
```

The config's `guest_ram_mappings` decides which memory slot files are opened and sent back to Cloud Hypervisor.

Current source does not attach a generation identifier to those files and does not require a final completion marker before restore starts.

That is enough for the mixed-generation hypothesis to survive source review.

## First distinguishing probe

The next useful experiment does not require KVM. Exercise the reference daemon protocol or a compact extraction of its file-publication logic with deterministic temporary files.

### Generation A seed

Create a complete snapshot directory representing A:

```text
migration_config.json -> config A
state.json            -> state A
memory-0              -> bytes A0
memory-1              -> bytes A1
```

Use distinguishable values and matching slot metadata.

### Interrupted generation B

Drive snapshot mode with B through:

```text
Start
MemoryFd(slot 0, B0)
MemoryFd(slot 1, B1)
Config(B)
State(B)
Abandon
```

### Predicted baseline residue

Current source predicts:

```text
migration_config.json -> B
state.json            -> B
memory-0              -> A0
memory-1              -> A1
```

A fixture should verify exact bytes, not only file existence.

### Restore-side discriminator

Point the restore artifact-loading path at that directory.

Plausible outcomes:

1. restore accepts the artifact set and begins sending A memory under B metadata/state — strongest form of the defect;
2. restore later fails for an incidental incompatibility — directory publication is still partial, but the claim narrows to stale/inconsistent artifact exposure rather than guaranteed successful mixed restore;
3. an existing completeness check rejects the directory before consuming it — this would defeat the current hypothesis and should be retained as a negative result.

Source review currently predicts outcome 1 for compatible A/B layouts because no explicit generation/completion check was found.

## Negative control

Run B into a fresh empty output directory through successful completion.

Expected:

```text
migration_config.json -> B
state.json            -> B
memory-0              -> B0
memory-1              -> B1
```

Restore should accept the resulting complete generation.

This proves the harness can recognize a valid publication and keeps protocol mistakes from masquerading as the interruption finding.

## Stronger failure injection

The Abandon case proves Config/State versus memory publication ordering. It does not make a tempting weaker repair lose.

A second fixture should fail during `dump_memory_slots()` after slot 0 is successfully replaced but before slot 1 is replaced.

Predicted residue when A existed first:

```text
migration_config.json -> B
state.json            -> B
memory-0              -> B0
memory-1              -> A1
```

This makes a repair that merely delays Config/State writes lose. The whole generation needs one publication rule, or restore needs an identity/completeness rule that rejects this state.

## Cross-context negative: sparse copying is not the owner

The first source suspicion was `write_region_sparse()` in `vmm/src/sparse.rs`.

Sparse copying intentionally writes only populated extents. If its destination already held nonzero bytes in source holes, stale bytes could survive.

Current callers eliminate that route:

### Internal MemoryManager snapshot

The `memory-ranges` snapshot destination is opened with `create_new(true)`. A previous file cannot be silently reused by that call.

### Offload daemon memory slot

`dump_fd_to_path()` truncates the destination before setting its length and invoking `copy_region()`.

Therefore sparse holes read back as zeros from a fresh/truncated file. The direct stale-byte hypothesis is closed for these current callers.

This negative result is useful because the visible symptom lives around sparse snapshot files, but the surviving lifecycle defect sits one level above the helper.

## Competing product boundaries

### Candidate A — generation staging and final publication

Build B under a fresh temporary sibling directory or generation namespace, complete and sync every artifact there, then publish the completed generation in one explicit final transition.

Properties:

- A remains intact while B is incomplete;
- all B files share one generation boundary;
- errors during memory slot N do not expose a partial B as the final snapshot;
- cleanup of abandoned temporary generations can be separate from correctness.

Open design question: replacing a non-empty directory atomically has filesystem/path semantics that need a small explicit policy. Do not choose implementation mechanics before the fixture establishes intended reuse behavior.

### Candidate B — empty-directory requirement plus completion marker

Reject a non-empty output directory before snapshot starts, write artifacts normally, and publish a final marker after all writes complete. Restore requires the marker.

Properties:

- very small policy surface;
- mixed A/B replacement disappears because reuse is rejected;
- partial first-generation directories become detectable by restore.

Cost:

- changes caller-visible reuse semantics;
- orchestration must choose a fresh path for each generation;
- marker and its durability still need an exact contract.

### Candidate C — cleanup/rollback on Abandon only

Delete or restore Config/State when `Abandon` arrives.

This loses immediately on process death, connection loss, and mid-memory-dump failure. Keep it as a negative alternative, not the selected repair.

### Candidate D — delay Config/State writes until Complete

This fixes the simple Config/State-before-memory Abandon fixture if memory files are written first.

It loses on the two-slot mid-dump fixture: some memory slots can belong to B while untouched slots remain A. Keep it only as another negative alternative.

## Durability follow-up

A separate source observation survived the pass:

- `migration_config.json` uses `fs::write()`;
- `state.json` uses `fs::write()`;
- each memory slot gets `sync_all()`;
- no explicit sync of the snapshot directory was found in the reference daemon path.

A successful protocol ACK can therefore have different durability treatment across one logical snapshot. The exact claim needs a crash/power-loss discriminator and filesystem durability contract, so keep it separate from the interruption/mixed-generation candidate.

If promoted later, the question is:

> What must be durable before the daemon ACKs Complete when that ACK may allow the source VM to disappear?

## Malformed-artifact follow-up

Restore parses local JSON into `guest_ram_mappings` and currently contains two narrow arithmetic/identity hardening leads:

- `file_offset + size` is used to size restore memfds without checked addition;
- `slot` is parsed as `u64` and narrowed with `as u32`.

These concern corrupted or caller-edited local artifact input. They do not explain the normal interrupted-publication sequence and stay outside #555 until a distinct consequence is demonstrated.

## On-demand restore follow-up

On-demand mode creates empty memfds and opens the corresponding snapshot memory file, while actual `read_exact_at()` calls happen when page faults arrive.

A truncated `memory-*` file may therefore survive initial setup and fail only when a guest page is demanded. Compare with eager restore, which copies the configured range before completion.

This can become a useful lifecycle question only after tracing the exact completion/resume ordering and building a truncated-artifact negative control. Keep it separate for now.

## Historical intent

The original offload design issue, #8277, says the goal is to move snapshot/restore data handling into a dedicated user-space process while keeping flexibility for encryption, compression, and transport.

Office-hour follow-up records that a reference implementation would live upstream and be actively maintained, with management software using it.

The current docs describe the in-tree daemon as intentionally minimal and a template for daemon authors. Minimality supports a small publication rule; it does not make mixed-generation final artifacts a useful example contract.

## Research bender checkpoint

```text
RESEARCH BENDER CHECKPOINT
Unit: Cloud Hypervisor reference offload snapshot publication
Exact upstream head: a18a2b3f66f7a3cec7f62d07605945beda8eb5d3
Fieldwork baseline before promotion: a4bd790a6a68e0b60b17664032609f75924b0a1c
Bounded question: can interrupted reuse expose a restoreable mixed-generation snapshot directory?
Technical result owner: offload_daemon/src/main.rs final-directory publication
Active variants: source-confirmed baseline; no product carrier
First distinguishing result: Config/State publish before memory; Abandon has no rollback; existing directory accepted
Alternatives still alive: staged generation publication; empty-dir + completion marker
Alternatives eliminated: sparse-helper stale bytes; Abandon-only cleanup; delay-Config/State-only as complete repair
Changed paths: Linux Fieldwork issue #555 + this investigation record only
Completed gates: exact-head source review; docs/design review; cross-context sparse caller review; duplicate issue search
Cleanup and residue: no upstream writes, no fork branch, no runtime resources
Evidence boundary: source-confirmed; executable interruption fixture pending
Stop condition: reproduce mixed-generation residue and select the smallest publication rule that makes it impossible or rejected
Reopening trigger: explicit upstream requirement for in-place replacement semantics or a completeness rule that defeats the baseline prediction
Next safe action: deterministic two-generation interruption fixture without KVM
External-contact state: false; none occurred
```

## Evidence boundary

Established:

- current source accepts an existing output directory;
- Config and State are written into final names before completion;
- memory files are refreshed only at completion;
- Abandon has no rollback for the earlier file writes;
- a mid-memory-dump failure can occur after some final memory names have been replaced;
- restore reads final filenames without an explicit generation/completion identity found in current source;
- direct sparse-copy callers start from fresh/truncated destination files;
- upstream intends to maintain the reference implementation.

Pending:

- execution of the two-generation Abandon fixture against current source;
- execution of the mid-memory-dump variant;
- direct restore-side acceptance/failure observation for mixed generation artifacts;
- intended policy for reusing a non-empty output directory;
- product candidate;
- formatting, Clippy, build, integration, or KVM gates for a candidate.

No target-native or synthetic execution is being presented as completed evidence in this record.

## Stop condition

Stop widening source and select or stop after these questions are answered:

1. Does exact current code leave A memory with B Config/State after the deterministic interrupted reuse sequence?
2. Does the restore artifact reader consume that mixed directory when A/B layouts are compatible?
3. Does the two-slot mid-dump probe make partial memory replacement observable?
4. Is output-directory reuse intended, rejected, or unspecified by project behavior/tests?
5. Which smallest publication policy handles interruption classes without broadening the reference daemon into a storage system?

If a fresh-directory-only contract is acceptable, prefer the smaller boundary. If replacement/reuse is a supported expectation, stage and publish one complete generation.

## Reopening trigger

After closeout, reopen only if:

- upstream source changes final-directory publication ordering;
- a new completion/generation check appears in restore;
- documented reuse semantics become explicit;
- target execution disproves the predicted mixed-generation residue;
- a supported storage backend requires publication semantics that the selected local-directory rule cannot express.

## Next safe action

Create a compact no-KVM fixture around the reference daemon's local UNIX migration protocol:

- valid A seed;
- B Config/State + Abandon;
- exact residue assertion;
- clean B completion control;
- optional deterministic failure on second memory-slot publication;
- restore-side preflight/acceptance observation.

Preserve the fixture and exact source head before considering product code.

## External-contact state

`false; none occurred`.
