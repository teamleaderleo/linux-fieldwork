# Current Fieldwork

Updated: 2026-08-12

This is the compact routing board for the strongest current Linux Fieldwork work. Exact source maps, commands, artifacts, broad matrices, discarded variants, and evidence limits stay in the owning issues, pull requests, and `investigations/` records.

A rich investigation is not a maintainer-facing draft. Derive public-facing text separately around the concrete behavior, the target contract, the smallest repair or policy question, and the distinguishing tests.

## Landed upstream

### Cloud Hypervisor — shutdown lifecycle event gates

**State:** landed; complete.

- Fieldwork: `#423`
- Upstream issue: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8046
- Upstream PR: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8699
- Merge: `a658c9f9fd0c4e0363004361d73ac8733fa24fd0`

The landed tests wait for the VMM-owned `shutdown` event before later boot or delete/create work instead of treating SSH loss as shutdown completion.

### Cloud Hypervisor — ACPI construction failures

**State:** landed; complete.

- Fieldwork: `#444`
- Upstream issue: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8666
- Upstream PR: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8709
- Merge: `735d44f54e222475b2737ed9ca814f1769107cd9`

The final two-file repair propagates checked ACPI construction/delivery failures through `CreatingAcpiTables`. Review intentionally removed a broader mutex-poison policy that did not match the surrounding VMM architecture.

## Submitted / monitoring

### BuildKit — finalized rootless mount-stub cleanup

**State:** owner-submitted; monitoring.

- Fieldwork: `#229`
- Upstream issue: https://redirect.github.com/moby/buildkit/issues/6686
- Upstream PR: https://redirect.github.com/moby/buildkit/pull/7033
- Submitted head: `069b2d673b4cba9fb195e8229b93432947d79ace`

No owner submission decision remains.

## Ready for human design / contribution review

### Bubblewrap — `--unshare-pid` helper lifecycle

**State:** exact-current candidate and repository gates green; bounded lifecycle-policy decision remains.

- Fieldwork: `#553`
- Review PR: `#557`
- Bubblewrap source: `2f55bae38468d0c50cf5df87b1e481e882b63acb`
- Product run/job: `31490203503` / `93774626736` — success

Candidate rule: use the eventfd early-return path only while a real descendant remains; otherwise let namespace PID 1 finish so the outer monitor can reap it. Exit-status, signal, live-descendant, and normal controls pass.

### libarchive — cpio inode identity mapping

**State:** focused and normal CI green; compatibility-policy decision remains.

- Fieldwork: `#446`
- Candidate: `teamleaderleo/libarchive#8`
- Upstream issue: https://redirect.github.com/libarchive/libarchive/issues/3314

The candidate assigns deterministic archive-local inode identities while preserving hardlink identity. The maintainer decision is whether losing representable source inode numbers is an acceptable tradeoff for collision-free host-independent archive identity.

## Proven / package next

### runc — `sd_notify` READY field ordering

**State:** exact-current behavioral gate green; clean source packaging and complete-diff review next.

- Fieldwork: `#596`
- Carrier: `#597`
- runc source: `7495faeac77318158e6d5faece1b0b0d53e6ced4`
- Carrier head: `d3778a29f45cfdf4b86cf8bd4bf162edc9d1125a`
- Dedicated run: `31602920323` — success
- Linux Fieldwork CI: `31602920314` — success

`notifySocket.run()` splits a datagram into fields but checks `READY=` against the whole datagram. The product repair is one operand, `got` → `line`. Baseline READY-first/no-READY pass, baseline READY-second fails, and all three candidate cases plus root-package tests pass.

## Proven candidate / review next

### Bubblewrap — PID 1 procfs environment representation

**State:** exact-current runtime and repository gates green; source/design review required before technical acceptance.

- Fieldwork: `#565`
- Carrier: `#567`
- Bubblewrap source: `2f55bae38468d0c50cf5df87b1e481e882b63acb`
- Carrier head: `e6b32d35fbff382cecfb7c6db9107f92927b9ba7`
- Dedicated run: `31604150937` — success
- Linux Fieldwork CI: `31604150964` — success

The baseline proves `--clearenv`, `--unsetenv`, and `--setenv` can change the command environment while the non-exec'd PID-1 helper retains original exec-time bytes in `/proc/1/environ`. The candidate zeroes only superseded original environment storage. Next review must challenge that storage lifetime/ownership model and repeated set/unset portability before promotion.

