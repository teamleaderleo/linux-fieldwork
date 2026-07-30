# Name-brand actionable candidate scan — selection record

Date: 2026-07-31  
Programme: [`ecosystem-contributions`](../../../programmes/ecosystem-contributions/STATUS.md)  
Authority: internal Linux Fieldwork research only; no new upstream contact authorized

## TL;DR

This round refreshed the project rules, scanned current work and public upstream queues, stopped duplicates with active or merged fixes, and promoted five externally recognizable problems into bounded Linux Fieldwork investigations:

1. BuildKit rootless versus rootful image metadata parity — issue #229;
2. libarchive seek-dependent format bidding on non-seekable streams — issue #230;
3. util-linux fsck versus udev/libblkid block-device locking — issue #232;
4. BuildKit multi-platform symlink rewriting — issue #233;
5. util-linux `lscpu` stable-series double-free mapping/backport — issue #234.

The existing systemd-oomd reload-registration investigation #140 remains the strongest VM-gated target. The libarchive and `lscpu` items offer the quickest current-CI path to executable evidence. The util-linux/systemd boot race has the highest operational consequence and the widest ownership boundary.

## Explain like I'm five

A large issue tracker contains shiny problems, duplicates, stale reports, active fixes, and problems that need hardware we do not have. This scan asked whether each item has a small experiment, a real consequence, a likely source owner, a clean stop rule, and enough room to contribute without duplicating somebody else's work.

## Why care

A continuing programme needs both volume and judgment. Promoting every plausible report creates an unusable backlog. Waiting only for spectacular findings creates idle periods. The useful middle is a steady queue of bounded, consequential work, with serious candidates entering when the environment and evidence support them.

## Instruction refresh

Current guidance requires the reader-facing argument before the test matrix:

- state the current answer and next action;
- explain the component and failure in low-jargon terms;
- show who receives the consequence;
- separate observation, intent evidence, interpretation, design choice, and open work;
- map important claims to source, commands, fixtures, or results;
- review failure, interruption, cleanup, metadata compatibility, and rerun;
- retain one canonical issue and one canonical fix carrier;
- keep external contact unauthorized until a deliberate decision.

Each promotion below therefore records why leaving it alone matters, precedent, likely ownership directions, negative ramifications, first probe, promotion signal, and stop signal.

## Selection method

Higher-ranked candidates had a current open report without visible equivalent development work, a pinnable source boundary, a small distinguishing fixture, a consequential result, a likely source owner, and an environment available now or behind one named capability gate. Public state is perishable; recheck assignees, branches, pull requests, comments, and current source before implementation.

# Ranked promotions

## A1 — libarchive seek-dependent bidders claim non-seekable streams

Linux Fieldwork: #230  
Public report: https://github.com/libarchive/libarchive/issues/3068  
Environment: current CI

The report identifies a sharp parser-selection defect: a strong format bidder can win even when the selected reader later requires seeking and the transport cannot seek. That can turn an early capability decision into a late failure and can block raw fallback or another reader.

In-tree precedent matters: ZIP already has separate seekable-reader handling. The correct answer is not automatically “lower every bid”; the matrix must distinguish abstention, an earlier explicit error, and seek emulation.

**First probe:** build current libarchive, generate a tiny 7-Zip archive, and compare regular-file, stdin, gzip-filter, memory-callback, and explicitly non-seekable callback inputs. Record selected format, status, diagnostics, and raw fallback. Map readers that bid before a later seek.

**Negative ramifications:** a broad bidder change can weaken reliable detection or silently route recognized archives through raw mode. Limit the first candidate to one proved seek-dependent reader and preserve seekable controls.

**Disposition:** execute first.

## A2 — util-linux `lscpu` double-free correction and stable backport map

Linux Fieldwork: #234  
Public report: https://github.com/util-linux/util-linux/issues/4401  
Environment: current CI with sanitizers

The report supplies a synthetic input and a useful boundary: 2.40.4 and 2.41 abort, while 2.42 does not. That converts a rare container topology race into deterministic ownership and backport work.

