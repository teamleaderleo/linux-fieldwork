# Cloud Hypervisor Landlock ordering during snapshot restore

Updated: 2026-08-11

Canonical source: `cloud-hypervisor/cloud-hypervisor` `main`
Exact source head: `915d359f97475b1a39d8561f8db514da9e692d19`

Relevant upstream history:

- Landlock implementation: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/6214
- restore enablement commit: `eea45a2c78b1f4884efa3d2d941062de22745e56`
- sandboxing tracker: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/5170

Related Fieldwork:

- `investigations/cloud-hypervisor-landlock-qcow-backing/README.md`
- internal documentation carrier: `teamleaderleo/cloud-hypervisor#18`

Primary owners:

- `vmm/src/lib.rs` — `vm_create()` and `vm_restore()` Landlock ordering
- `vmm/src/vm.rs` — `Vm::new()` initialization order
- `vmm/src/device_manager.rs` — device creation and disk opens
- `vmm/src/vm_config.rs` — Landlock rule collection

Current state: **source-confirmed fresh-boot/restore policy divergence; runtime differential pending**
Upstream-contact state: **disabled / no contact performed**

## TL;DR

Fresh VM creation and snapshot restore apply the same Landlock configuration at different points in the file-open lifecycle.

Fresh creation applies Landlock before the VM and its block devices are built:

```text
vm_create
  -> collect VMConfig + explicit Landlock paths
  -> restrict_self()
  -> later vm_boot / Vm::new
  -> create devices
  -> open disks and QCOW backing files
```

Snapshot restore does the reverse for device construction:

```text
vm_restore
  -> read snapshot
  -> Vm::new
     -> create DeviceManager
     -> create devices
     -> open disks and QCOW backing files
  -> restrict_self()
  -> vm.restore()
```

So file-backed resources opened by `Vm::new()` are outside Landlock enforcement on restore. The VMM thread is restricted only after those descriptors already exist.

This becomes a concrete policy divergence with QCOW backing files. On fresh boot, a backing path omitted from the Landlock allowlist is expected to fail when the block backend opens it after `restrict_self()`. On restore, the same omitted backing path can be opened before `restrict_self()`, after which the already-open backing descriptor remains part of the restored disk path.

The bounded question is:

> Which restore resources intentionally need to be opened before Landlock, and how can the VMM preserve the same explicit path policy across fresh boot and restore without breaking snapshot-memory access?

Do not collapse this into the QCOW documentation lane. The owner here is restore ordering and sandbox timing.

## Explain like I'm five

Fresh boot says:

```text
first lock the doors
then open the VM's files
```

Restore says:

```text
open the VM's files
then lock the doors
```

If a file is missing from the allowlist, fresh boot can stop it. Restore may already have the file open by the time the lock is applied.

## Why care

Landlock is a path-access boundary. Users reasonably expect a restored VM with the same configuration to retain the same sandbox policy as a fresh VM.

A lifecycle path that opens additional files before applying the sandbox creates two practical problems:

1. the same VM configuration can accept a file graph on restore that fresh creation rejects;
2. future initialization code added inside `Vm::new()` can acquire host resources before the restore sandbox is active.

The finding is security-adjacent but fully bounded to public source and synthetic/owned test plans. No external target or private data is involved.

## Exact current-source sequence

### Fresh create

The original Landlock design deliberately applies the ruleset in the VMM thread during `vm_create()`. The upstream PR rationale says this is done before the remaining VM threads are spawned so those threads inherit the restriction.

Current `VmConfig::apply_landlock()` collects configured paths and caller-supplied `landlock_rules`, then calls `restrict_self()`.

The actual VM object and devices are created later when the VM is booted.

### Restore

Current `vm_restore()` performs:

1. `recv_vm_state(source_url)`;
2. restore/config checks;
3. `Vm::new(... Some(&snapshot), Some(source_url), ...)`;
4. **then**, if `landlock_enable`, `apply_landlock(...)`;
5. `vm.restore()`.

The ordering was introduced by commit `eea45a2c...`, whose complete product change inserted Landlock after the restored `Vm` had already been constructed.

### `Vm::new()` creates devices before returning