## Strong candidates requiring current-source packaging renewal

### Cloud Hypervisor — AArch64 cache chain

Keep these as separate decisions and refresh each selected source against current Cloud Hypervisor before packaging:

- `#499` — typed errors for present-but-unusable cache metadata while missing metadata keeps fallback behavior;
- `#541` — identify cache leaves by exported `level` + `type`, not fixed sysfs indices;
- `#542` — keep PPTT consistent with the existing shared-L2 FDT omission policy;
- `#543` — require one representable topology across the full eligible host-CPU set.

### glibc loader-cache boundaries

**State:** executed candidates retained; current-source compatibility review next.

Current `gnutools/glibc` is `ae646973c5957b7eed06cb80d49d13b42178072d`, seven file-disjoint commits after the latest native cache source used here.

- `#502` / PR `#527` — byte-distinct SONAME identity within comparator-equivalent cache names;
- `#532` / PR `#534` — numeric comparator overflow with mixed-generation cache compatibility;
- `#503` / PR `#539` — continue through cached HWCAP candidates when the preferred cached file is stale.

Do not combine these solely because they share `ld.so.cache`; their contracts differ.

## Active repair / execution

### Cloud Hypervisor — KVM dirty-log granularity

**State:** defect/candidate well evidenced; pre-publish review found a memory-scaling regression; streaming repair staged.

- Fieldwork: `#617`
- Base: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
- Signed candidate: `2038c3cb262ac27604f647729557893a61510f99`
- Real 4K KVM migration: `31567234922` / `94021476274` — success

KVM needs host-page granularity while MSHV keeps fixed 4K semantics. Synthetic 4K/16K/64K conversion and real 4K migration are green; real non-4K KVM migration remains unavailable. Do not package the signed candidate as-is: pre-publish review found an extra full bitmap allocation. `STREAMING_REPAIR.patch` restores iterator-based merge/conversion while retaining tail validation; review and execute that delta first.

### Tini — startup lifecycle races

**State:** exact source current; reduced syscall discriminators strong; native Tini confirmation pending.

- Research PR: `#560`
- Tini source: `369448a167e8b3da4ca5bca0b3307500c3371828`

Keep two findings separate: process-group forwarding before PGID creation, and parent death before `PR_SET_PDEATHSIG` installation. Do not package either until an exact Tini binary gate confirms the reduced fixtures.

### systemd-nspawn — SIGHUP cleanup boundary

**State:** source/history only; runtime discriminator pending.

- Fieldwork: `#572`
- Research PR: `#574`

Run an exact SIGTERM/SIGHUP/explicit-cleanup differential before selecting a patch.

### mkosi — interruption and bind identity

**State:** source/history plus reduced evidence; full mkosi runtime pending.

- `#552` / PR `#554` — repeat interrupt delivery while a signal-resistant child remains in the secondary wait;
- `#561` — bind optimizer identity around `foreign` / `relative` semantics.

### Flatpak — p11-kit lifecycle

**State:** source/history plus existing public reproduction; supervised-child design unexecuted.

- Fieldwork: `#568`

Next evidence is an owned lifecycle/readiness/recovery fixture, not a maintainer packet.

### DuckDB / systemd-oomd scout

**State:** scoping/source-read only.

- Research PR: `#588`

Neither candidate has product execution yet.

## Parked / negative results

- Cloud Hypervisor PPTT descriptor reuse: retired after table semantics explained the apparent duplication.
- mkosi ToolsTree `depmod`: retired after current `chroot_cmd()` PATH behavior explained the report.
- bootc #1805: current source already validates fs-verity capability before destructive mutation.
- bootc #1896: upstream already landed the file-backed `rpm2cpio` workaround.
- bootc #2318: belongs to broader Docker v2s2/composefs support rather than a narrow bootc-owned repair.

## Communication / evidence rule

Internal records should remain detailed enough to defend source identity, privilege/platform boundaries, failure ownership, cleanup, rerun, and compatibility. Maintainer-facing text should normally carry only the concrete behavior, target contract, smallest repair or policy question, discriminating test, and one useful non-goal.

Green CI proves execution, not target-contract acceptance. A rich investigation is not a giant public draft.

## External-contact state

Existing human-performed upstream interactions recorded here are the two landed Cloud Hypervisor contributions and the submitted BuildKit contribution. No additional canonical upstream issue, pull request, comment, review, reaction, email, patch submission, merge, release, or deployment is authorized or performed by this board refresh.
