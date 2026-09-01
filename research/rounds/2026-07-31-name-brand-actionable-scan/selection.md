# Name-brand actionable candidate scan — selection record

Date: 2026-07-31  
Programme: [`ecosystem-contributions`](../../../programmes/ecosystem-contributions/STATUS.md)  
Authority: internal Linux Fieldwork research only; no new upstream contact authorized

## TL;DR

This round refreshed the project rules, scanned current work and public upstream queues, stopped duplicates with active or merged fixes, and opened five bounded Linux Fieldwork units:

1. BuildKit rootless versus rootful image metadata parity — issue #229;
2. libarchive non-seekable 7-Zip overlap review — issue #230;
3. util-linux fsck versus udev/libblkid block-device locking — issue #232;
4. BuildKit multi-platform symlink rewriting — issue #233;
5. util-linux `lscpu` stable-series double-free mapping/backport — issue #234.

A post-branch overlap refresh corrected the libarchive classification: open upstream PR 3070 already owns the seekability-aware bidder and pipe/raw test, while merged PR 3074 restored forward-only stream reading. Issue #230 is therefore an overlap/evidence review, not an implementation target.

The existing systemd-oomd reload-registration investigation #140 remains the strongest VM-gated target. The `lscpu` item offers the quickest current-CI path to executable contribution evidence. The util-linux/systemd boot race has the highest operational consequence and the widest ownership boundary.

## Explain like I'm five

A large issue tracker contains shiny problems, duplicates, stale reports, active fixes, and problems that need hardware we do not have. This scan asked whether each item has a small experiment, a real consequence, a likely source owner, a clean stop rule, and enough room to contribute without duplicating somebody else's work.

The live-overlap correction is part of the result. Finding that somebody already owns a credible fix is a successful stop, not lost work.

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

Each unit below therefore records why leaving it alone matters, precedent, likely ownership directions, negative ramifications, first probe, promotion signal, and stop signal.

## Selection method

Higher-ranked candidates had a current open report, a pinnable source boundary, a small distinguishing fixture, a consequential result, a likely source owner, and an environment available now or behind one named capability gate.

Public state is perishable. Recheck assignees, branches, pull requests, comments, and current source before implementation. The missed libarchive PR demonstrates why this check must happen immediately before branch creation, not only during the broad scan.

# Ranked units

## A1 — util-linux `lscpu` double-free correction and stable backport map

Linux Fieldwork: #234  
Public report: https://github.com/util-linux/util-linux/issues/4401  
Environment: current CI with sanitizers

The report supplies a synthetic input and a useful boundary: 2.40.4 and 2.41 abort, while 2.42 does not. That converts a rare container topology race into deterministic ownership and backport work.

This should begin as canonical-fix archaeology rather than a second implementation. Bisect the first passing commit, determine whether it actually fixes node-map ownership, and reduce only the needed change onto maintained branches.

**First probe:** hash the fixture; run affected, passing, and main versions under ASan/UBSan; record allocation and invalid-free stacks; bisect; test a reduced backport against ordinary text, parse, JSON, leaks, and repeated execution.

**Negative ramifications:** removing one free can trade an abort for a leak or stale alias. A topology refactor can alter script-visible output.

**Disposition:** execute first.

## A2 — BuildKit multi-platform local export rewrites absolute symlinks

Linux Fieldwork: #233  
Public report: https://github.com/moby/buildkit/issues/6684  
Environment: container-capable CI

The single-platform result is a natural compatibility control. Multi-platform export reportedly changes `/usr/bin/bash` into `/linux_amd64/usr/bin/bash`, suggesting a host destination prefix leaked into stored symlink metadata.

Filesystem-copy precedent separates the path where the link object is created from the bytes stored as its target. Destination containment and payload preservation are related but distinct decisions.

**First probe:** export absolute, relative, dangling, upward, and hard-link controls through single/multi-platform local, tar, and OCI outputs. Compare `readlink`, lstat metadata, tar/PAX headers, and hard-link identity, then locate the path-join owner.

**Negative ramifications:** a naive “never prefix links” change can preserve unsafe links or alter intentional exporter policy. Check extraction containment separately.

**Disposition:** execute after one BuildKit environment gate.