This should begin as canonical-fix archaeology rather than a second implementation. Bisect the first passing commit, determine whether it actually fixes node-map ownership, and reduce only the needed change onto maintained branches.

**First probe:** hash the fixture; run affected, passing, and main versions under ASan/UBSan; record allocation and invalid-free stacks; bisect; test a reduced backport against ordinary text, parse, JSON, leaks, and repeated execution.

**Negative ramifications:** removing one free can trade an abort for a leak or stale alias. A topology refactor can alter script-visible output.

**Disposition:** execute early.

## A3 — BuildKit multi-platform local export rewrites absolute symlinks

Linux Fieldwork: #233  
Public report: https://github.com/moby/buildkit/issues/6684  
Environment: container-capable CI

The single-platform result is a natural compatibility control. Multi-platform export reportedly changes `/usr/bin/bash` into `/linux_amd64/usr/bin/bash`, suggesting a host destination prefix leaked into stored symlink metadata.

Filesystem-copy precedent separates the path where the link object is created from the bytes stored as its target. Destination containment and payload preservation are related but distinct decisions.

**First probe:** export absolute, relative, dangling, upward, and hard-link controls through single/multi-platform local, tar, and OCI outputs. Compare `readlink`, lstat metadata, tar/PAX headers, and hard-link identity, then locate the path-join owner.

**Negative ramifications:** a naive “never prefix links” change can preserve unsafe links or alter intentional exporter policy. Check extraction containment separately.

**Disposition:** execute after one BuildKit environment gate.

## A4 — BuildKit rootless worker changes reproducible image metadata

Linux Fieldwork: #229  
Public report: https://github.com/moby/buildkit/issues/6686  
Environment: rootful plus rootless BuildKit workers

BuildKit supports repeatable builds and rootless execution. A report that `/proc` and `/sys` stub directories differ between worker modes sits at the intersection of reproducibility, privilege reduction, OCI metadata, and cache identity.

The probe must compare complete image metadata, not only extracted bytes, and must preserve legitimate rootless ID mapping. The owner may be worker setup, snapshot/export normalization, or an explicitly versioned compatibility contract.

**First probe:** run one pinned Dockerfile through rootful and rootless workers; export OCI layouts; compare manifests, configs, layer order, type, mode, uid/gid, mtime, xattrs, and PAX headers, concentrating on `/proc` and `/sys`.

**Negative ramifications:** global normalization can erase user-requested ownership or hide meaningful worker differences. Control snapshotter, compression, frontend, architecture, and timestamps.

**Disposition:** capability-gated priority.

## A5 — systemd-oomd loses user-service registration after daemon reload

Linux Fieldwork: #140  
Public report: https://github.com/systemd/systemd/issues/43174  
Environment: cgroup-v2 VM with PSI and a lingering user

The service remains active and still advertises `ManagedOOMMemoryPressure=kill`, while its cgroup disappears from oomd after `systemctl --user daemon-reload`. That is a dangerous “configuration looks healthy, enforcement disappeared” lifecycle shape.

The existing investigation already names the Varlink publication paths and `TEST-55-OOMD.sh`. Decisive evidence is the timestamped remove/update sequence and its owner.

**First probe:** capture PID 1, user-manager, and oomd ManagedOOM traffic around reload; identify the exact remove/AUTO event and why no registration follows.

**Negative ramifications:** a repair can create stale registrations, duplicate ownership, or re-register a cgroup whose configuration genuinely changed. Test reload, stop, restart, logout, and reconnect.

**Disposition:** highest-value VM execution; keep #140 canonical.

## A6 — util-linux fsck and udev use mismatched block-device locks

Linux Fieldwork: #232  
Public report: https://github.com/util-linux/util-linux/issues/4477  
Environment: direct loop-device fixture, then VM/initramfs

The report connects two distinct lock objects to a rare boot failure: fsck updates an ext4 superblock while udev/libblkid reads identity; a missing UUID removes `/dev/disk/by-uuid`, stops the matching systemd fsck unit, and prevents the mount.

Systemd documents block-device-node locking; util-linux moved fsck locks under `/run/fsck` after earlier design discussion. The first task is to understand why both decisions exist and prove whether they fail to serialize the same device.