`Vm::new_from_memory_manager()` creates the device manager and enters hypervisor-specific initialization. KVM/MSHV initialization calls:

```text
DeviceManager::create_devices(...)
```

before `Vm::new()` returns.

### Device creation opens disks

`DeviceManager::create_devices()` calls `make_virtio_devices()`, which calls `make_virtio_block_devices()`.

For an ordinary block device, `make_virtio_block_device()` calls:

```rust
open_disk(&DiskOpenOptions {
    path: disk_path,
    readonly: disk_cfg.readonly,
    direct: disk_cfg.direct,
    sparse: disk_cfg.sparse,
    backing_files: disk_cfg.backing_files,
    ...
})
```

For QCOW2 with `backing_files=on`, this can recursively open backing files.

All of this occurs before restore calls `apply_landlock()`.

## Thread inheritance boundary

The original Landlock PR explicitly relies on inheritance: worker threads spawned after the VMM thread is restricted inherit the ruleset.

Restore still starts vCPU threads later in `Vm::restore()`, after Landlock, so vCPU inheritance remains in the intended order.

However `Vm::new()` can start other helper threads during construction. Current examples include rate-limiter threads during `DeviceManager::new()` and serial-manager setup during device creation. Those are created before restore applies the VMM-thread Landlock restriction.

This is a second discriminator, not yet a broad claim that every pre-created helper can perform sensitive filesystem operations. The first executable proof should stay on file-open ordering because its policy consequence is direct.

## Strongest differential probe: QCOW backing path

Use the related QCOW transitive-path finding to make the ordering visible without relying on timing.

### Prepare source state

Create two identical raw backing files:

```text
allowed/base.raw
unlisted/base.raw
```

Create `overlay.qcow2` initially referencing `allowed/base.raw`.

Run the source VM with:

```text
--landlock
--disk path=overlay.qcow2,backing_files=on
--landlock-rules path=allowed/base.raw,access=r
```

Pause and snapshot successfully.

Keep `allowed/base.raw` in place so the saved Landlock rule remains valid.

### Change only the trusted backing reference

After the source VMM is stopped, update the QCOW backing reference so the same overlay now points to:

```text
unlisted/base.raw
```

The new backing file is intentionally absent from the saved Landlock rules.

Use a disposable secondary disk or otherwise keep guest correctness independent of backing contents; the observation is whether the VMM can open the path.

### Fresh-boot control

Boot an equivalent fresh VM with the modified overlay and the same Landlock rule set.

Expected from current source:

```text
restrict_self()
then QCOW backing open
-> permission denied for unlisted/base.raw
```

### Restore case

Restore the snapshot with Landlock enabled from its saved configuration.

Expected from current source ordering:

```text
Vm::new
-> QCOW backing open succeeds before Landlock
-> restrict_self()
-> restore continues with already-open backing descriptor
```

If this differential reproduces, it proves the sandbox path policy depends on lifecycle route.

## Simpler file-open probe if QCOW mutation is inconvenient

Choose any file-backed device whose constructor opens a path inside `Vm::new()` and whose configured path can be changed in the restored configuration before `Vm::new()` runs while keeping the saved Landlock rule set stale.

QCOW remains preferable because the top-level configured path can stay identical while only a transitive backing path changes. That isolates Landlock timing from config-path replacement.

## Important restore-source constraint

Moving `apply_landlock()` mechanically to the top of `vm_restore()` is unlikely to be sufficient.

Restore itself must access resources that fresh boot does not:

- snapshot state via `source_url`;
- memory snapshot/backing files used by the memory manager;
- ordinary VM-config files and devices;
- transitive disk paths such as trusted QCOW backing files.

The selected repair must decide which of these paths are automatically part of restore authority and which remain explicit caller rules.

## Candidate repair boundaries

### Candidate A — collect restore paths, then restrict before `Vm::new()`

Sequence:

1. read enough snapshot metadata to recover/validate configuration;
2. collect the required snapshot/memory paths plus normal VMConfig paths and explicit user rules;
3. apply Landlock;
4. construct `Vm::new()` and open devices under the sandbox;
5. restore runtime state.

This gives fresh/restore parity but requires a complete inventory of restore source files.