## A3 — BuildKit rootless worker changes reproducible image metadata

Linux Fieldwork: #229  
Public report: https://github.com/moby/buildkit/issues/6686  
Environment: rootful plus rootless BuildKit workers

BuildKit supports repeatable builds and rootless execution. A report that `/proc` and `/sys` stub directories differ between worker modes sits at the intersection of reproducibility, privilege reduction, OCI metadata, and cache identity.

The probe must compare complete image metadata, not only extracted bytes, and must preserve legitimate rootless ID mapping. The owner may be worker setup, snapshot/export normalization, or an explicitly versioned compatibility contract.

**First probe:** run one pinned Dockerfile through rootful and rootless workers; export OCI layouts; compare manifests, configs, layer order, type, mode, uid/gid, mtime, xattrs, and PAX headers, concentrating on `/proc` and `/sys`.

**Negative ramifications:** global normalization can erase user-requested ownership or hide meaningful worker differences. Control snapshotter, compression, frontend, architecture, and timestamps.

**Disposition:** capability-gated priority.

## A4 — systemd-oomd loses user-service registration after daemon reload

Linux Fieldwork: #140  
Public report: https://github.com/systemd/systemd/issues/43174  
Environment: cgroup-v2 VM with PSI and a lingering user

The service remains active and still advertises `ManagedOOMMemoryPressure=kill`, while its cgroup disappears from oomd after `systemctl --user daemon-reload`. That is a dangerous “configuration looks healthy, enforcement disappeared” lifecycle shape.

The existing investigation already names the Varlink publication paths and `TEST-55-OOMD.sh`. Decisive evidence is the timestamped remove/update sequence and its owner.

**First probe:** capture PID 1, user-manager, and oomd ManagedOOM traffic around reload; identify the exact remove/AUTO event and why no registration follows.

**Negative ramifications:** a repair can create stale registrations, duplicate ownership, or re-register a cgroup whose configuration genuinely changed. Test reload, stop, restart, logout, and reconnect.

**Disposition:** highest-value VM execution; keep #140 canonical.

## A5 — util-linux fsck and udev use mismatched block-device locks

Linux Fieldwork: #232  
Public report: https://github.com/util-linux/util-linux/issues/4477  
Environment: direct loop-device fixture, then VM/initramfs

The report connects two distinct lock objects to a rare boot failure: fsck updates an ext4 superblock while udev/libblkid reads identity; a missing UUID removes `/dev/disk/by-uuid`, stops the matching systemd fsck unit, and prevents the mount.

Systemd documents block-device-node locking; util-linux moved fsck locks under `/run/fsck` after earlier design discussion. The first task is to understand why both decisions exist and prove whether they fail to serialize the same device.

**First probe:** create an ext4 loop image, instrument both lock identities and superblock timing, pause fsck at the critical write, run the udev/blkid read, and add a shared-lock negative control before attempting boot loops.

**Negative ramifications:** changing lock identity or order can deadlock, over-serialize partitions, mishandle aliases/device mapper, or leave stale initramfs locks. Do not hide the race with a broad sleep.

**Disposition:** highest-consequence investigation; execute after the current-CI items and require strong independent review.

# Overlap review

## libarchive non-seekable 7-Zip handling

Linux Fieldwork: #230  
Public report: https://github.com/libarchive/libarchive/issues/3068  
Active equivalent fix: https://github.com/libarchive/libarchive/pull/3070  
Merged streamability repair: https://github.com/libarchive/libarchive/pull/3074  
Environment: current CI

The initial scan said no linked fix existed. That was wrong. Open PR 3070 already changes core seekability detection, the 7-Zip bidder, and a pipe/raw fallback test. Merged PR 3074 replaced one unconditional central-directory seek with forward consumption and restored stream reading for compatible layouts.

Current source's `seek_compat()` can consume forward on non-seekable input but cannot move backward. That means “7-Zip requires seek” is too broad: some archive layouts and operations can proceed sequentially, while others still need random access.

A controlled fork probe at `teamleaderleo/libarchive#1` first established that current master lists a tiny 7-Zip archive through direct and gzip-filtered pipes. Self-review then added extraction cases because listing alone can consume to end metadata without proving payload access.

