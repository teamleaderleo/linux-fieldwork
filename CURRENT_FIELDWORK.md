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

### Cloud Hypervisor — propagate ACPI construction failures

**State:** human-submitted upstream; maintainer approved; canonical CI / merge pending.

- Canonical issue: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8666
- Upstream PR: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8709
- Fieldwork issue: `teamleaderleo/linux-fieldwork#444`
- Submission branch: `teamleaderleo/cloud-hypervisor:fix/8666-acpi-errors`
- Submitted head: `e9c86bacee14a2fd6fe871dc678c6b3f1ac4012a`
- Canonical base: `a1fcb9f790616ac615f66de73be540b0b20844b1`
- Maintainer review: Rob Bradford — approved, `Thanks!`
- Canonical CI run: `31367757232` — in progress at last check
- Frozen product diff digest: `sha256:76c53e120c22dab4886904a875e3aba86ae6d49130e4080cbcdb46ad3df56466`
- Primary exact-byte validation run/job: `31367122335` / `93387811635`
- Validation artifact: `9054647068`
- Artifact digest: `sha256:bd30f0644818a73f2827a5eed5a497c58210ec87c6e0c2e8abacc934d65c010b`
- Archived superseded carrier: `teamleaderleo/cloud-hypervisor#3`

The submitted two-file patch is 73 additions / 48 deletions. It gives the private ACPI path its own error type for checked guest-address overflow, missing fw_cfg, fw_cfg ACPI-delivery I/O failures, and guest-memory write failures; the VM wraps these once as `CreatingAcpiTables` and returns them through boot.

The broader first candidate also propagated three poisoned mutexes. That handling was deliberately removed before submission because it introduced a local ACPI mutex-poison policy that the wider VMM does not share. The narrowing also removed FACP/TDX `Result` churn that existed only for poison handling. Fixed SRAT type sizes remain compile-time assertions, and the duplicate runtime size test was removed.

The final validation carrier verifies exact product identity before testing the product commit itself. Nightly rustfmt, the focused address success/overflow unit test, VMM Clippy with warnings denied, x86_64 KVM/MSHV, fw_cfg, TDX, and AArch64 KVM/MSHV passed. A validation-only follow-up at `6cc1559217fb5e7e73246095b2b5d2c10d1c4476` also passed the repository's required RISC-V KVM build without changing product bytes.

A VM boot smoke test was not run and is explicitly disclosed in the upstream PR. Detailed rationale, exact receipts, discarded poison design, Rust learning notes, final PR wording, and packaging lessons live under `investigations/cloud-hypervisor-acpi-error-propagation/`.

## Proven and ready for human review

### BuildKit — rootless/rootful reproducibility

**State:** product defect reproduced and runc/native candidate proven end to end; ready for human review with a backend-scope decision.

- Canonical issue: https://redirect.github.com/moby/buildkit/issues/6686
- Internal Fieldwork issue: #229
- Branch: `teamleaderleo/buildkit:linux-fieldwork/rootless-reproducibility`

Exact-current matching rootful/rootless native-snapshotter workers reproduced the divergence without registry input. Rootful committed runtime-created `/proc` and `/sys` mountpoint stubs while rootless omitted `/sys`. Pre-creating the mountpoints made the control converge.

The candidate reuses BuildKit's existing mount-stub ownership cleanup but feeds it the finalized OCI spec after rootless conversion. Strict patch application, focused ownership tests, candidate binary builds, matching rootful/rootless runc/native workers, implicit parity, and explicit-control parity all passed. The remaining caveat is live containerd-worker/runtime coverage; runc/native is proven.

## Strong candidate — human design review useful

### Cloud Hypervisor — propagate AArch64 cache-discovery runtime errors

**State:** submitted-ACPI restack complete; exact parser and propagation patches pass executable AArch64 fixtures, backend/quality gates, and stable full-index byte identity.

- Canonical issue: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8097
- Internal Fieldwork issue: #499
- Branch: `teamleaderleo/cloud-hypervisor:linux-fieldwork/cache-runtime-errors`
- Internal draft PR: `teamleaderleo/cloud-hypervisor#6`
- Exact canonical base: `a1fcb9f790616ac615f66de73be540b0b20844b1`
- Submitted ACPI prerequisite: `e9c86bacee14a2fd6fe871dc678c6b3f1ac4012a`
- Validated product carrier head: `a696e285eaece00335e106acdfb5a651ccb2261f`
- Focused run/job: `31383431370` / `93438452796` — success
- Focused artifact: `9060813988`
- Artifact digest: `sha256:8aa69452ae02c872ecc7e3c89551c5eb6b554a5d1678d6227a53ff7e5c479576`
- Parser stored/generated digest: `sha256:223c3d5af488b47de2e092316ee1f63d609d3fcc65b955579431e3c3f74ce1d1`
- Propagation stored/generated digest: `sha256:2b5f2269c4f36c92931954c2befc20b23fe6867fcf08a2370416b8d7344bc4a4`