Leading design family if the path inventory is bounded and already available before `Vm::new()`.

### Candidate B — pre-open every restore resource intentionally, then restrict

Sequence:

1. validate and pre-open snapshot, memory, disk, and device resources;
2. keep only descriptors needed by restore;
3. apply Landlock;
4. build the VM from those descriptors without new path opens.

This produces a strong authority boundary but is a much larger change because many current device constructors accept paths.

### Candidate C — document restore as setup-before-sandbox

Treat the current ordering as intentional: restore initialization may open configured resources before Landlock, while Landlock protects only steady-state future opens.

This would need explicit project evidence because it conflicts with the original fresh-create rationale and creates observable path-policy differences. Keep it as a competing explanation until maintainers/history or runtime behavior resolves intent.

## Negative controls

1. Fresh VM with authorized backing path succeeds.
2. Fresh VM with unauthorized backing path fails under Landlock.
3. Restore with all backing paths explicitly allowed succeeds.
4. Restore with Landlock disabled succeeds regardless of Landlock rules.
5. Restore source path itself remains accessible under whichever candidate rule inventory is tested.
6. vCPU startup still happens after the chosen restriction point.

## Adjacent contexts

### Live migration receive

Current receive-migration code applies Landlock while reconstructing the destination through a different path. Compare its ordering before generalizing a restore fix; migration may already provide a better model for collecting configuration before creating devices.

### On-demand restore

Memory restore modes may need continued access to snapshot/memory backing after `Vm::new()`. A candidate must preserve those accesses through explicit rules or pre-opened descriptors.

### File-backed console/TPM/vhost-user resources

These can expose additional pre-sandbox opens during `Vm::new()`. Map them only after the QCOW differential establishes the lifecycle invariant.

### Helper threads created in `Vm::new()`

Check rate limiter and serial-manager thread Landlock state after the primary file-open probe. Promote a thread-inheritance subfinding only if one of those workers can perform a post-construction filesystem action that fresh boot blocks but restore allows.

## Evidence boundary

Established:

- fresh-create Landlock design intentionally restricts the VMM before later VM worker/device creation;
- current restore reads snapshot state, constructs `Vm::new()`, and only then calls `apply_landlock()`;
- `Vm::new()` reaches `DeviceManager::create_devices()` before returning;
- block-device creation calls `open_disk()` inside that pre-Landlock restore window;
- QCOW backing files can therefore be opened in that window;
- restore's Landlock ordering comes directly from the original Landlock PR/commit rather than a later accidental refactor;
- original PR rationale explicitly depends on child-thread inheritance from a previously restricted VMM thread;
- no current upstream issue dedicated to this restore-order policy divergence was found in the bounded search.

Pending:

- fresh-vs-restore executable differential on exact current main;
- exact behavior of already-open backing descriptors after restore restriction;
- complete restore path inventory needed before a candidate can move Landlock earlier;
- on-demand restore interaction;
- helper-thread inheritance runtime check;
- candidate code and CI.

## Stop condition

Promote to a product candidate only after the fresh-vs-restore differential reproduces and the required restore source paths are enumerated.

A repair must preserve:

- snapshot state access;
- memory restore access, including on-demand modes where supported;
- normal disk/device restore;
- explicit Landlock denial for paths outside the approved set;
- fresh/restore parity for the same approved file graph;
- correct thread inheritance for workers created after the restriction point.

If runtime shows restore still denies the unlisted backing path through another mechanism, retain the source-order result as a negative and identify that mechanism before changing code.

## Current disposition of the QCOW documentation carrier

Internal draft `teamleaderleo/cloud-hypervisor#18` should remain **HOLD / research-only** until this restore differential is resolved. The documentation statement that callers must grant every QCOW backing path is directionally correct for fresh creation, but publishing it without documenting or fixing restore parity would leave an important lifecycle exception unexplained.

## Next safe action

Build the fresh-vs-restore QCOW differential above on a disposable secondary disk. Preserve both command lines, snapshot config, QCOW backing metadata before/after, Landlock rules, exact error/open result, and cleanup state. Then inspect receive-migration ordering as the nearest working comparison before designing a patch.
