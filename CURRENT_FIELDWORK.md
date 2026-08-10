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

Source review preserves IORT header/alignment checks, the validated PCI-segment bound, serial lookup consistency, aarch64 controller/VGIC presence, and fw_cfg table-pointer bookkeeping as explicit invariants. Fixed structure-size checks are compile-time assertions.

The focused workflow passes exact source blob verification, `git apply --check`, exact two-file generated scope, `git diff --check`, the repository's actual nightly rustfmt rules, an execution-proven exact unit test with successful-addition and overflow cases, focused Clippy with warnings denied, x86_64 KVM and MSHV compile, fw_cfg compile, TDX compile, and aarch64 KVM and MSHV cross-compile.

Two stronger gates found real refinement work. Focused Clippy rejected the initial `std::result::Result` alias under the repository's denied `clippy::absolute_paths`; the candidate now uses the project-style `result::Result`. Nightly rustfmt then exposed that earlier stable formatting checks had ignored the repository's nightly-only import grouping settings; the runner and workflow now install/use nightly explicitly and the stored patch matches nightly output.

The final workflow generates the product diff, requires `cmp` equality against stored `candidate.patch`, and records SHA-256 for both paths. The artifact records the same `4d65c...` digest for stored and generated patches, so review, application, quality checks, backend/architecture checks, and retained evidence all refer to the same bytes.

Product scope remains 98 insertions and 53 deletions across `vmm/src/acpi.rs` and `vmm/src/vm.rs`; most of the diff is mechanical `Result`/error plumbing.

**Current recommendation:** keep `acpi::Error` with one VM wrapper; keep defensive `MissingFwCfg`; keep the current address-helper test unless a natural second production failure fixture appears; keep the validated/programming invariants explicit. Reopen the product decision for a guarded source-blob change, a canonical fix, a concrete remaining runtime-input panic, a natural second failure fixture, or a supported backend/architecture counterexample.

### Cloud Hypervisor — propagate AArch64 cache-discovery runtime errors

**State:** current runtime-error boundary saturated; exact parser and propagation patches pass executable AArch64 fixtures, backend/quality gates, and automatic byte-identity checks.

- Canonical issue: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8097
- Internal Fieldwork issue: #499
- Branch: `teamleaderleo/cloud-hypervisor:linux-fieldwork/cache-runtime-errors`
- Internal draft PR: `teamleaderleo/cloud-hypervisor#6`
- Exact canonical base: `a1fcb9f790616ac615f66de73be540b0b20844b1`
- Validated product carrier head: `044a728ddf5d9dbb00eba04a6df6679e84521441`
- Focused run/job: `31351617608` / `93343416995` — success
- Focused artifact: `9049185049`
- Artifact digest: `sha256:810949828cb8d1a0fd8816f6390acf15a5b8f339f08e94d3561513edd94388ff`
- Parser stored/generated digest: `sha256:6b521032579139478e272d39f5fee89e004bbaf8cea97ef0c68f4c1e200ceb67`
- Propagation stored/generated digest: `sha256:9eadc8528c391a59c40f5507b37487fb8a528bf1a0b5f95d8c0ce961541107f5`

The candidate preserves the existing missing-cache behavior while turning present-but-unusable host cache metadata into ordinary errors. Missing cache root stays cache-less; missing individual properties retain zero/false defaults; other I/O failures, malformed decimal/cache-size values, and checked byte-size overflow return typed `arch::aarch64::cache::Error` values with path/source context.

Cross-context review found two consumers of `read_cache_topology()`, so the same failure propagates through both PPTT/ACPI and AArch64 FDT system setup. The candidate is deliberately stacked on the exact validated #8666 ACPI patch: the runner verifies the immutable prerequisite carrier commit and patch blob, applies/commits that prerequisite locally, then applies only the two #8097 successor patches.

Seven named synthetic AArch64 fixtures execute under qemu-user and pass again on an immediate clean rerun: missing root, missing properties/defaults, valid cache metadata, malformed size, malformed decimal, non-`NotFound` read failure, and checked cache-size overflow. Focused AArch64 Clippy passes for `arch` and `vmm`; AArch64 KVM/MSHV and x86_64 KVM compile gates also pass.

After the semantic matrix went green, temporary formatter and Clippy repair layers were removed. The final carrier stores only `candidate.patch` for cache parsing/tests and `propagation.patch` for FDT/CPU/ACPI propagation. The final workflow regenerates each diff, requires `cmp` equality against each stored patch, and records matching SHA-256 values.

Combined successor scope is five files and +333/-118: `arch/src/aarch64/cache.rs` (+305/-108) plus 28 insertions / 10 deletions across `arch/src/aarch64/fdt.rs`, `arch/src/aarch64/mod.rs`, `vmm/src/acpi.rs`, and `vmm/src/cpu.rs`. Most growth is deterministic fixture coverage and typed error plumbing.

**Current recommendation:** keep missing metadata as fallback, keep present malformed/unreadable metadata as errors, and keep both propagation paths. The fixed-index portability concern has since been reproduced and isolated as Fieldwork #541 instead of widening #8097.

### Cloud Hypervisor — validate AArch64 cacheinfo identity before passthrough

**State:** fixed-index defect reproduced; exact one-file conservative candidate passes runtime/quality/backend gates and automatic byte identity.

