# Candidate design — apply Landlock before restored VM construction

Updated: 2026-08-11

Exact upstream base: `915d359f97475b1a39d8561f8db514da9e692d19`

Status: **design candidate only; runtime differential and compile carrier still required**

## Selected design family

The smallest coherent candidate is:

1. recover and validate the saved `VmConfig`;
2. read `state.json` while the VMM still has its pre-restore authority;
3. derive a temporary read-only Landlock rule from the **current** `RestoreConfig.source_url` directory;
4. apply the normal saved VM rules plus that temporary restore rule;
5. construct `Vm::new()` under Landlock;
6. let `MemoryManager::new_from_snapshot()` open `memory-ranges` under Landlock;
7. let restored device constructors open disks/backing files under Landlock;
8. call `vm.restore()`.

This matches the current receive-migration policy: configuration is known before restored constructors run, and constructors execute inside the Landlock domain.

## Why the current source directory is temporary authority

`RestoreConfig.source_url` is supplied for the restore operation. It can differ from the location serialized in a snapshot's old rules because snapshots can be copied or moved.

The restore source is therefore operation-specific authority, similar to received host-specific FDs: needed to perform this restore, but undesirable as a permanent mutation of the VM's saved policy.

Permanently appending each restore source to `VmConfig.landlock_rules` would accumulate stale paths across restore/snapshot cycles.

## Proposed API refinement

Current `VmConfig::apply_landlock()` creates a ruleset, adds all saved/configured paths, adds `landlock_rules`, and immediately calls `restrict_self()`.

Add a crate-private variant that accepts temporary extra rules while retaining the existing call for create/receive paths.

Conceptually:

```rust
impl VmConfig {
    pub(crate) fn apply_landlock(&self) -> LandlockResult<()> {
        self.apply_landlock_with_extra_rules(&[])
    }

    pub(crate) fn apply_landlock_with_extra_rules(
        &self,
        extra_rules: &[LandlockConfig],
    ) -> LandlockResult<()> {
        let mut landlock = Landlock::new()?;

        // existing automatic VmConfig rules
        // existing self.landlock_rules

        for rule in extra_rules {
            rule.apply_landlock(&mut landlock)?;
        }

        landlock.restrict_self()?;
        Ok(())
    }
}
```

Exact helper naming can change. Keep the public configuration schema unchanged.

## Restore-side change

Current lower helper ordering is effectively:

```rust
let snapshot = recv_vm_state(source_url)?;
let mut vm = Vm::new(..., Some(&snapshot), Some(source_url), ...)?;
if config.landlock_enable {
    apply_landlock(&mut config)?;
}
vm.restore()?;
```

Candidate ordering:

```rust
let snapshot = recv_vm_state(source_url)?;

if config.landlock_enable {
    let source_path = url_to_path(source_url)?;
    let extra = [LandlockConfig {
        path: source_path,
        access: "r".to_string(),
    }];
    config.apply_landlock_with_extra_rules(&extra)?;
}

let mut vm = Vm::new(..., Some(&snapshot), Some(source_url), ...)?;
vm.restore()?;
```

The exact code should avoid holding the config mutex across `Vm::new()`.

## Why directory read is the leading scope

The fixed snapshot files live under one directory:

- `config.json`
- `state.json`
- `memory-ranges`

The first two are already read before the restriction point. `memory-ranges` is read after it, and on-demand mode keeps the file open in the UFFD handler.

Granting the explicitly selected restore directory read access:

- covers the fixed snapshot file set;
- supports on-demand reads;
- supports future snapshot files under the same root without moving the sandbox later again;
- remains bounded to the caller-selected restore source.

A three-file explicit rule list is a viable competing implementation if project review prefers narrower rights.

## Critical behavior changes to prove

### Fresh-vs-restore QCOW parity

After the change, a QCOW backing path outside saved/explicit VM rules should be denied on both:

```text
fresh boot
snapshot restore
```

The current source predicts restore-only acceptance because the backing fd is acquired before Landlock.

### Moved snapshot

A copied snapshot restored from a new source directory absent from saved rules should continue to work because the current restore source is temporarily allowed read-only.

### On-demand memory

`memory-ranges` must remain readable through the already-open fd in `FileUffdMemorySource`, and `uffd-handler` should now be spawned after Landlock so it inherits the domain.

### Original-location control

A snapshot restored from its original pre-authorized directory must remain unchanged.

## Errors and ownership

The candidate should make failures occur at the real owner:

- unavailable/unauthorized restore source -> restore source/Landlock setup error;
- unauthorized disk/backing path -> device/block open permission error during `Vm::new()`;
- invalid snapshot bytes -> config/state deserialize error before restriction where currently appropriate;
- memory snapshot failure -> MemoryManager restore error under the selected source rule.

Do not convert ordinary disk permission errors into generic Landlock setup failures.

## Security and lifecycle boundary

This change does not let snapshot metadata enlarge disk/device authority.

The only new temporary rule comes from the restore API's explicit `source_url`, which the caller already selected as the snapshot source.

Disk paths, QCOW backing paths, memory-zone files, payloads, TPM sockets, VFIO paths, and caller Landlock rules continue to come from the normal saved configuration/policy.

## Receive-migration control

Leave `vm_receive_config()` unchanged.

It already applies Landlock before hypervisor VM, MemoryManager, and device creation. The snapshot candidate should converge toward that ordering without sharing code prematurely.

A later refactor can unify the two paths only if the duplicate code becomes a maintenance problem after behavior is proven.

## Test carrier plan

Keep the first executable carrier focused on ordering, with a disposable secondary QCOW disk.

### Test 1 — restore rejects unlisted backing path

1. boot/snapshot a Landlocked VM with an authorized backing path;
2. stop source;
3. change the overlay's trusted backing reference to an unlisted sibling path containing equivalent bytes;
4. restore with the candidate;
5. assert restore returns a permission/open failure before VM becomes runnable.

Baseline current main should accept/open that backing path during pre-Landlock `Vm::new()`.

### Test 2 — moved snapshot succeeds

1. copy the snapshot directory to another path absent from saved rules;
2. restore candidate from the copied directory;
3. assert snapshot state + memory restore succeeds because the current source directory receives temporary read authority.

### Test 3 — ordinary fresh control

Fresh boot with the same unlisted backing path should fail under both baseline and candidate.

### Test 4 — on-demand restore

Restore with `memory_restore_mode=ondemand`; confirm boot/resume, page faults/prefault completion, and no permission regression reading `memory-ranges`.

## Stop signals

Abandon or revise this candidate if execution shows any of these:

- current baseline restore already denies the unlisted backing path before Landlock through another mechanism;
- `source_url` can represent a non-file source in snapshot restore where a filesystem rule is invalid;
- restored memory requires path access outside the chosen source directory after `Vm::new()`;
- a worker needed by restore is intentionally created before Landlock and cannot safely move after it;
- adding current source read authority conflicts with an established project policy.

## Upstream packet boundary

No upstream packet should be prepared until:

1. baseline fresh-vs-restore differential is executed;
2. moved-snapshot control is executed;
3. candidate compiles and passes focused restore tests;
4. on-demand restore is exercised;
5. full diff is reviewed for rule lifetime and config mutation;
6. external contact is explicitly authorized.
