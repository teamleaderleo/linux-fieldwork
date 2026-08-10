# Integration test carrier — fresh boot vs snapshot restore Landlock ordering

Updated: 2026-08-11

Exact upstream head: `915d359f97475b1a39d8561f8db514da9e692d19`

## Existing test surfaces to reuse

`cloud-hypervisor/tests/integration.rs` already contains:

- `snapshot_restore_common::snapshot_and_check_events()`;
- `snapshot_restore_common::_test_snapshot_restore()`;
- standard source/destination API + event-monitor setup;
- UFFD snapshot/restore tests;
- `test_landlock()` and `test_disk_hotplug_with_landlock()`;
- `_test_live_migration_with_landlock()`, which verifies the destination sandbox by attempting a path that was not pre-authorized.

There is no snapshot-restore + Landlock test in the current integration file.

The new test should reuse the snapshot event/cleanup helpers and the Landlock hotplug test's error/cleanup conventions. Avoid adding a new harness.

## Critical fixture layout

Use **separate host directories** so Landlock rules do not accidentally cover the negative path.

```text
vm-dir/
  overlay.qcow2         # configured disk path; automatically granted

allowed-base-dir/
  base.raw              # explicitly granted read access

unlisted-base-dir/
  base.raw              # deliberately absent from every Landlock rule

snapshot-dir/           # explicitly granted rw so vm.snapshot can create files
  config.json
  state.json
  memory-ranges
```

Do not place `unlisted-base-dir` beneath any rule granted for `vm-dir`, `allowed-base-dir`, or `snapshot-dir`.

Do not use `path=<guest.tmp_dir>,access=rw` for this test: that common convenience rule would grant the negative backing path and make the discriminator useless.

## Prepare equivalent backing bytes

Create `allowed-base-dir/base.raw` with a small deterministic byte pattern or filesystem.

Copy it byte-for-byte to `unlisted-base-dir/base.raw`.

Create the overlay with a raw backing file:

```text
qemu-img create -f qcow2 \
  -F raw \
  -b <allowed-base-dir>/base.raw \
  <vm-dir>/overlay.qcow2
```

Attach this as a **secondary** disk. Keep the normal boot disk unchanged so a backing-path failure cannot be confused with root-disk boot correctness.

## Source VM

Start the ordinary integration guest with:

```text
--landlock
--disk path=<vm-dir>/overlay.qcow2,image_type=qcow2,backing_files=on
--landlock-rules path=<allowed-base-dir>/base.raw,access=r
--landlock-rules path=<snapshot-dir>,access=rw
```

The exact option parser may require both rules in one `--landlock-rules` argument, matching existing tests.

Controls before snapshot:

1. guest boots;
2. VMM API responds;
3. secondary disk is visible if a simple guest-side check is available;
4. `snapshot-dir` already exists before the VMM starts so Landlock can open/grant it.

Pause and snapshot with the existing event helper.

Then terminate the source process using the suite's existing cleanup helper.

## Mutate only the trusted backing reference

After the source process is gone, change the QCOW metadata without copying data:

```text
qemu-img rebase -u \
  -f qcow2 \
  -F raw \
  -b <unlisted-base-dir>/base.raw \
  <vm-dir>/overlay.qcow2
```

The overlay path stays identical. Only the transitive backing reference changes.

Because the two raw bases are byte-identical, any guest-visible data change is removed from the discriminator. The question is path authority/open ordering.

## Baseline current-main observations

Run two paths against the same modified overlay and saved rule set.

### A. Fresh boot control

Start an equivalent fresh VMM with Landlock and the same rules:

```text
allowed: overlay.qcow2 (automatic)
allowed: old allowed-base/base.raw
allowed: snapshot-dir
unlisted: new backing path
```

Expected current-main source behavior:

```text
apply Landlock
Vm::new
open overlay
open unlisted backing
-> permission denied
```

Required assertion:

- fresh VM fails to boot/create the secondary disk through an open/permission error;
- process/API cleanup remains normal.

### B. Snapshot restore

Restore the saved snapshot after the same backing metadata change.

Expected current-main source behavior:

```text
read state/config
Vm::new
open overlay
open unlisted backing  # before Landlock
apply saved Landlock rules
vm.restore
```

Required assertion:

- restore progresses past disk construction and becomes a usable/restored VM, or at minimum reaches a state proving the unlisted backing was successfully opened;
- no rule in the saved config grants `unlisted-base-dir`.

The strongest result is:

```text
fresh boot: denied
restore: accepted
```

with identical top-level disk configuration and Landlock rule set.

## Candidate result

After moving Landlock before `Vm::new()` with temporary current-source read authority:

```text
fresh boot: denied
restore: denied
```

for the unlisted backing case.

Then rebase the overlay back to the explicitly allowed backing path and prove restore succeeds.

## Moved-snapshot control

Copy the complete snapshot directory to a fifth, separate path that is absent from the saved Landlock rules.

Candidate restore should succeed from:

```text
source_url=file://<copied-snapshot-dir>
```

because the **current** restore source receives temporary read authority.

This catches the regression that a naive “move apply_landlock earlier” patch would introduce.

## On-demand control

Run one candidate restore with:

```text
memory_restore_mode=ondemand
```

The current source's UFFD snapshot tests provide the existing setup patterns.

Required observations:

- `memory-ranges` opens under the temporary source rule;
- UFFD handler starts after Landlock;
- restore reaches ordinary completion/prefault behavior;
- guest remains usable;
- an unrelated path remains denied.

## Process cleanup

Retain exact cleanup discipline from the existing integration suite:

- kill/wait source after snapshot;
- kill/wait each fresh-control and restore child;
- remove snapshot and disposable backing directories only after child output is captured;
- preserve stderr from the fresh denial and any restore failure;
- verify no VMM process remains.

## Failure-owner checklist

When a gate fails, classify before changing product code:

- `qemu-img` fixture creation/rebase;
- Landlock capability/host kernel;
- snapshot destination permission;
- QCOW parser/backing open;
- restore source permission;
- memory snapshot read;
- product ordering;
- test cleanup.

A fresh-control failure for the wrong reason does not prove the Landlock differential.

## Minimal promotion gate

A product branch becomes justified when baseline current main produces:

```text
fresh boot with unlisted backing -> Landlock denial
snapshot restore with same unlisted backing -> backing opened before Landlock
```

and the candidate turns the second result into the same denial while preserving moved-snapshot and ordinary authorized restore controls.
