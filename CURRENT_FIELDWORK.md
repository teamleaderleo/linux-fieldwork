# Current Fieldwork

Updated: 2026-08-12

This is the compact routing board for the strongest current Linux Fieldwork work. Detailed source maps, commands, receipts, artifacts, discarded variants, and evidence limits stay in the owning issues, pull requests, and `investigations/` records.

A rich investigation is not a maintainer-facing draft. For contribution preparation, derive a decision-sized issue or pull-request packet from the evidence instead of copying this board or the investigation transcript. See `MAINTAINER_COMMUNICATION.md` once its review lands.

## Landed upstream

### Cloud Hypervisor — API shutdown lifecycle event gates

**State:** landed upstream; complete.

- Fieldwork issue: `teamleaderleo/linux-fieldwork#423`
- Upstream issue: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8046
- Upstream PR: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8699
- Upstream merge: `a658c9f9fd0c4e0363004361d73ac8733fa24fd0`

The landed test change waits for the VMM-owned `shutdown` event before a later boot or delete/create transition instead of treating SSH loss as shutdown completion. All four retained HTTP/D-Bus KVM selectors passed before submission.

### Cloud Hypervisor — propagate ACPI construction failures

**State:** landed upstream; complete.

- Fieldwork issue: `teamleaderleo/linux-fieldwork#444`
- Upstream issue: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8666
- Upstream PR: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8709
- Upstream merge: `735d44f54e222475b2737ed9ca814f1769107cd9`

The landed two-file repair propagates checked ACPI construction and delivery failures through `CreatingAcpiTables`. Review deliberately removed the broader mutex-poison policy so the final contribution matched Cloud Hypervisor's existing error architecture.

## Submitted / monitoring

### BuildKit — finalized rootless mount-stub cleanup

**State:** owner-submitted upstream; monitoring.

- Fieldwork issue: `teamleaderleo/linux-fieldwork#229`
- Upstream issue: https://redirect.github.com/moby/buildkit/issues/6686
- Upstream PR: https://redirect.github.com/moby/buildkit/pull/7033
- Submitted head: `069b2d673b4cba9fb195e8229b93432947d79ace`

The contribution registers mount-stub cleanup after rootless conversion finalizes the mount list, restoring the retained rootful/rootless runc/native parity case. No owner submission decision remains on this board.

## Ready for human design or contribution review

### Bubblewrap — `--unshare-pid` helper lifecycle

**State:** exact-current candidate and product gates green; bounded lifetime-policy decision remains.

- Fieldwork issue: `teamleaderleo/linux-fieldwork#553`
- Internal review PR: `teamleaderleo/linux-fieldwork#557`
- Exact Bubblewrap source: `2f55bae38468d0c50cf5df87b1e481e882b63acb`
- Authoritative product run/job: `31490203503` / `93774626736` — success

Current Bubblewrap can let the outer monitor return through the eventfd path before it reaps namespace PID 1. The candidate uses that early-return path only while a real descendant remains; otherwise PID 1 exits normally and the outer monitor reaps it. Exit `42`, SIGTERM→`143`, the background-child behavior, and the retained Bubblewrap suites all pass.

**Maintainer packet shape:** eventfd ownership race → live-descendant discriminator → narrow drain-before-notify behavior → regression. Keep the privileged-container receipts internal unless requested.

### libarchive — deterministic cpio inode identity mapping

**State:** focused tests, normal multi-platform CI, and lint green; compatibility-policy decision remains.

- Fieldwork issue: `teamleaderleo/linux-fieldwork#446`
- Candidate PR: `teamleaderleo/libarchive#8`
- Upstream issue: https://redirect.github.com/libarchive/libarchive/issues/3314

The candidate gives nonzero newc entries deterministic archive-local inode identities while preserving hardlink identity by device/inode tuple. The remaining question is whether losing representable source inode numbers is an acceptable compatibility tradeoff for collision-free host-independent archive identity.

**Maintainer packet shape:** demonstrate the low-32-bit collision, state the archive-identity tradeoff explicitly, show distinct/hardlink/device controls, and ask the compatibility question directly.

## Strong candidates requiring current-source packaging renewal

### Cloud Hypervisor — AArch64 cache chain

The retained cache work remains technically strong but should not be presented as one giant contribution. Refresh each selected source against current Cloud Hypervisor before packaging.

- `#499` — present-but-unusable cache metadata becomes a typed error while missing metadata retains fallback behavior.
- `#541` — identify cache leaves by exported `level` + `type` instead of assuming fixed sysfs indices.
- `#542` — keep PPTT consistent with the existing shared-L2 FDT omission policy.
- `#543` — derive one representable cache topology from the full eligible host-CPU set and fall back to cache-less output when eligible CPUs disagree.

Each has retained target-native execution and a bounded owner. Treat them as separate maintainer decisions; the landed ACPI prerequisite is now history, not a pending dependency.

### glibc loader-cache boundaries

**State:** executed candidate evidence retained; current-source review/compatibility renewal required before a maintainer packet.

Current `gnutools/glibc` is `ae646973c5957b7eed06cb80d49d13b42178072d`, seven commits after the source used by the latest native cache work. Those intervening commits are file-disjoint from the loader-cache owning paths, so the evidence is not discarded, but current-source review still precedes promotion.

- `#502` / PR `#527` — comparator-equivalent, byte-distinct SONAME identity; preserve cache ordering while making exact requested-name eligibility explicit.
- `#532` / PR `#534` — numeric comparator overflow; preserve legacy ordering and mixed-generation cache compatibility without fixed-width signed accumulation.
- `#503` / PR `#539` — stale selected HWCAP entry; continue through appropriate cached candidates before abandoning cache semantics, while preserving priority and ordinary-search fallback.

