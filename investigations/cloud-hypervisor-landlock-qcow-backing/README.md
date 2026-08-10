# Cloud Hypervisor Landlock coverage for QCOW backing files

Updated: 2026-08-11

Canonical source: `cloud-hypervisor/cloud-hypervisor` `main`
Exact source head: `915d359f97475b1a39d8561f8db514da9e692d19`

Relevant upstream history:

- Landlock implementation: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/6214
- sandboxing tracker: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/5170

Primary owners:

- `vmm/src/vm_config.rs` — `DiskConfig::apply_landlock()` / `VmConfig::apply_landlock()`
- `vmm/src/lib.rs` — Landlock activation during `vm_create()`
- `block/src/formats/qcow/parser.rs` — backing-chain path open
- `docs/landlock.md` — user-visible path policy

Current state: **source-confirmed transitive-path gap; runtime confirmation pending**
Upstream-contact state: **disabled / no contact performed**

## TL;DR

Landlock is applied during `vm_create()` before the VM boots and before the block backend opens a QCOW backing chain.

For each configured disk, Cloud Hypervisor automatically allows only the literal `DiskConfig.path`:

```text
--disk path=/images/overlay.qcow2
              ↓
automatic Landlock rule for /images/overlay.qcow2
```

When `backing_files=on`, the trusted QCOW metadata can later direct the block backend to open another file. That transitive backing path is absent from the automatic Landlock rules.

So this valid configuration family requires an additional manual rule:

```text
--landlock
--disk path=/images/overlay.qcow2,backing_files=on
--landlock-rules path=/base/base.raw,access=r
```

The current Landlock guide already explains this exact operator responsibility for Flat VMDK extent files. It does not explain the equivalent QCOW backing-file case; the guide groups `qcow2` with ordinary disk formats whose configured `path=` is automatically allowed.

The leading repair is therefore **documentation + regression coverage for transitive QCOW backing paths**, not automatic whitelisting from image metadata. Automatic whitelisting would let a disk image expand the process sandbox according to paths stored inside the image, which cuts against the current threat model's requirement that the management stack validate backing-file identity.

## Explain like I'm five

Landlock gives Cloud Hypervisor a list of files it may open.

The config says:

```text
use overlay.qcow2
```

so Cloud Hypervisor puts `overlay.qcow2` on the list.

That QCOW file can say:

```text
my older data lives in base.raw
```

Cloud Hypervisor later tries to open `base.raw`, but Landlock never received that second path. The open is denied unless the person launching the VM added `base.raw` to the list too.

The VMDK documentation already teaches this for descriptor extent files. QCOW backing files need the same treatment.

## Why care

`backing_files=on` is a supported QCOW feature. Landlock is also a supported sandboxing option. Their combination introduces a hidden extra-path requirement that the current user guide does not state.

The practical failure occurs during disk creation/boot as a permission error opening a backing layer. A user following the existing Landlock guide can whitelist every configured disk path and still have the VM fail because the real file graph contains another path.

This is also a security-boundary documentation issue: the management stack is already responsible for validating trusted QCOW backing paths. The same validated path set is the natural source for explicit Landlock rules.

## Exact source observations

### 1. Automatic disk rule covers one path

Current `DiskConfig::apply_landlock()` does only:

```rust
if let Some(path) = &self.path {
    landlock.add_rule_with_access(path, "rw")?;
}
```

It has no image-format branch and does not parse backing metadata.

### 2. VM rules are frozen during `vm_create()`

`VmConfig::apply_landlock()`:

1. constructs a Landlock ruleset;
2. applies each configured disk rule;
3. applies caller-supplied `landlock_rules`;
4. calls `restrict_self()`.

`vm_create()` stores the VM config and applies Landlock before the later boot path creates the block device.

That timing means the backing file must already be covered when the QCOW parser tries to open it.

### 3. QCOW backing files are opened from metadata

With `backing_files=on`, QCOW parsing resolves the backing path and opens it as a separate file. Backing chains can recurse.

The configured overlay path does not imply Landlock permission for a sibling or parent backing file. File rules are path-specific unless the caller explicitly grants a containing directory.

### 4. Existing guide recognizes the same class for VMDK

`docs/landlock.md` says Cloud Hypervisor needs the complete lifetime file list before enabling Landlock.

Its multi-file section then explains that Flat VMDK `path=` names a descriptor while extent data lives in other files, so callers must add those extent paths through `--landlock-rules`.

The preceding wording groups raw, qcow2, VHD, and existing VMDK as formats where Landlock grants access to `--disk path=`. That sentence is true about the automatic rule but incomplete for QCOW2 with backing files enabled.

## Threat-model constraint

