# Name-brand actionable candidate scan — selection record

Date: 2026-07-31  
Programme: [`ecosystem-contributions`](../../../programmes/ecosystem-contributions/STATUS.md)  
Authority: internal Linux Fieldwork research only; no new upstream contact authorized

## TL;DR

This round refreshed the project rules, scanned current work and public upstream queues, stopped duplicates with active or merged fixes, and promoted four externally recognizable problems into bounded Linux Fieldwork investigations:

1. BuildKit rootless versus rootful image metadata parity — issue #229;
2. libarchive seek-dependent format bidding on non-seekable streams — issue #230;
3. util-linux fsck versus udev/libblkid block-device locking — issue #232;
4. BuildKit multi-platform symlink rewriting — issue #233;
5. util-linux `lscpu` stable-series double-free mapping/backport — issue #234.

The existing systemd-oomd reload-registration investigation #140 remains the strongest VM-gated target. The new libarchive and `lscpu` items offer the quickest current-CI path to executable evidence. The util-linux/systemd boot race has the highest operational consequence but also the widest ownership and compatibility boundary.

## Explain like I'm five

A large issue tracker contains shiny problems, duplicates, stale reports, active fixes, and problems that need hardware we do not have. This scan did not simply collect impressive names. It asked whether each item has a small experiment, a real consequence, a likely source owner, a clean stop rule, and enough room to contribute without duplicating somebody else's work.

## Why care

A continuing research programme needs both volume and judgment. Promoting every plausible report creates an unusable backlog. Waiting only for spectacular security findings creates long idle periods. The useful middle is a steady queue of bounded, consequential work across major projects, with serious candidates entering when the environment and evidence support them.

## Instruction refresh

The current repository guidance now makes the reader-facing argument part of the evidence contract:

- state the current answer and next action near the top;
- explain the component and failure in low-jargon terms;
- show who receives the consequence;
- separate observed behavior, historical intent, interpretation, design choice, and open work;
- map important prose claims to source, commands, fixtures, or results;
- review failure, interruption, cleanup, compatibility metadata, and rerun;
- prefer one canonical issue and one canonical fix carrier;
- keep external contact explicitly unauthorized until a deliberate decision.

This round therefore records not only “interesting issue” but also why leaving it alone matters, likely precedent, viable ownership directions, negative ramifications, first probe, promotion signal, and stop signal.

## Selection method

The scan covered current public state in BuildKit, libarchive, util-linux, systemd, Nixpkgs, and adjacent retained queues. A candidate received higher priority when it had:

- a current open report with no visible equivalent development work;
- a pinned or easily pinned source boundary;
- a small distinguishing fixture;
- a result that affects artifact identity, boot, lifecycle, parser selection, memory ownership, or reproducibility;
- an environment available in current CI, rootless containers, or a clearly named VM gate;
- a likely source owner and at least two plausible outcomes;
- a bounded correction whose compatibility risks can be enumerated;
- a clean duplicate, stop, or reroute rule.

Public issue state is perishable. Recheck assignees, linked branches, pull requests, comments, and current source immediately before implementation.

# Ranked promotions

## A1 — libarchive seek-dependent bidders claim non-seekable streams

Linux Fieldwork: #230  
Public report: https://github.com/libarchive/libarchive/issues/3068  
Environment: current CI

### Why this is attractive

The report already identifies the shape of the defect: a strong format bidder can win automatic detection even when the chosen reader later requires seeking and the transport cannot seek. The result crosses parser selection, stream capability, fallback policy, and diagnostic timing. A tiny 7-Zip/gzip/pipe fixture can distinguish the old behavior from a candidate.

### Why not leave it alone

Late failure is harder to interpret than capability-aware selection. It may also block raw fallback or another reader that could handle the stream. Because libarchive is a shared library behind many archive tools, the behavior reaches more than one command-line client.

### Historical and implementation precedent