- Internal Fieldwork issue: #541
- Branch: `teamleaderleo/cloud-hypervisor:linux-fieldwork/cache-index-portability`
- Internal draft PR: `teamleaderleo/cloud-hypervisor#7`
- Exact canonical base: `a1fcb9f790616ac615f66de73be540b0b20844b1`
- Baseline head: `06f6343cbf3762095b8d808aa8b6a09a30537414`
- Baseline run/job: `31353310424` / `93348082267` — success
- Baseline artifact: `9049729478`
- Baseline artifact digest: `sha256:4e922bac17707e84b836e195d14b7a1253107e56b50b4451d2a6a2b5e2f28658`
- Validated product carrier head: `7713a59e21c48262843da100087454dae3c0772d`
- Final run/job: `31353819973` / `93349565675` — success
- Final artifact: `9049940543`
- Final artifact digest: `sha256:30312c669c81beac2c59cb4b3ce353d94a019934ac550e033095be432c412a00`
- Stored/generated patch digest: `sha256:d54bf458a609eddaf5b7d6de350fb2c1d770b61e254d494df58c6dd43a8be074`

The baseline proves Linux AArch64 cache sysfs indices identify discovered cache leaves rather than fixed architectural levels. The current mapping works for split L1 Data/Instruction plus unified L2/L3, while synthetic Linux-consistent unified-L1 and split-L2 layouts make Cloud Hypervisor assign cache bytes to the wrong guest fields.

The one-file candidate validates each leaf's exported `level` and `type` before filling the existing guest model. It preserves the representable split-L1/unified-L2/L3 path and returns the existing cache-less `None` path with one warning for valid layouts the current FDT/PPTT model cannot faithfully encode, including unified L1, split L2, gaps, and extra cache levels.

All 11 AArch64 cache tests execute under qemu-user and pass twice. Nightly rustfmt, focused AArch64 Clippy, AArch64 KVM/MSHV, x86_64 KVM regression, and stored/generated `cmp` all pass on the exact patch bytes. Product scope is only `arch/src/aarch64/cache.rs`; most of the +177 lines are identity helpers and deterministic fixtures.

**Current recommendation:** keep the conservative recognition/omission boundary. A generic cache-leaf guest model is a separate future design if faithful unified-L1, split-L2, L4+, or heterogeneous topology passthrough becomes desirable.

### Cloud Hypervisor — align PPTT with shared-L2 FDT policy

**State:** real-host-backed FDT/PPTT divergence reproduced; exact 8+/2- PPTT-only candidate passes the full focused matrix and byte identity.

- Internal Fieldwork issue: #542
- Branch: `teamleaderleo/cloud-hypervisor:linux-fieldwork/cache-sharing-pptt`
- Internal draft PR: `teamleaderleo/cloud-hypervisor#8`
- Exact canonical base: `a1fcb9f790616ac615f66de73be540b0b20844b1`
- Baseline head: `5984c730f13cc624aa4afc7c571cc1820b990286`
- Baseline run/job: `31354589117` / `93351815736` — success
- Baseline artifact: `9050195795`
- Baseline artifact digest: `sha256:6cde182b9d479b25b7d20de6fd969c4b65316584607b157f7e3806ad091e07a0`
- Validated product carrier head: `b3c66237ed59f6d7ac521d821f2f9bf138868ead`
- Final run/job: `31354957658` / `93352819836` — success
- Final artifact: `9050335649`
- Final artifact digest: `sha256:fda9508233172888806dd8cc24ebd48578c026723aebdfba2641ce8d58084577`
- Stored/generated patch digest: `sha256:f25ed351643d03097878b96a8899eaa0d92498adce6c1f37f3f1941f316ca1a4`

Historical Cloud Hypervisor review already records an ARMv8 host with L2 `shared_cpu_list=0,4,8,12` and the migration-aware rationale for avoiding a guessed guest L2 sharing relationship. The test-only baseline reproduces the modern discrepancy: the exact stacked cache reader returns `l2_cache_shared=true`, FDT omits L2/L3 for that metadata, while PPTT ignores the flag and retains its private-L2 chain.

The candidate consumes `l2_cache_shared` only in PPTT construction, leaves L1 untouched, and suppresses L2/L3 when host L2 is shared. This restores parity with the established FDT caution without changing cache discovery, error policy, identity recognition, or vCPU affinity.

All 12 AArch64 cache fixtures execute under qemu-user and pass twice. The FDT/PPTT policy discriminator converges to L1-only for shared-L2 hosts; nightly rustfmt, focused AArch64 VMM Clippy, AArch64 KVM/MSHV, x86_64 KVM regression, and exact stored/generated `cmp` all pass. Product scope is `vmm/src/cpu.rs`, +8/-2.

**Current recommendation:** keep the PPTT-only correction. A fuller shared-cache model should wait for stable vCPU-to-host grouping semantics instead of deriving a guest sharing group from CPU0 metadata.

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

No other active candidate currently outranks the strong-candidate review queue above. Further AArch64 cache work should require a concrete supported-host counterexample or a deliberate decision to build a richer guest cache model; the obvious adjacent PPTT descriptor-reuse hypothesis was retired after ACPI specification review.

## Parked or negative results

### Cloud Hypervisor — PPTT cache-descriptor reuse hypothesis

**State:** retired after ACPI specification review.

A first read of `create_pptt()` suggested reusing one serialized L1/L2 cache descriptor across processor nodes might incorrectly imply one physically shared cache. ACPI PPTT explicitly permits identical private resource instances to share one resource structure for table compaction; the processor hierarchy node carries the private-resource relationship. Descriptor reuse alone is therefore valid. Reopen only for guest-visible sharing errors, incorrect hierarchy attachment, unique-reference requirements, or future non-identical instances.

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