**First probe:** create an ext4 loop image, instrument both lock identities and superblock timing, pause fsck at the critical write, run the udev/blkid read, and add a shared-lock negative control before attempting boot loops.

**Negative ramifications:** changing lock identity or order can deadlock, over-serialize partitions, mishandle aliases/device mapper, or leave stale initramfs locks. Do not hide the race with a broad sleep.

**Disposition:** highest-consequence investigation; execute after A1/A2 and require strong independent review.

# Additional queue

## Nixpkgs AAVMF firmware regression

Retained source: `research/rounds/2026-07-30-ecosystem-candidate-scan/selection.md`  
Public report: https://github.com/NixOS/nixpkgs/issues/485220  
Environment: aarch64 QEMU

Pinned working and failing nixpkgs revisions plus a QEMU command already exist. Convert the console boundary into one automated pass/fail marker before bisecting package flags, edk2/AAVMF variants, or QEMU compatibility. Keep it behind the aarch64 gate.

## caching_proxy same-UID parent-swap race

Linux Fieldwork: #227  
Environment: current CI

Validation followed by pathname reuse may permit a same-UID process to redirect cache reads or publication outside a validated root. This can produce reusable descriptor-relative containment work across projects.

## make_mirror update-cache signal ownership

Linux Fieldwork: #231  
Environment: current CI

A concurrent workstream found that an `update_cache()` pipeline subshell can clean on INT/TERM, kill a parent-owned proxy, continue work, clean twice, and return success. Keep it separate from top-level PID registration so process and cleanup ownership stay explicit.

# Stops and references

## BuildKit OTLP shutdown stall

Public report: https://github.com/moby/buildkit/issues/6747  
Disposition: **stop duplicate implementation**

Focused upstream work through PR #6757 already owns the collector-unreachable shutdown delay. Retain it as precedent for bounded telemetry shutdown and non-blocking trace forwarding.

## BuildKit `COPY --chmod` directory mode regression

Public report: https://github.com/moby/buildkit/issues/6801  
Disposition: **stop duplicate implementation**

An equivalent correction already landed through PR #6828. Retain the lesson: mode tests must include implicitly created directories, not only copied files.

## libarchive RAR stored-symlink allocation report

Public report: https://github.com/libarchive/libarchive/issues/3023  
Disposition: **retain as a stop/interpretation record**

The report was closed as not security-impacting. The lesson is to separate sanitizer severity, attacker control, allocation size, and deployment consequence before labeling a parser issue.

## libarchive PPMd short-read accounting

Public issue: https://github.com/libarchive/libarchive/issues/3337  
Active fix: https://github.com/libarchive/libarchive/pull/3340  
Disposition: **watch adoption and downstream retirement**

Active equivalent work owns implementation. Retain the fixture as parser refill-accounting precedent.

# Portfolio recommendation

Use a two-speed queue:

1. **Continuous current-CI production:** libarchive bidder, `lscpu` fix map, local lifecycle/path races, and package-harvesting leaves.
2. **Serious capability-gated work:** systemd-oomd VM, fsck/udev boot race, BuildKit rootful/rootless parity, and AAVMF aarch64.

This keeps output flowing without pretending every target has equal consequence. Promotion expires when current upstream state changes.

# Immediate sequence

1. Execute #230's libarchive callback/pipe matrix.
2. Execute #234's sanitizer and bisect matrix.
3. Run #233's BuildKit exporter fixture when a pinned daemon/container is available.
4. Provision the cgroup-v2 VM for #140.
5. Build #232's direct loop-device fixture before boot loops.
6. Run #229's rootful/rootless OCI metadata comparison.
7. Preserve #231 and #227 as parallel work owned by their current workstreams.
8. Recheck external issue and development state before every branch.

# Evidence boundary

This round establishes current public issue state and internal actionability, not the underlying product defects. Public reports can be incomplete or wrong. No newly promoted upstream source was executed during this selection pass. Each first probe must independently establish baseline behavior on an exact revision before a candidate patch or upstream packet is justified.

No third-party issue, comment, review, pull request, email, or patch was created by this work.