The report points to ZIP's separate seekable-reader registration as an in-tree design pattern. The correct result is not automatically “lower every bid”: the experiment must decide whether abstention, an earlier explicit error, or seek emulation matches libarchive's selection contract.

### First action

Build current libarchive, generate a tiny valid 7-Zip archive, and compare regular-file, stdin, gzip-filter, memory-callback, and explicitly non-seekable callback inputs. Record bid/selection, status, diagnostic, and raw fallback. Map every reader that bids before a later seek.

### Main downside risk

A broad bidder change can weaken reliable format detection or silently route recognized archives through raw mode. Keep the first candidate limited to one proved seek-dependent reader and preserve seekable controls.

### Disposition

**Execute first.** It combines a name-brand library with a current-CI fixture and a bounded compatibility question.

## A2 — util-linux `lscpu` double-free correction and stable backport map

Linux Fieldwork: #234  
Public report: https://github.com/util-linux/util-linux/issues/4401  
Environment: current CI with sanitizers

### Why this is attractive

The report supplies a synthetic input and a useful version boundary: 2.40.4 and 2.41 abort, while 2.42 does not. That converts a rare container topology race into a deterministic ownership and backport investigation.

### Why not leave it alone

`lscpu` is routinely called by installers, CI, support scripts, and inventory systems. Inconsistent topology input should produce a controlled result, not heap corruption. Stable distributions may remain on the affected branches even when current main is safe.

### Historical precedent and direction

This should begin as canonical-fix archaeology rather than a new implementation. Bisect the first passing commit, determine whether it truly repairs node-map ownership, and reduce only the needed change onto maintained 2.40/2.41 code.

### First action

Hash the supplied fixture; run affected, passing, and main versions under ASan/UBSan; record allocation and both frees; bisect; then test a reduced backport against ordinary text, parse, JSON, and repeated execution.

### Main downside risk

Removing one free can trade an abort for a leak or stale alias. A larger topology refactor can change script-visible output. Review ownership and output compatibility, not only process survival.

### Disposition

**Execute early.** This is the lowest-cost route to a real stable-series contribution packet or a precise retirement map.

## A3 — BuildKit multi-platform local export rewrites absolute symlinks

Linux Fieldwork: #233  
Public report: https://github.com/moby/buildkit/issues/6684  
Environment: container-capable CI

### Why this is attractive

The single-platform result supplies a natural compatibility control. Multi-platform export reportedly changes `/usr/bin/bash` into `/linux_amd64/usr/bin/bash`, suggesting a host destination prefix has leaked into stored symlink metadata.

### Why not leave it alone

Symlink target text is part of a filesystem artifact. A build can succeed and export a plausible tree whose links fail only when used. The same source producing different rootfs semantics solely because a second platform was requested is a strong artifact-integrity defect.

### Historical precedent and direction

Copy and archive systems generally separate the path where a link object is created from the bytes stored as its target. Destination containment and link-payload preservation must remain separate questions.

### First action

Export one absolute, relative, dangling, upward, and hard-link control through single/multi-platform local, tar, and OCI outputs. Compare `readlink`, lstat metadata, tar/PAX headers, and hard-link identity, then locate the path-join owner.

### Main downside risk

An apparently simple “do not prefix links” change can preserve unsafe links or alter intentional compatibility behavior. Check exporter policy and extraction containment separately.

### Disposition

**Execute after one BuildKit environment gate.** High signal, likely small owner, broad relevance.

## A4 — BuildKit rootless worker changes reproducible image metadata

Linux Fieldwork: #229  
Public report: https://github.com/moby/buildkit/issues/6686  
Environment: rootful plus rootless BuildKit workers

### Why this is attractive

BuildKit explicitly supports repeatable builds and rootless execution. A report that `/proc` and `/sys` stub directories differ between rootful and rootless workers sits directly at the intersection of reproducibility, privilege reduction, OCI metadata, and cache identity.

### Why not leave it alone