**Review probe:** compare seekable file, direct pipe, gzip filter, externally decompressed pipe, listing, and extraction. Add larger archives and explicit callback seek failure if the small matrix leaves the active PR's boundary unclear.

**Negative ramifications:** a global bidder abstention can reject genuinely streamable archives or silently route them through raw mode. Keeping the bid can produce a late seek error. Spooling changes resource and cleanup behavior.

**Disposition:** stop independent implementation; retain exact evidence and review active PR 3070's compatibility boundary.

# Additional queue

## Nixpkgs AAVMF firmware regression

Retained source: `research/rounds/2026-07-30-ecosystem-candidate-scan/selection.md`  
Public report: https://github.com/NixOS/nixpkgs/issues/485220  
Environment: aarch64 QEMU

Pinned working and failing nixpkgs revisions plus a QEMU command already exist. Convert the console boundary into one automated pass/fail marker before bisecting package flags, edk2/AAVMF variants, or QEMU compatibility. Keep it behind the aarch64 gate.

## DuckDB read-only decode input mutation

Linux Fieldwork: #254  
Environment: current CI

Current source writes replacement bytes through a writable pointer to input BLOB storage. A controlled-fork candidate allocates result-owned storage only for invalid replacement input and retains a native dictionary-compression regression. Exact-head build/test remains active.

## DuckDB same-process checkpoint wrong result

Linux Fieldwork: #256  
Environment: current CI

A release matrix reproduced a persisted filtered wrong result on 1.5.4 and a clean 1.3.2 control. The first classifier did not independently prove the secondary-index execution path, so the probe is being strengthened before source modification.

## caching_proxy same-UID parent-swap race

Linux Fieldwork: #227  
Environment: current CI

Validation followed by pathname reuse may permit a same-UID process to redirect cache reads or publication outside a validated root. This can produce reusable descriptor-relative containment work across projects.

## make_mirror update-cache signal ownership

Linux Fieldwork: #231  
Environment: current CI

A concurrent workstream found that an `update_cache()` pipeline subshell can clean on INT/TERM, kill a parent-owned proxy, continue work, clean twice, and return success. Keep it separate from top-level PID registration so process and cleanup ownership stay explicit.

# Stops and references

## Deno `fetch()` Happy Eyeballs report

Linux Fieldwork: closed #253  
Public report: https://github.com/denoland/deno/issues/36279  
Disposition: **retained negative result**

Stable Deno 2.9.4 raced to healthy IPv4 in about 305 ms when IPv6 SYN packets were dropped. The public fixture instead accepted IPv6 TCP and withheld HTTP bytes, which is a response stall after connection establishment. Replaying the request through IPv4 would require a separate HTTP retry contract.

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

1. **Continuous current-CI production:** `lscpu` fix archaeology, DuckDB decode ownership, DuckDB checkpoint classification, local lifecycle/path races, and package-harvesting leaves.
2. **Serious capability-gated work:** systemd-oomd VM, fsck/udev boot race, BuildKit rootful/rootless parity, BuildKit exporter metadata, and AAVMF aarch64.

Overlap reviews such as libarchive #230 remain useful when they transfer exact tests or compatibility findings without creating a competing fix.

# Immediate sequence

1. Finish #254's DuckDB decode candidate gate.
2. Finish #256's strengthened checkpoint classifier.
3. Execute #234's sanitizer and canonical-fix matrix.
4. Classify #230's libarchive extraction probe and review active PR 3070; do not implement a competing fix.
5. Run #233's BuildKit exporter fixture when a pinned daemon/container is available.
6. Provision the cgroup-v2 VM for #140.
7. Build #232's direct loop-device fixture before boot loops.
8. Run #229's rootful/rootless OCI metadata comparison.
9. Preserve #231 and #227 as parallel work owned by their current workstreams.
10. Recheck external issue and development state before every branch.

# Evidence boundary

This round establishes public issue state and internal actionability, not every underlying product defect. Public reports can be incomplete or wrong. Deno #253 already produced a retained negative result. DuckDB #256 reproduced a release-boundary wrong result while mechanism attribution remains under repair. Each first probe must independently establish baseline behavior on an exact revision before a candidate patch or upstream packet is justified.

No third-party issue, comment, review, pull request, email, or patch was created by this work.