The candidate preserves the existing missing-cache behavior while turning present-but-unusable host cache metadata into ordinary errors. Missing cache root stays cache-less; missing individual properties retain zero/false defaults; other I/O failures, malformed decimal/cache-size values, and checked byte-size overflow return typed `arch::aarch64::cache::Error` values with path/source context.

Both consumers are covered: failures propagate through PPTT/ACPI and AArch64 FDT system setup. The refreshed carrier reconstructs the exact submitted ACPI two-file prerequisite, applies the five-file cache successor, and verifies exact full-index stored/generated patch identity so Git object-abbreviation length cannot mutate the receipt.

Seven named synthetic AArch64 fixtures execute under qemu-user and pass twice: missing root, missing properties/defaults, valid cache metadata, malformed size, malformed decimal, non-`NotFound` read failure, and checked cache-size overflow. Nightly rustfmt, AArch64 `arch` + `vmm` Clippy, AArch64 KVM/MSHV, and x86_64 KVM VMM Clippy all pass.

**Current recommendation:** keep missing metadata as fallback, keep present malformed/unreadable metadata as errors, and keep both propagation paths. Treat `a696e285...` / run `31383431370` as the packaging baseline. Cache identity, sharing, and affinity are now proven in the separate successor candidates below.

### Cloud Hypervisor — validate AArch64 cacheinfo identity before passthrough

**State:** fixed-index defect reproduced; refreshed one-file candidate passes 17 runtime fixtures, quality/backend gates, and stable semantic patch identity on the final prerequisite chain.

- Internal Fieldwork issue: #541
- Branch: `teamleaderleo/cloud-hypervisor:linux-fieldwork/cache-index-portability`
- Internal draft PR: `teamleaderleo/cloud-hypervisor#7`
- Exact canonical base: `a1fcb9f790616ac615f66de73be540b0b20844b1`
- Validated product carrier head: `8dfd55a96b0cbf3d6891c25735455b8b793133e9`
- Final run/job: `31384297689` / `93441155201` — success
- Final artifact: `9061137258`
- Final artifact digest: `sha256:6010ea690bdc8e8a9376f337b69f584520802204b27ce82ccc70067329be4f9a`
- Stored patch digest: `sha256:c3c0b19e8025fa8b1f90d9b2378165676f877fe2572c52b62e3ab1871e13e1e9`
- Regenerated full-index digest: `sha256:ee57a555a56792604f7128304fe5658f7ff6198b2f3e9961b41a1fff515d89fe`
- Stable patch ID: `ebb2816be4e0969b2385d5fe155f3b50359b04b9`

The baseline defect is unchanged: Linux AArch64 cache sysfs indices identify discovered cache leaves rather than fixed architectural levels. The candidate maps leaves by exported `level` + `type`, preserves representable split-L1/unified-L2/L3, tolerates higher levels without shifting lower mappings, and omits valid <=L3 layouts the current guest model cannot faithfully encode.

All 17 AArch64 cache tests execute under qemu-user and pass twice. Nightly rustfmt, AArch64 `arch` Clippy, AArch64 KVM/MSHV, and x86_64 KVM VMM Clippy pass. Product scope remains only `arch/src/aarch64/cache.rs`.

The retained historical patch uses abbreviated Git object IDs while the regenerated receipt uses full IDs; both are pinned and produce the same stable patch ID, proving identical product hunks without rewriting the frozen patch for presentation metadata.

**Current recommendation:** keep the conservative recognition/omission boundary. A generic cache-leaf guest model remains a separate future design.

### Cloud Hypervisor — align PPTT with shared-L2 FDT policy

**State:** real-host-backed FDT/PPTT divergence reproduced; refreshed one-file PPTT-only candidate passes 19 fixtures, policy, quality/backend gates, and stable semantic patch identity.

- Internal Fieldwork issue: #542
- Branch: `teamleaderleo/cloud-hypervisor:linux-fieldwork/cache-sharing-pptt`
- Internal draft PR: `teamleaderleo/cloud-hypervisor#8`
- Exact canonical base: `a1fcb9f790616ac615f66de73be540b0b20844b1`
- Validated product carrier head: `32cde9c6849c9744e2945f6900c8e4035f7ccf03`
- Final run/job: `31385048099` / `93443487858` — success
- Final artifact: `9061406751`
- Final artifact digest: `sha256:aa71ae99ffd2426dc929c21f6522834765c0c92e0160456b159d3167748b79cb`
- Stored patch digest: `sha256:8729ff3d3c106768b536fbfb674f6cdbb0771d133c62e3d2c05de47012eed014`
- Regenerated full-index digest: `sha256:dced58b28add79c073c1c87901e3340d44337306c9e19a5966c8bc019689c9e7`
- Stable patch ID: `cb1de5b90d10f17f7157ba013bf8fa4d247388ac`

