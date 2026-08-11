# Receive-migration comparison for Landlock restore ordering

Updated: 2026-08-12

Canonical source: `cloud-hypervisor/cloud-hypervisor` `main`
Exact source head: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Parent investigation: `investigations/cloud-hypervisor-landlock-restore-order/README.md`
External-contact state: **disabled / no upstream contact performed**

## TL;DR

Receive-migration is an existing positive neighbour for applying Landlock before most restored VM resources are reconstructed.

The two restore paths currently order the same ingredients differently:

```text
snapshot restore
  recv config/state
  pre-create console resources
  Vm::new(... source_url ...)
    -> memory manager / device reconstruction / disk opens
  apply Landlock
  restore VM state

receive migration
  receive + validate config
  update memory zones
  pre-create console resources
  apply Landlock
  create hypervisor VM + MemoryManager
  receive VM state
  Vm::new_from_memory_manager(...)
    -> device reconstruction / restore
```

This narrows the design question. Cloud Hypervisor already has one migration path in which the configuration is known, console resources are prepared, and the VMM restricts itself **before** memory-manager and device reconstruction. The snapshot-restore ordering is therefore not forced by a general requirement that all restore resources exist before Landlock.

The remaining special case is the snapshot source itself. Snapshot restore reads `config.json` and `state.json` before `Vm::new()`, while the memory manager uses the snapshot directory for the `memory-ranges` payload. `VmConfig::apply_landlock()` inventories configured VM paths and explicit `landlock_rules`, but it does not receive `source_url`. Moving snapshot enforcement earlier therefore needs an explicit source-directory policy or a pre-opened-source design rather than a simple call reordering.

## Exact source observations

### Snapshot metadata is read before VM construction

`vmm/src/migration/mod.rs` defines:

```text
config.json
state.json
```

and `recv_vm_config()` / `recv_vm_state()` resolve `file://...` to a directory and open those files directly.

### Snapshot memory has a separate file

`vmm/src/memory_manager.rs` defines:

```text
SNAPSHOT_FILENAME = "memory-ranges"
```

`Vm::new()` receives the snapshot `source_url`, so any candidate that applies Landlock before `Vm::new()` must preserve access needed by memory restoration from that source.

### Snapshot restore applies Landlock after construction

Current `vm_restore()` performs, in order:

1. receive snapshot state/config;
2. install `self.vm_config`;
3. `pre_create_console_devices(self)`;
4. construct `Vm::new(... Some(&snapshot), Some(source_url), ...)`;
5. if enabled, `apply_landlock(&mut self.vm_config)`;
6. `vm.restore()`.

This is the ordering that permits a configured disk backend to open a secondary path before the restriction becomes active.

### Receive migration applies Landlock before reconstruction

Current receive-migration performs, in order:

1. receive and validate the migrated VM config;
2. update memory-zone metadata;
3. install `self.vm_config`;
4. `pre_create_console_devices(self)`;
5. if enabled, `apply_landlock(&mut self.vm_config)`;
6. create the hypervisor VM and `MemoryManager`;
7. receive state and reconstruct the VM/device graph.

The receive path therefore supplies an in-tree precedent for the narrower ordering:

```text
configuration known
+ console resources prepared
+ Landlock active
+ memory/device reconstruction follows
```

## What this changes in the candidate space

### Candidate A — move snapshot Landlock before `Vm::new()` and grant the snapshot source

Leading candidate for execution:

1. read `config.json` and `state.json` as today;
2. pre-create console resources as today;
3. derive the exact snapshot-source path authority still needed after restriction;
4. apply the VM config Landlock rules plus that source authority;
5. construct `Vm::new()`;
6. restore.

A directory-level grant for the snapshot source is the simplest first probe because the format already treats `source_url` as a directory and stores multiple named files below it. A tighter pre-open design remains possible if execution shows the directory grant is unnecessarily broad.

### Candidate B — pre-open every restore payload before restriction

This would preserve the current ability to access the source without adding a path rule, but it changes ownership/API boundaries more substantially. Keep it as a competitor only if Candidate A cannot express the source requirement cleanly.

### Candidate C — document the current ordering

This remains the negative-control design. It would say restore intentionally reconstructs devices before Landlock. The receive-migration path weakens that explanation because a sibling restore mechanism already enforces earlier.

## Required differential

Use the QCOW backing-path fixture already defined by the parent investigation.

Configuration:

```text
allowed/
  overlay.qcow2
  snapshot/
unlisted/
  backing.raw
```

Landlock rules permit `allowed/` and the explicit snapshot source needed by the candidate, but do not permit `unlisted/backing.raw`.

Compare:

1. **fresh create/boot** using `allowed/overlay.qcow2` whose backing reference resolves to `unlisted/backing.raw`;
2. **snapshot restore** under the same VM path policy;
3. **receive-migration** as a sibling ordering control where practical.

The product invariant is:

> A disk path denied by the active VM Landlock policy must not become usable merely because the VM entered through snapshot restore instead of fresh boot.

The strongest failure is a differential in which fresh boot is denied but snapshot restore succeeds because the backing file was opened before restriction.

## Console boundary

Both snapshot restore and receive-migration call `pre_create_console_devices()` before Landlock. Do not move the restriction ahead of that helper without a separate discriminator. The current comparison supports an enforcement point **after console pre-creation and before memory/device reconstruction**.

## Evidence boundary

Established here from exact current source:

- snapshot restore applies Landlock after `Vm::new()`;
- receive-migration applies Landlock before `MemoryManager` and VM/device reconstruction;
- both paths pre-create console resources before Landlock;
- snapshot metadata consists of `config.json` and `state.json` below a `file://` directory;
- memory snapshot code names a separate `memory-ranges` payload;
- `VmConfig::apply_landlock()` has no `source_url` parameter.

Still pending:

- runtime fresh-vs-restore QCOW differential;
- proof of the minimum source-directory access required after moving enforcement;
- candidate CI;
- decision whether a directory grant or pre-opened payload is the better long-term boundary.

## Next action

Execute the QCOW backing-path differential. If baseline restore can reach an unlisted backing path that fresh boot rejects, implement Candidate A on an internal carrier using the receive-migration ordering as the source-level model, then rerun with the snapshot source explicitly granted and the backing path still denied.
