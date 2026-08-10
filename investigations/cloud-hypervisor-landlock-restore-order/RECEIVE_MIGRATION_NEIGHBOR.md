# Positive neighbor — receive-migration applies Landlock before VM construction

Updated: 2026-08-11

Exact upstream head: `915d359f97475b1a39d8561f8db514da9e692d19`

## Result

Live receive-migration provides a current in-tree example of the ordering that snapshot restore lacks.

During `vm_receive_config()`, the destination:

1. receives and deserializes `VmMigrationConfig`;
2. validates/replaces host-specific VFIO file descriptors;
3. applies memory-zone updates;
4. stores the received `VmConfig`;
5. prepares console paths/fds;
6. **applies Landlock when `landlock_enable` is set;**
7. only then creates the hypervisor VM and `MemoryManager`.

Later, when the final migration state arrives, `vm_receive_state()` calls `Vm::new_from_memory_manager(...)`, which creates the restored devices under the already-active Landlock domain.

So current code has this lifecycle split:

```text
fresh create:
  config -> Landlock -> Vm::new -> devices/files

receive migration:
  received config -> Landlock -> hypervisor VM / memory -> Vm::new_from_memory_manager -> devices/files

snapshot restore:
  read snapshot -> Vm::new -> devices/files -> Landlock -> vm.restore
```

Snapshot restore is the outlier.

## Why this changes the candidate ranking

The receive-migration path demonstrates that Cloud Hypervisor already treats **received restored configuration as sufficient input to build the Landlock ruleset before restored device construction**.

That strengthens the case for the snapshot-restore candidate family:

```text
read only the metadata needed to recover/validate config
collect snapshot-specific file authority
apply Landlock
construct memory/devices
restore state
```

The remaining difference is snapshot storage itself. Receive-migration gets memory/state over already-established sockets and received file descriptors; snapshot restore needs filesystem access to its source URL and memory files.

The next owner is therefore the **snapshot file inventory**, not a general uncertainty about whether restored devices can be created after Landlock.

## Useful negative control

A future snapshot-restore candidate should compare its ordering with receive-migration and preserve this property:

> once the destination has enough trusted configuration to enumerate host paths, restored device constructors run inside the Landlock domain.

Do not weaken receive-migration while repairing snapshot restore.

## Remaining question

Enumerate every filesystem object snapshot restore must access after `recv_vm_config()` / `recv_vm_state()` but before and during `Vm::new()` / `MemoryManager` restore, including on-demand modes.

If those paths can be derived from the restore source plus saved configuration before device construction, candidate A from the main investigation becomes substantially smaller and more credible.

## Evidence boundary

Established from current source:

- receive-migration applies Landlock before hypervisor VM and memory-manager creation;
- final received state constructs devices later under the active Landlock domain;
- snapshot restore applies Landlock after `Vm::new()` and pre-sandbox device/file opens;
- the lifecycle paths therefore have a real ordering difference in current main.

Runtime parity remains pending.
