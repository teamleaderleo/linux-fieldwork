# Current Fieldwork

Updated: 2026-08-10

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

### Cloud Hypervisor — propagate ACPI construction failures

**State:** current source/review boundary saturated; exact stored candidate passes the strengthened focused matrix and is byte-identical to the generated tested diff.

- Canonical issue: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8666
- Internal Fieldwork issue: #444
- Branch: `teamleaderleo/cloud-hypervisor:linux-fieldwork/acpi-error-propagation`
- Internal draft PR: `teamleaderleo/cloud-hypervisor#3`
- Validated product carrier head: `0a2f55acbd23b7f44899a69132a4236ef9240027`
- Focused run/job: `31349013458` / `93336246241` — success
- Focused artifact: `9048345416`
- Artifact digest: `sha256:5335c66d23be38b9a988335061918adf8f7f44b4b4b564bf22a9c736d350e210`
- Stored/generated product patch digest: `sha256:4d65cdbcb01a72eb09ae3b905a5d4e46b8e140c4cec8d3e1f00380ac5476628d`

The candidate remains a small two-file correctness fix inside the private `vmm::acpi` module. It introduces `acpi::Error` and propagates checked table-address overflow, allocator/GIC/fw_cfg mutex poisoning, missing fw_cfg at the crate-internal helper boundary, guest-memory write failures, and fw_cfg I/O through one VM-level `CreatingAcpiTables` boundary. Poisoned-lock diagnostics retain the resource name.

Source review preserves IORT header/alignment checks, the validated PCI-segment bound, serial lookup consistency, aarch64 controller/VGIC presence, and fw_cfg table-pointer bookkeeping as explicit invariants. Fixed structure-size checks are compile-time assertions. The separate aarch64 cache-topology runtime panic family remains a successor under canonical issue #8097 and Fieldwork #499 instead of silently widening this patch.

The focused workflow now passes exact source blob verification, `git apply --check`, exact two-file generated scope, `git diff --check`, the repository's actual nightly rustfmt rules, an execution-proven exact unit test with successful-addition and overflow cases, focused Clippy with warnings denied, x86_64 KVM and MSHV compile, fw_cfg compile, TDX compile, and aarch64 KVM and MSHV cross-compile.

Two stronger gates found real refinement work. Focused Clippy rejected the initial `std::result::Result` alias under the repository's denied `clippy::absolute_paths`; the candidate now uses the project-style `result::Result`. Nightly rustfmt then exposed that earlier stable formatting checks had ignored the repository's nightly-only import grouping settings; the runner and workflow now install/use nightly explicitly and the stored patch matches nightly output.

The final workflow generates the product diff, requires `cmp` equality against stored `candidate.patch`, and records SHA-256 for both paths. The artifact records the same `4d65c...` digest for stored and generated patches, so review, application, quality checks, backend/architecture checks, and retained evidence all refer to the same bytes.

Product scope remains 98 insertions and 53 deletions across `vmm/src/acpi.rs` and `vmm/src/vm.rs`; most of the diff is mechanical `Result`/error plumbing.

**Current recommendation:** keep `acpi::Error` with one VM wrapper; keep defensive `MissingFwCfg`; keep the current address-helper test unless a natural second production failure fixture appears; keep the validated/programming invariants explicit. Reopen the product decision for a guarded source-blob change, a canonical fix, a concrete remaining runtime-input panic, a natural second failure fixture, or a supported backend/architecture counterexample.

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

No other active candidate currently outranks the strong-candidate review queue above.

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
