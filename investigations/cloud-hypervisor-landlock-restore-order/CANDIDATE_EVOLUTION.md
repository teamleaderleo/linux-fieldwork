# Landlock restore-order candidate evolution

Updated: 2026-08-12

Parent: `investigations/cloud-hypervisor-landlock-restore-order/README.md`
Exact upstream base: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: **disabled / no upstream contact performed**

## TL;DR

The first product carrier identified the right ownership family but placed the restriction too late. Adjacent source review defeated it before promotion.

### v1 — retained provenance, superseded design

Internal draft: `teamleaderleo/cloud-hypervisor#31`
Exact head: `6fb65eefe721fbdd74e9c7de922f992f8a182ce0`
Shape: two files, +8/-12.

v1 moved the snapshot-only Landlock call from after `Vm::new()` to the seam immediately after `MemoryManager::new_from_snapshot()` and before `Vm::new_from_memory_manager()`.

That fixes device-manager ordering, including QCOW backing opens, but adjacent review found two earlier owners that still execute before the restriction:

1. `MemoryManager::new()` can open configured memory-zone backing files while reconstructing snapshot memory.
2. On-demand restore calls `restore_by_uffd()`, which opens the snapshot `memory-ranges` file and then spawns the `uffd-handler` thread before `MemoryManager::new_from_snapshot()` returns.

Therefore v1 does not restore the fresh-create inheritance boundary completely. It remains useful provenance because it proved the device-construction seam but is not the selected design.

## v2 — selected design family

The restriction moves to the beginning of snapshot `Vm::new()`, after `Vmm::vm_restore()` has already read snapshot metadata and pre-created console resources, but before snapshot memory reconstruction.

The existing VM configuration already grants its normal memory-zone, disk, payload, console, device, socket, and explicit Landlock paths. Snapshot restore needs two additional resources that do not belong to ordinary fresh-create authority:

### `memory-ranges`

`MemoryManager::new_from_snapshot()` derives exactly:

```text
url_to_path(source_url) / "memory-ranges"
```

Eager restore opens this file to refill guest memory. On-demand restore opens the same file and retains its descriptor inside `FileUffdMemorySource`.

v2 grants this exact file **read-only**. It does not grant the whole snapshot directory because `config.json` and `state.json` were already read before `Vm::new()` starts.

### `/dev/userfaultfd`

On-demand restore prefers opening `/dev/userfaultfd` read/write and falls back to the `userfaultfd(2)` syscall when the device path is unavailable.

If on-demand mode is selected **and** `/dev/userfaultfd` exists, v2 grants that exact node `rw`. If the node does not exist, no path rule is added, preserving the syscall fallback instead of turning a missing optional device into a Landlock setup failure.

## Required ordering after v2

```text
Vmm::vm_restore
  read config.json + state.json
  pre-create console resources
  Vm::new(snapshot)
    derive exact restore-only rules
    apply VM Landlock + restore-only rules
    create/restore MemoryManager
      memory-zone backing opens happen under Landlock
      memory-ranges open happens under Landlock
      optional /dev/userfaultfd open happens under Landlock
      uffd-handler inherits Landlock
    create CPU/device managers
      disk and transitive QCOW backing opens happen under Landlock
      helper threads inherit Landlock
  vm.restore
```

Fresh create remains unchanged because the extra path is snapshot-only. Receive-migration remains unchanged because it calls `new_from_memory_manager()` after applying its own Landlock policy.

## Implementation shape

The selected product shape is still bounded:

1. expose the existing `memory-ranges` filename constant within the crate so restore code does not duplicate the format string;
2. extend `VmConfig::apply_landlock()` with an internal variant that accepts additional `LandlockConfig` rules, while preserving the existing no-extra-rules wrapper for fresh create and receive migration;
3. in snapshot `Vm::new()`, add read-only `memory-ranges` and conditional `rw` `/dev/userfaultfd`, then apply Landlock before any snapshot memory reconstruction;
4. remove the old late restore restriction from `Vmm::vm_restore()`.

No disk-specific or QCOW-specific policy enters the product patch. QCOW remains the discriminator proving why generic construction ordering matters.

## Evidence supporting the move

### Generic file-descriptor mechanism

Hosted run/job `31547742820` / `93963728979`:

```text
allowed path + new open      -> succeeds
unlisted path + new open     -> PermissionDenied
unlisted path + old open FD  -> remains readable
```

### Real QCOW backing chain

Hosted run/job `31548103949` / `93964786948`:

```text
restrict before QcowDisk::new -> exact backing open PermissionDenied
construct before restrict     -> post-restriction read returns backing marker bytes
```

### Adjacent source review

`restore_by_uffd()` explicitly spawns `uffd-handler` during snapshot `MemoryManager` construction. This makes the earlier restriction point necessary for inheritance parity, not merely for path-open parity.

## Stop rule

Do not promote v2 until:

- exact product bytes pass repository formatting, Clippy, backend builds, DCO, and package checks;
- eager snapshot restore still reaches `memory-ranges` under Landlock;
- on-demand restore can create UFFD through `/dev/userfaultfd` where present or the syscall fallback where absent;
- the QCOW negative control stays denied after the candidate restriction;
- a full VMM restore fixture confirms the saved configuration remains restorable when all required paths are approved.