Historical Cloud Hypervisor review records an ARMv8 host with shared L2 and a migration-aware reason to avoid guessing a guest L2 sharing relationship. The candidate consumes `l2_cache_shared` in PPTT construction, leaves L1 untouched, and suppresses L2/L3 when host L2 is shared. This restores FDT/PPTT parity without changing cache discovery, error policy, identity recognition, or affinity.

The policy discriminator converges for shared-L2 and private-L3 cases. All 19 AArch64 cache fixtures pass twice; nightly rustfmt, AArch64 VMM Clippy, AArch64 KVM/MSHV, and x86_64 KVM VMM Clippy pass. Product scope remains `vmm/src/cpu.rs`, +8/-2.

**Current recommendation:** keep the PPTT-only correction. Per-vCPU heterogeneous cache domains and richer migration semantics belong outside this candidate.

### Cloud Hypervisor — select cache topology from eligible vCPU host CPUs

**State:** refreshed six-file v3 candidate and matching negative control pass on one final prerequisite lineage; exact v3 stored/generated bytes converge.

- Internal Fieldwork issue: #543
- Branch: `teamleaderleo/cloud-hypervisor:linux-fieldwork/cache-affinity-selection`
- Internal draft PR: `teamleaderleo/cloud-hypervisor#9`
- Exact canonical base: `a1fcb9f790616ac615f66de73be540b0b20844b1`
- Refreshed negative-control head: `d7d7ce4e686d1b8995c4acf6d1547d5f8fddfbf5`
- Baseline run/job: `31386883339` / `93449175645` — success
- Baseline artifact: `9062095139`
- Baseline artifact digest: `sha256:40c67563008483b72eee25e236283a0f466b4bb4173ebb65f1a3997f3d8d7140`
- Validated candidate head: `9775f648653ee495aa1a44aacaf64f656720eb13`
- Candidate run/job: `31386771082` / `93448827517` — success
- Candidate artifact: `9062114230`
- Candidate artifact digest: `sha256:77e47ee076b4ef3d65f83b34be0233a065feb4d491a61eec6aab1eca7aa305fc`
- v3 patch blob: `c1d99cfc6166efaa7871b0648e119c0a434a157f`
- Stored/generated v3 digest: `sha256:aec77fdcb31df5667bfbea0c688e00ea07a9750f5cdd1c9cdc9b1d67404939a0`
- Stable patch ID: `e802917e7fb7320d5d99b05ec1902666e18b73f5`

The negative control proves two valid eligible host CPU roots can expose different representable private-cache geometry. The candidate derives the eligible host CPU set from explicit CpuManager affinity plus inherited scheduler affinity for unpinned vCPUs, includes hotpluggable vCPUs through `max_vcpus`, supports dynamically sized affinity masks including high CPU IDs, and requires one common representable topology across the full eligible set.

FDT and PPTT receive the same selected topology. If eligible host CPUs disagree, the existing cache-less path is used. The shared-L2/private-L3 omission policy remains intact. AArch64 filesystem restrictions grant read-only `/sys/devices/system/cpu` access so dynamically selected `cpuN/cache` trees remain readable.

The v2 -> v3 refresh changed no production policy. Frozen v2 was three-way restacked over the final cache-identity implementation; only twelve calls in two new cache-root tests required helper-syntax adaptation because final #541 split identity and `size` writes. The mechanically refreshed result then passed the complete matrix and was frozen as v3.

Candidate validation passes exact six-file scope, selector/Landlock policy, nightly rustfmt, matching/differing root tests, four CpuManager affinity selectors including CPU ID 1300 and hotpluggable vCPUs, full AArch64 cache regression, AArch64 `arch` + `vmm` Clippy, AArch64 KVM/MSHV, x86_64 KVM VMM compile, and literal full-index stored/generated byte equality.

**Current recommendation:** treat v3 as the end of this cache-passthrough chain unless a supported-host counterexample appears or a deliberate richer per-vCPU guest cache-domain/migration design is chosen. Issue #544 is closed as a duplicate of #542.

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

No other active candidate currently outranks the strong-candidate review queue above. Further AArch64 cache work should require a concrete supported-host counterexample or a deliberate decision to build a richer guest cache model; the cache runtime-error, identity, sharing, and affinity chain is now revalidated on the submitted ACPI boundary.

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

`true — Cloud Hypervisor PRs #8699 and #8709 were submitted by the human contributor; #8709 has maintainer approval.`

No other canonical upstream pull requests, issue comments, reviews, reactions, emails, or other intentional interactions have been created from this workbench. Historical automatic cross-reference events were generated by direct canonical issue references in fork commits and internal GitHub interaction surfaces; current live records use redirect links and keep iterative internal commit messages free of canonical issue references to avoid creating additional backlinks.
