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

**State:** narrowed candidate is green across the focused test and default, fw_cfg, TDX, and aarch64 compile surfaces. Cleanup and broader fork CI review remain before promotion.

- Canonical issue: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8666
- Internal Fieldwork issue: #444
- Branch: `teamleaderleo/cloud-hypervisor:linux-fieldwork/acpi-error-propagation`
- Internal draft PR: `teamleaderleo/cloud-hypervisor#3`
- Candidate semantic head: `fd25b6848a7ebe676c86985533954e623db4b31e`
- Validated carrier head: `df48ecb3f7c0c23746ecbdf7efc8fbdc384147c0`
- Focused run/job: `31344505710` / `93323825124` — success
- Focused artifact: `9046890513`
- Artifact digest: `sha256:3749e5022ac5aad2cafd713e00a42a1813e04ca82d1c6e7246cb9103d5df676e`
- Broader fork CI: `31344505713` — in progress at last check

Source review narrowed the error boundary before the successful run. Checked table-address overflow, allocator/GIC/fw_cfg mutex poisoning, guest-memory writes, fw_cfg presence at the helper boundary, and fw_cfg I/O are propagated. IORT layout checks, the validated PCI-segment bound, serial lookup consistency, and aarch64 controller/VGIC presence remain explicit invariants.

The focused workflow passes exact-source application, two-file generated scope, diff check, rustfmt, the deterministic overflow unit test, KVM compile, fw_cfg compile, TDX compile, and aarch64 KVM cross-compile. The previous aarch64 red belonged to the harness: `ring` could not find `aarch64-linux-gnu-gcc`; installing `gcc-aarch64-linux-gnu` repaired that gate without changing candidate semantics.

The retained generated diff was reviewed in full and changes only `vmm/src/acpi.rs` and `vmm/src/vm.rs`. The remaining carrier cleanup is to fold the proven narrowing now performed by `run_candidate.py` into the canonical `apply_candidate.py` transform, rerun the same focused matrix, and then classify the broader fork CI independently.

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