Mode-dependent layer metadata can change image digests, defeat cache sharing, complicate provenance comparison, and make privilege reduction alter artifact identity even when the requested filesystem content is the same.

### Historical precedent and direction

The first probe must compare complete image metadata—not only extracted bytes—and must preserve legitimate rootless ID mapping. The open question is whether parity belongs in worker setup, snapshot/export normalization, or an explicitly versioned compatibility contract.

### First action

Run the same minimal Dockerfile through pinned rootful and rootless workers; export OCI layouts; compare manifests, configs, layer member order, mode, uid/gid, mtime, xattrs, and PAX headers, concentrating first on `/proc` and `/sys`.

### Main downside risk

Global normalization can erase user-requested ownership or hide meaningful worker differences. Keep variables such as snapshotter, compression, frontend, architecture, and timestamps controlled.

### Disposition

**Capability-gated priority.** More infrastructure than A1/A2, but a strong name-brand result if reproduced.

## A5 — systemd-oomd loses user-service registration after daemon reload

Linux Fieldwork: #140  
Public report: https://github.com/systemd/systemd/issues/43174  
Environment: cgroup-v2 VM with PSI and a lingering user

### Why this remains the strongest VM item

The service remains active and still advertises `ManagedOOMMemoryPressure=kill`, while the monitored cgroup disappears from oomd after `systemctl --user daemon-reload`. That is a dangerous “configuration looks healthy, enforcement disappeared” lifecycle shape.

### Why not leave it alone

User-manager reload is ordinary administrative behavior. Losing memory-pressure protection until oomd restarts can turn a declared resource policy into silent non-enforcement.

### Historical precedent and direction

The investigation already names the Varlink publication paths and `TEST-55-OOMD.sh`. The decisive evidence is the timestamped remove/update sequence and owner—not another static reading of the issue.

### First action

Provision the VM, capture PID 1, user-manager, and oomd ManagedOOM traffic around reload, identify the exact remove/AUTO event, and determine why no registration follows.

### Main downside risk

A repair can create stale registrations, duplicate ownership, or re-register a cgroup whose unit configuration genuinely changed. Test reload, stop, restart, logout, and manager reconnect.

### Disposition

**Highest-value VM execution.** Existing issue remains canonical; no duplicate was created.

## A6 — util-linux fsck and udev use mismatched block-device locks

Linux Fieldwork: #232  
Public report: https://github.com/util-linux/util-linux/issues/4477  
Environment: direct loop-device fixture, then VM/initramfs

### Why this is the juiciest high-consequence item

The report connects two distinct lock objects to a rare boot failure: fsck updates an ext4 superblock while udev/libblkid reads identity; a missing UUID removes `/dev/disk/by-uuid`, stops the corresponding systemd fsck unit, and prevents the mount.

### Why not leave it alone

A one-in-a-thousand boot failure is still serious when it suppresses a required filesystem mount. The apparent contract spans util-linux, libblkid, udev, systemd, initramfs state, and filesystem metadata.

### Historical precedent and direction

Systemd documents block-device-node locking; util-linux moved fsck locking to `/run/fsck` after earlier design discussion. The first task is to understand why both decisions exist and prove whether they now fail to serialize the same device.

### First action

Create an ext4 loop image, instrument both lock identities and superblock read/write timing, pause fsck at the critical write, run the udev/blkid read, and add a shared-lock negative control before attempting repeated boots.

### Main downside risk

Changing lock identity or order can deadlock, over-serialize independent partitions, mishandle aliases/device mapper, or leave stale initramfs locks. A sleep or unconditional retry would hide rather than own the race.

### Disposition

**Serious investigation, execute after A1/A2.** Highest blast radius and likely strongest need for independent review.

# Additional queue

## Nixpkgs AAVMF firmware regression

Retained source: `research/rounds/2026-07-30-ecosystem-candidate-scan/selection.md`  
Public report: https://github.com/NixOS/nixpkgs/issues/485220  
Environment: aarch64 QEMU

