# Snapshot restore path inventory for an earlier Landlock boundary

Updated: 2026-08-11

Exact upstream head: `915d359f97475b1a39d8561f8db514da9e692d19`

## TL;DR

Snapshot restore's filesystem-specific inputs are compact and share one caller-selected directory.

Current snapshot layout uses:

```text
<source_url>/config.json
<source_url>/state.json
<source_url>/memory-ranges
```

`config.json` and `state.json` are opened and fully read before `Vm::new()`.

`memory-ranges` is opened from `MemoryManager::new_from_snapshot()` during `Vm::new()`:

- full restore opens it and copies saved ranges into guest RAM;
- on-demand restore opens it and hands the fd to `FileUffdMemorySource`; the UFFD handler keeps it open while pages are faulted/prefaulted.

That means a restore candidate can plausibly apply Landlock before `Vm::new()` if the current restore source directory is included as read authority.

## Exact files

### `config.json`

Owner: `vmm/src/migration/mod.rs::recv_vm_config()`.

The function converts `file://...` to a directory, appends `config.json`, opens it, reads it completely, and deserializes `VmConfig`.

This happens in the request-layer `vm_restore()` before the lower restore helper reaches `Vm::new()`.

### `state.json`

Owner: `vmm/src/migration/mod.rs::recv_vm_state()`.

The lower restore helper reads and deserializes this before constructing the VM.

### `memory-ranges`

Owner: `vmm/src/memory_manager.rs::MemoryManager::new_from_snapshot()`.

It derives the path by appending the constant `SNAPSHOT_FILENAME = "memory-ranges"` to the same source URL directory.

Full mode calls `fill_saved_regions()`, which opens the file read-only and copies saved extents/ranges.

On-demand mode calls `restore_by_uffd()`, which opens the file read-only and places the fd into `FileUffdMemorySource`. The spawned UFFD handler retains the source until restore is complete or stopped.

## Why the current restore source must be considered separately from saved rules

A source VM running with Landlock must have enough authority to create its snapshot destination. In practice, a caller that snapshots to `/snap/a` under Landlock needs that destination in the source VM's explicit rules, and those rules are serialized into the saved config.

That does **not** guarantee that a future restore uses the same location.

A snapshot can be copied or moved:

```text
created at: /snap/a
restored from: /archive/b
```

The saved Landlock rule can still name `/snap/a` while the restore API explicitly names `/archive/b` as `source_url`.

Current late-Landlock ordering succeeds in reading `/archive/b` before applying the saved rules. A candidate that simply moves `apply_landlock()` earlier would regress this use case unless the **current** restore source is added to the rule set used for restriction.

## Candidate authority rule

The caller explicitly supplies `RestoreConfig.source_url`. For a `file://` restore source, grant that selected snapshot directory read access for the restore lifetime:

```text
current source_url directory -> r
```

Then apply the normal saved VM configuration rules plus this restore-specific read rule before `Vm::new()`.

Why directory read instead of three individual files:

- all standard snapshot files are defined beneath that directory;
- on-demand memory restore needs continued read access to `memory-ranges`;
- a directory rule naturally covers the fixed snapshot file set while staying scoped to the caller-selected snapshot root;
- future snapshot-format additions under the same root do not silently recreate the late-sandbox problem.

A file-specific list is still a competing option if maintainers prefer maximum narrowness.

## Avoid permanently mutating saved VM policy

The current restore source is an operation-specific input. Permanently appending it to `VmConfig.landlock_rules` has a side effect: future snapshots of the restored VM can serialize old restore locations and accumulate stale paths.

Prefer an application interface that accepts temporary extra rules for the current `restrict_self()` call, for example conceptually:

```text
VmConfig::apply_landlock_with_extra_rules([source_url -> r])
```

while retaining ordinary `VmConfig::apply_landlock()` for create/receive paths.

This keeps runtime sandbox authority accurate without changing the VM's durable configuration.

## Candidate ordering

A credible first design is now:

```text
recv config.json
validate/patch restored config
recv state.json
derive current source directory read rule
apply saved config Landlock rules + temporary source rule
Vm::new(... source_url ...)
  -> MemoryManager opens memory-ranges under Landlock
  -> DeviceManager opens disks/backing files under Landlock
  -> helper threads spawned here inherit Landlock
vm.restore()
```

This mirrors the receive-migration positive neighbor: once trusted configuration and operation-specific path authority are known, restored constructors execute inside the Landlock domain.

## On-demand restore benefit

Today `restore_by_uffd()` opens `memory-ranges` and spawns `uffd-handler` before restore applies Landlock.

With the earlier boundary:

1. the snapshot source directory is allowed read-only;
2. Landlock is applied;
3. the memory snapshot file is opened;
4. `uffd-handler` is spawned afterward and inherits the Landlock domain.

This closes both the file-open ordering difference and the pre-existing-thread inheritance difference for this handler.

## Snapshot creation documentation gap

The bounded source/doc search found no Landlock guidance explaining that snapshot destinations must be included in the predeclared rules when a running Landlocked VM will call `vm.snapshot`.

That is adjacent to this repair but should stay separate until runtime confirms the exact error path. A future docs update may need to cover:

- snapshot destination write authority;
- restore source read authority;
- QCOW backing paths and other transitive VM resource paths.

Avoid publishing piecemeal docs until the restore-order policy is selected.

## Negative controls for a candidate

1. Restore from the original snapshot location whose path is already in saved rules.
2. Restore from a copied snapshot location absent from saved rules; temporary `source_url` authority should make this work.
3. An unrelated path outside both saved rules and current source URL should remain denied.
4. QCOW backing file outside saved/explicit rules should be denied during `Vm::new()` after the ordering fix.
5. On-demand restore should continue reading `memory-ranges` after `vm_restore()` returns.
6. Receive-migration ordering should remain unchanged.

## Evidence boundary

Established from current source:

- fixed snapshot metadata files are `config.json` and `state.json`;
- guest RAM snapshot file is `memory-ranges`;
- all are derived from the same `file://` source directory;
- full and on-demand memory restore open `memory-ranges` during `Vm::new()`;
- on-demand keeps its fd in a spawned UFFD handler;
- receive-migration already applies Landlock before restored memory/device construction;
- the restore source can differ from paths serialized in the saved VM config.

Pending:

- runtime moved-snapshot control under Landlock;
- runtime fresh-vs-restore QCOW backing differential;
- exact temporary-rule API design;
- compile/test candidate.
