# Current Fieldwork

Updated: 2026-08-07

This is the live operational board for the strongest current investigations. Detailed evidence remains in the linked fork branches, internal pull requests, Fieldwork issues, and retained CI artifacts.

## Submitted upstream

### Cloud Hypervisor — API shutdown lifecycle event gates

**State:** human-submitted upstream; review pending.

- Canonical issue: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8046
- Upstream PR: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8699
- Fieldwork issue: `teamleaderleo/linux-fieldwork#423`
- Submission branch: `teamleaderleo/cloud-hypervisor:fix/8046-shutdown-events`
- Submitted head: `f7e386b074138700cb57101b8c3ef0ecc069a018`
- Archived evidence PR: `teamleaderleo/cloud-hypervisor#1`
- Superseded fork review PR: `teamleaderleo/cloud-hypervisor#5`
- Current canonical/fork-main base: `538237492941914440eec589ae4d2bfe33f7f108`
- Runtime workflow/job: `30953976821` / `92176887306`
- Runtime artifact: `8915262953`
- Artifact digest: `sha256:eed3ebbca87dba9fa11801d12ea69a3cc57fa137f00a33dc4542dbbd9addec3b`

All four real KVM selectors passed: HTTP shutdown, HTTP delete/create/boot, D-Bus shutdown, and D-Bus delete/create/boot.

The submitted branch is exactly one commit ahead of the synchronized upstream base and changes only `cloud-hypervisor/tests/common/tests_wrappers.rs`: 32 additions, 15 deletions. The final version preserves explanatory comments around normal guest poweroff and the VMM-owned shutdown-event completion gate.

Submission hygiene is present in the submitted commit: valid `tests:` component, wrapped explanatory body, `Fixes #8046`, `Assisted-by: ChatGPT:GPT-5.6 Thinking`, and DCO `Signed-off-by: Leo Li <cheerleaderleo@outlook.com>`.

The upstream PR body explains why `--no-shutdown` is needed: it keeps the VMM/API process alive after guest poweroff so the tests can exercise the subsequent boot or delete/create transition. The test then waits for the exact VMM `shutdown` event instead of treating SSH loss as completion.

Earlier fork materialization commits and internal interaction surfaces referenced the canonical issue directly, producing noisy GitHub timeline backlinks. Those are historical. `ADAPTIVE_COORDINATION.md` already requires `redirect.github.com` for external GitHub references in interaction surfaces; current live records now follow that rule.

## Proven and ready for human review

### BuildKit — rootless/rootful reproducibility

**State:** product defect reproduced and runc/native candidate proven end to end; ready for human review with a backend-scope decision.

- Canonical issue: https://redirect.github.com/moby/buildkit/issues/6686
- Internal Fieldwork issue: #229
- Branch: `teamleaderleo/buildkit:linux-fieldwork/rootless-reproducibility`

Exact-current matching rootful/rootless native-snapshotter workers reproduced the divergence without registry input. Rootful committed runtime-created `/proc` and `/sys` mountpoint stubs while rootless omitted `/sys`. Pre-creating the mountpoints made the control converge.

The candidate reuses BuildKit's existing mount-stub ownership cleanup but feeds it the finalized OCI spec after rootless conversion. Strict patch application, focused ownership tests, candidate binary builds, matching rootful/rootless runc/native workers, implicit parity, and explicit-control parity all passed. The remaining caveat is live containerd-worker/runtime coverage; runc/native is proven.

## Strong candidate — human design review useful

### libarchive — deterministic cpio inode identity mapping

**State:** baseline defect proven; production candidate focused tests, normal CI, and lint are green. Main remaining question is compatibility policy, not basic correctness.

- Canonical issue: https://redirect.github.com/libarchive/libarchive/issues/3314
- Internal Fieldwork issue: #446
- Baseline branch/PR: `linux-fieldwork/cpio-inode-remap`, `teamleaderleo/libarchive#7`
- Candidate branch/PR: `linux-fieldwork/cpio-inode-synthesis-candidate`, `teamleaderleo/libarchive#8`
- Baseline run: `31047067855` — success
- Candidate focused run: `31047099193` — success
- Candidate normal CI: `31047096729` — success across Linux, macOS, Windows, and FreeBSD jobs
- Candidate lint: `31047099122` — success

The deterministic baseline constructs two 64-bit source inode values with identical low 32 bits and proves that current newc encoding collapses them to the same archive identity. Odc already synthesizes archive-local inode values and provides project precedent.

The candidate synthesizes all nonzero newc archive inode identities in encounter order and retains hardlink mappings by `(devmajor, devminor, ino)`. Focused tests prove distinct large identities remain distinct, repeated hardlinks remain equal, and the same inode on another device remains separate. `test_write_format_cpio`, `test_write_format_cpio_newc`, `test_format_newc`, and `test_option_c` all pass.

CIFuzz run `31047099243` is not candidate evidence: the OSS-Fuzz integration fetched `refs/pull/8/merge` from canonical `libarchive/libarchive`, so it tested canonical PR #8 rather than fork PR #8 and then failed in unrelated generated test-list infrastructure. Do not treat that red badge as a candidate failure.

**Human decision:** is changing representable newc inode values to archive-local sequential identities an acceptable compatibility tradeoff? It gives collision-free, host-independent behavior and preserves hardlink identity, but no longer preserves source inode numbers when they happen to fit in 32 bits.

## Active investigation

### Cloud Hypervisor — propagate ACPI construction failures

**State:** error-boundary design remains plausible; latest focused run exposed one candidate transform bug plus one test-feature configuration problem. Not ready for human review yet.

- Canonical issue: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8666
- Internal Fieldwork issue: #444
- Branch: `teamleaderleo/cloud-hypervisor:linux-fieldwork/acpi-error-propagation`
- Internal draft PR: `teamleaderleo/cloud-hypervisor#3`
- Latest focused run/job: `31046631486` / `92443620996`

Latest run passed exact-source application, generated-scope checks, and rustfmt. The focused test build then found:

1. a real aarch64 transform bug: the generated code attempted to lock `interrupt_controller` without first binding it from `device_manager.get_interrupt_controller()`;
2. a separate test invocation problem: building VMM tests without a hypervisor backend produced unrelated uninhabited-hypervisor/VFIO errors.

Next gate: restore the missing interrupt-controller binding, run the unit test with a real backend feature, then execute default, fw_cfg, TDX, and aarch64 compile surfaces.

## Parked or negative results

### mkosi — ToolsTree depmod hypothesis

**State:** retired after source review.

Current `chroot_cmd()` already establishes `PATH=/usr/bin:/usr/sbin` inside the target, covering the reported host-PATH failure while preserving target `depmod` configuration semantics. Moving `depmod` into ToolsTree with `--basedir` would add configuration/version risk. Do not revive the retained patch without new evidence.

Other parked results:

- bootc #1805: current source already performs fs-verity capability validation before destructive mutation; no duplicate branch opened.
- bootc #1896: upstream PR #2357 merged the requested file-backed `rpm2cpio` workaround; no duplicate work.
- bootc #2318: folds into broader Docker v2s2/composefs support rather than a narrow bootc-owned defect.

## External-contact state

`true — Cloud Hypervisor PR #8699 was submitted by the human contributor on 2026-08-07.`

No other canonical upstream pull requests, issue comments, reviews, reactions, emails, or other intentional interactions have been created from this workbench. Historical automatic cross-reference events were generated by direct canonical issue references in fork commits and internal GitHub interaction surfaces; current live records use redirect links to avoid creating additional backlinks.