The current threat model treats QCOW images as trusted when `backing_files` is enabled and says the management stack must validate that the backing file is the expected value.

That argues against a first repair that automatically reads an arbitrary backing path from the image and adds it to the Landlock allowlist.

The safer policy is:

```text
management stack validates backing chain
        ↓
management stack supplies the validated paths as Landlock rules
        ↓
Cloud Hypervisor sandbox remains an explicit allowlist
```

This mirrors the existing Flat VMDK documentation model.

## First runtime probe

Use a disposable raw backing and QCOW overlay in the same temporary directory so ordinary Unix permissions and mount differences cannot explain the result.

Create:

```text
base.raw
  ↑
overlay.qcow2 (backing file = base.raw)
```

Run three otherwise identical cases.

### A. Feature control — no Landlock

```text
backing_files=on
landlock=off
```

Expected: backing chain opens successfully.

### B. Automatic rules only

```text
backing_files=on
landlock=on
no explicit rule for base.raw
```

Expected from current source: boot/disk open fails with permission denied on the backing path.

### C. Explicit backing rule

```text
backing_files=on
landlock=on
landlock rule for base.raw (read access)
```

Expected: same chain succeeds.

Use a directory rule as an adjacent control only after the exact-file rule proves the owner.

## Additional discriminators

### Relative vs absolute backing path

Run both forms. The policy should depend on the resolved object, not the spelling stored in QCOW metadata.

### Multi-layer chain

After the one-backing case, use:

```text
top.qcow2 -> middle.qcow2 -> base.raw
```

Grant top + middle but omit base. Confirm failure occurs at the first ungranted layer. Then grant all validated layers and confirm success.

This proves the requirement is recursive.

### Landlock disabled

The same chain must remain a passing control, proving the backing parser itself is healthy.

## Candidate repair boundaries

### Candidate A — docs + focused integration test

Update `docs/landlock.md` so the multi-file section covers both:

- Flat VMDK extents;
- QCOW2 backing files when `backing_files=on`.

Explain that callers must explicitly allow every validated backing file or a validated containing directory.

Add a Landlock/QCOW backing test that proves automatic-only denial and explicit-rule success.

**Leading candidate.** It preserves the current explicit sandbox policy and matches the QCOW threat model.

### Candidate B — automatic backing-path rules

Parse backing metadata before `restrict_self()` and add discovered paths automatically.

This is a much broader policy change. It means trusted disk metadata participates directly in defining the process allowlist and creates additional path-resolution/TOCTOU questions.

Keep this out unless project maintainers explicitly prefer automatic transitive rules.

### Candidate C — pre-open validated backing fds

A management layer or VMM pre-opens the validated chain and passes descriptors into the block backend before sandboxing.

This can produce a tighter authority model but requires a much larger block/config API change. There is no evidence for that scope here.

## Negative controls

1. Raw disk + Landlock should continue to work with only its configured path.
2. QCOW without backing files should continue to work with only its configured path.
3. QCOW backing chain + Landlock disabled should work.
4. QCOW backing chain + explicit backing rule should work.
5. Flat VMDK behavior/documented rule model should remain unchanged.
6. A truly absent backing file should keep its ordinary not-found/open error instead of being confused with Landlock denial.

## Evidence boundary

Established:

- automatic disk Landlock rules contain only the configured top-level path;
- caller-supplied Landlock rules are added before `restrict_self()`;
- Landlock is applied during `vm_create()` before later block-device/backing-file opens;
- QCOW backing files are separate recursive file opens;
- current Landlock docs explicitly teach manual transitive-path rules for Flat VMDK but omit QCOW backing chains;
- current QCOW threat model already assigns backing-file validation to the management stack;
- no dedicated current upstream issue or PR for `Landlock + QCOW backing` was found in the bounded search.

Pending:

- executable permission-denied baseline on exact current main;
- exact final error chain and operation label;
- relative/absolute parity;
- multi-layer chain behavior;
- candidate documentation/test diff and CI.

## Stop condition

If the three-case runtime probe matches source prediction and explicit validated rules restore operation, keep the repair at documentation + regression coverage unless fresh project history calls for automatic discovery.

Promote to product-code design only if:

- explicit rules cannot make the supported chain work;
- resolved backing paths differ from the paths the management stack can reasonably whitelist;
- migration/restore changes backing-path identity after the sandbox is frozen;
- a real backend requires opening additional undiscoverable paths after `vm_create()`.

## Next safe action

Build the smallest integration fixture around an existing QCOW backing test: enable Landlock, keep the backing file outside the automatically granted top-level file rule, prove the expected denial, then add one explicit read rule and prove success. Record the exact error chain before editing documentation.