Do not combine these just because they share `ld.so.cache`; they have different contracts and compatibility questions.

## Active execution / repair

### runc — `sd_notify` READY field ordering

**State:** exact-current source confirmed; execution carrier repaired; renewed gate running.

- Fieldwork issue: `teamleaderleo/linux-fieldwork#596`
- Carrier PR: `teamleaderleo/linux-fieldwork#597`
- Exact runc source: `7495faeac77318158e6d5faece1b0b0d53e6ced4`
- Repaired carrier head: `d3778a29f45cfdf4b86cf8bd4bf162edc9d1125a`
- Renewed dedicated run: `31602920323` — queued at this board refresh

`notifySocket.run()` splits one datagram into fields but checks `READY=` against the complete datagram. The intended product change is one predicate operand, `got` → `line`. The first exact-current carrier failed before behavior because the stored patch had invalid context; that materialization defect is repaired. Do not call the product candidate green until READY-first, READY-second, no-READY, and package controls execute on the repaired head.

### Bubblewrap — PID 1 procfs environment representation

**State:** exact-current baseline behavior proven; candidate materialization repaired; renewed candidate gate running.

- Fieldwork issue: `teamleaderleo/linux-fieldwork#565`
- Carrier PR: `teamleaderleo/linux-fieldwork#567`
- Exact Bubblewrap source: `2f55bae38468d0c50cf5df87b1e481e882b63acb`
- Repaired carrier head: `b051dfd48af06a8c3dbaa7ebc65f1b99d1f2001f`
- Renewed dedicated run: `31602951324` — queued at this board refresh

The baseline shows that `--clearenv`, `--unsetenv`, and `--setenv` change the eventual command environment while the non-exec'd PID-1 helper can retain the original exec-time bytes in `/proc/1/environ`. The first candidate run never compiled because the retained patch was syntactically corrupt; that carrier defect is repaired. The candidate remains experimental until command semantics, procfs semantics, unrelated-variable controls, and `--as-pid-1` all execute successfully.

### Tini — startup lifecycle races

**State:** exact upstream source current; reduced Linux syscall discriminators strong; Tini-native confirmation pending.

- Research PR: `teamleaderleo/linux-fieldwork#560`
- Exact Tini source: `369448a167e8b3da4ca5bca0b3307500c3371828`

Keep the two findings separate:

1. process-group forwarding can target `-child_pid` before the child process group exists;
2. a direct parent can exit before `PR_SET_PDEATHSIG` is installed.

Reduced fixtures strongly distinguish both orderings, but no exact Tini binary gate has run yet. Do not package either as upstream-ready until the native source path confirms it.

### systemd-nspawn — SIGHUP cleanup boundary

**State:** source/history evidence only; exact-current runtime discriminator pending.

- Fieldwork issue: `teamleaderleo/linux-fieldwork#572`
- Research PR: `teamleaderleo/linux-fieldwork#574`

Current source handles SIGINT/SIGTERM through the nspawn event loop while SIGHUP remains outside that path; normal unix-export cleanup lives on `finish:`. Run the exact SIGTERM/SIGHUP/explicit-cleanup differential before choosing a product patch.

### mkosi — interruption and bind-identity work

**State:** source/history plus reduced executable evidence; full mkosi runtime still pending.

- `#552` / PR `#554` — repeated interrupts can be suppressed by the process-global one-shot latch while a signal-resistant child keeps the parent in its secondary wait.
- `#561` — bind optimizer identity omits `foreign` / `relative` semantic distinctions in places where later `nofollow` history shows the intended pattern.

Keep the execution-policy questions separate and require real disposable mkosi fixtures before source promotion.

### Flatpak — p11-kit auxiliary-process lifecycle

**State:** exact source/history plus existing public reproduction; supervised-child design only.

- Fieldwork issue: `teamleaderleo/linux-fieldwork#568`

Current source can retain a detached p11-kit PID/socket identity after the daemon exits. A foreground supervised-child design fits existing Flatpak/p11-kit capabilities, but Fieldwork has not compiled or executed it. Next evidence is an owned lifecycle/readiness/recovery fixture, not a maintainer packet.

### DuckDB / systemd-oomd high-leverage scout

**State:** scoping/source-read only.

- Research PR: `teamleaderleo/linux-fieldwork#588`

DuckDB's reserved Hive null-token serialization and oomd reporter-identity collision remain bounded investigation candidates. Neither has candidate execution yet.

## Parked or negative results

- Cloud Hypervisor PPTT descriptor reuse: retired after ACPI PPTT review showed identical private resources may share a resource structure for table compaction.
- mkosi ToolsTree `depmod`: retired after current `chroot_cmd()` PATH behavior explained the original report without the retained patch.
- bootc #1805: current source already validates fs-verity capability before destructive mutation.
- bootc #1896: upstream work already landed the file-backed `rpm2cpio` workaround.
- bootc #2318: belongs to broader Docker v2s2/composefs support, not a narrow bootc-owned repair.

## Communication and evidence rule

Internal Linux Fieldwork records should remain detailed enough to defend exact source identity, privilege/platform boundaries, failure ownership, cleanup, rerun, and compatibility. Maintainer-facing text should normally carry only the concrete behavior, target contract, smallest repair or contract question, discriminating test, and one useful non-goal.

Do not turn green CI into target-contract acceptance. Do not turn a rich investigation into a giant public draft. Do not hide a real compatibility or policy question behind implementation language.

## External-contact state

Existing human-performed upstream interactions recorded here are the two landed Cloud Hypervisor contributions and the submitted BuildKit contribution. No additional canonical upstream issue, pull request, comment, review, reaction, email, patch submission, merge, release, or deployment is authorized or performed by this board refresh.
