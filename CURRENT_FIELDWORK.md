# Current Fieldwork

Updated: 2026-08-06

This is the live operational board for the strongest current investigations. It is intentionally short. Detailed evidence remains in the linked fork branches, internal pull requests, and Fieldwork issues.

## Proven and packaging

### Cloud Hypervisor — API shutdown lifecycle event gates

**State:** runtime-proven; clean contribution commit is being materialized.

- Canonical issue: `cloud-hypervisor/cloud-hypervisor#8046`
- Diagnostic branch: `teamleaderleo/cloud-hypervisor:linux-fieldwork/api-shutdown-events`
- Clean branch: `teamleaderleo/cloud-hypervisor:linux-fieldwork/api-shutdown-events-clean`
- Internal evidence PR: `teamleaderleo/cloud-hypervisor#1`
- Runtime workflow/job: `30953976821` / `92176887306`
- Runtime artifact: `8915262953`
- Artifact digest: `sha256:eed3ebbca87dba9fa11801d12ea69a3cc57fa137f00a33dc4542dbbd9addec3b`

All four real KVM selectors passed:

- HTTP shutdown;
- HTTP delete/create/boot;
- D-Bus shutdown;
- D-Bus delete/create/boot.

The intended contribution is one signed-off commit changing only `cloud-hypervisor/tests/common/tests_wrappers.rs`. The diagnostic workflow now always attempts to materialize that clean branch after its focused gate passes.

## Active investigations

### Cloud Hypervisor — propagate ACPI construction failures

**State:** exact-source candidate applies cleanly; first run stopped only on rustfmt; formatting repair pushed; compile matrix pending.

- Canonical issue: `cloud-hypervisor/cloud-hypervisor#8666`
- Internal Fieldwork issue: #444
- Branch: `teamleaderleo/cloud-hypervisor:linux-fieldwork/acpi-error-propagation`
- Internal draft PR: `teamleaderleo/cloud-hypervisor#3`
- Failed run: `31012686760`, job `92328666632`
- First incomplete step: `cargo fmt --all -- --check`

The candidate establishes an ACPI-specific error boundary across direct-memory, fw_cfg, and TDX paths. The first failure was one mechanically unformatted expression, not a compile or design rejection. The generator now runs rustfmt before the check. Next gate: focused unit test, default build, fw_cfg build, TDX build, and aarch64 build.

### libarchive — deterministic cpio inode identity mapping

**State:** deterministic baseline and production hypothesis exist; initial failures were carrier defects; repaired runs pending.

- Canonical issue: `libarchive/libarchive#3314`
- Internal Fieldwork issue: #446
- Baseline branch/PR: `linux-fieldwork/cpio-inode-remap`, `teamleaderleo/libarchive#7`
- Candidate branch/PR: `linux-fieldwork/cpio-inode-synthesis-candidate`, `teamleaderleo/libarchive#8`

Source finding:

- newc truncates 64-bit source inode values to 32 bits, allowing distinct source identities to collide;
- odc already uses synthetic archive-local inode values;
- the candidate extends the synthetic policy to newc and keys retained hardlink mappings by `(devmajor, devminor, ino)`.

Initial baseline run `31013548101` reached final link and failed because an older carrier used a nonexistent `assertEqualInt64` helper. The current baseline uses the project’s real `assertEqualInt` helper.

Initial candidate run `31015401080` failed while inserting a forward declaration into the transform script. The wrapper now patches the actual synthesis-prototype marker. Next gate: compile the library and both cpio test binaries, run deterministic identity tests, then run `test_format_newc` and `test_option_c`.

### mkosi — ToolsTree depmod executable boundary

**State:** exact-source patch and focused regression prepared; normal checkout execution still pending.

- Canonical issue: `systemd/mkosi#4319`
- Branch: `teamleaderleo/mkosi:linux-fieldwork/tools-tree-depmod-path`

Finding: `run_depmod()` bypasses the ToolsTree-aware sandbox and uses a chroot command whose executable lookup depends on host `PATH`. Candidate routes depmod through `Context.sandbox()` and uses `--basedir /buildroot` so tools come from ToolsTree while metadata is written to the target root.

Next gate: apply in a normal checkout and run focused pytest, ruff, mypy, and the original host-PATH reproducer.

### BuildKit — rootless/rootful reproducibility

**State:** discriminator and archive comparison tooling validated synthetically; live daemon gate pending.

- Canonical issue: `moby/buildkit#6686`
- Branch: `teamleaderleo/buildkit:linux-fieldwork/rootless-reproducibility`

The tooling compares OCI config diff IDs and reports the first divergent layer plus `/proc` and `/sys` metadata. Next gate: run against matching rootful and rootless BuildKit daemons and locate the earliest divergence boundary.

## Parked or negative results

- bootc #1805: current source already performs fs-verity capability validation before destructive mutation; no duplicate branch opened.
- bootc #1896: upstream PR #2357 merged the requested file-backed `rpm2cpio` workaround; no duplicate work.
- bootc #2318: folds into broader Docker v2s2/composefs support rather than a narrow bootc-owned defect.

## External-contact state

`false; none occurred`.

No canonical upstream issue comments, pull requests, reviews, reactions, emails, or other interactions have been created from this workbench.