The report retains pinned working and failing nixpkgs revisions plus a QEMU console command. The next useful work remains converting the console boundary into one automated pass/fail marker before bisecting Nixpkgs flags, edk2/AAVMF variants, or QEMU compatibility. This stays behind the aarch64 capability gate.

## caching_proxy same-UID parent-swap race

Linux Fieldwork: #227  
Environment: current CI

This internally discovered race is less famous than BuildKit or systemd, but it has a sharp consequence: validation followed by pathname reuse may permit a same-UID process to redirect cache reads or publication outside a validated root. Keep it active because it can produce descriptor-relative path-handling knowledge reusable across many projects.

## make_mirror update-cache signal ownership

Linux Fieldwork: #231  
Environment: current CI

A concurrent workstream found that an `update_cache()` pipeline subshell can run cleanup on INT/TERM, kill a proxy owned by its parent, continue work, clean twice, and return success. This is locally actionable and composes with the existing top-level PID-registration work, but it should remain separate so one process owner does not silently absorb another owner's cleanup policy.

# Stops and references

## BuildKit OTLP shutdown stall

Public report: https://github.com/moby/buildkit/issues/6747  
Disposition: **stop duplicate implementation**

The collector-unreachable shutdown delay already received focused upstream work through BuildKit PR #6757. Retain it as precedent for bounded telemetry shutdown and non-blocking trace forwarding, not a new branch target.

## BuildKit `COPY --chmod` directory mode regression

Public report: https://github.com/moby/buildkit/issues/6801  
Disposition: **stop duplicate implementation**

The report already has an equivalent merged correction through PR #6828. The useful lesson is to include implicitly created directories, not only copied files, in mode-preservation tests.

## libarchive RAR stored-symlink allocation report

Public report: https://github.com/libarchive/libarchive/issues/3023  
Disposition: **retain as a stop/interpretation record**

The report was closed as not security-impacting rather than promoted into a parallel fix. Its useful lesson is that sanitizer severity, attacker control, allocation size, and reachable deployment consequence must be separated before labeling a parser issue.

## libarchive PPMd short-read accounting

Retained source: prior ecosystem scan  
Public issue: https://github.com/libarchive/libarchive/issues/3337  
Active fix reference: https://github.com/libarchive/libarchive/pull/3340  
Disposition: **watch adoption and downstream retirement**

This remains a strong parser refill-accounting reference, but active equivalent work owns implementation.

# Portfolio recommendation

Use a two-speed queue:

1. **Continuous current-CI production:** libarchive bidder, `lscpu` backport map, local lifecycle and path races, package-harvesting leaves.
2. **Serious capability-gated work:** systemd-oomd VM, fsck/udev boot race, BuildKit rootful/rootless parity, AAVMF aarch64.

This keeps output flowing without pretending every target has equal consequence. One or two current-CI investigations can proceed while a VM or container environment is being prepared. Promotion still expires when current upstream state changes.

# Immediate sequence

1. Execute #230's libarchive callback/pipe matrix.
2. Execute #234's sanitizer and bisect matrix.
3. Run #233's BuildKit exporter fixture when a pinned daemon/container environment is available.
4. Provision the cgroup-v2 VM for #140.
5. Build #232's direct loop-device synchronization fixture before attempting boot loops.
6. Run #229's rootful/rootless OCI metadata comparison.
7. Preserve #231/#227 as parallel current-CI work owned by their existing workstreams.
8. Recheck every external issue and linked-development state immediately before branch creation.

# Evidence boundary

This round establishes current public issue state and internal actionability, not the underlying product defects. Public reports can be incomplete or wrong. No imported source was executed for the newly promoted items during this selection pass. Each issue's first probe must independently establish baseline behavior on an exact revision before a candidate patch or upstream packet is justified.

No third-party issue, comment, review, pull request, email, or patch was created by this work.