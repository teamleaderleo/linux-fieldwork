# Linux research landscape — 2026-07-30

## In simple words

This round maps promising Linux and Debian research into bounded lanes. Each lane begins as a question, names likely source trees, proposes a first probe, and records the environment needed to produce useful evidence. The immediate emphasis is work that can begin on the repository's existing Ubuntu 24.04 GitHub runner, with VM and kernel-lab work retained for later.

## Purpose

The list is a map for choosing work. It does not assert that any target contains a defect. A lane earns an investigation only after source reading and a small distinguishing probe reveal a concrete mechanism, consequence, and evidence path.

## Research method

The round used these filters:

1. **Consequence** — correctness, security, data integrity, cleanup, recovery, compatibility, or measurable resource behavior.
2. **Bounded first probe** — a small command, fixture, fault injection, or source-and-test map can distinguish useful outcomes.
3. **Exact source identity** — the target can be imported at a commit or package revision.
4. **Environment fit** — the required privilege, kernel, VM, hardware, and runtime requirements can be stated before work begins.
5. **Evidence portability** — another person can repeat the important observation.
6. **Honest stopping** — expected behavior, complete existing coverage, or weak consequence can close the lane cleanly.

## Execution classes

- **Current CI** — suitable for the existing Ubuntu 24.04 runner and ordinary package installation.
- **Privileged CI** — likely suitable for the current runner with `sudo`, mounts, namespaces, loop devices, or cgroup access; verify runner capabilities first.
- **VM** — requires QEMU, a booted guest, nested PID 1, controlled reboot, or crash simulation.
- **Kernel lab** — requires a custom kernel, kernel configuration, specialized tracing, fault injection, or hardware.
- **Source first** — begin with code and test mapping before choosing an execution environment.

The current repository already runs focused verification on `ubuntu-24.04`, installs dependencies with `sudo apt-get`, and retains artifacts. See [the existing mmdebstrap workflow](../.github/workflows/mmdebstrap-unwritable-tmpdir.yml).

## Recommended starting order

These lanes combine consequential boundaries with a credible first probe on the current repository setup:

1. **LF-02 — chrootless `DPKG_ROOT` containment**
2. **LF-07 — maintainer-script interruption and idempotency**
3. **LF-12 — reproducible package variance**
4. **LF-14 — archive extraction and metadata contracts**
5. **LF-20 — systemd stop, timeout, and descendant cleanup**
6. **LF-22 — cgroup v2 delegation and resource cleanup**
7. **LF-15 — OverlayFS copy-up, hard-link, and xattr behavior**
8. **LF-11 — merged-`/usr` path assumptions**
9. **LF-03 — rootless ownership and idmapped mounts**
10. **LF-23 — cancellation, subprocess, and file-descriptor cleanup**

A useful first campaign would select two lanes from packaging, two from namespaces or filesystems, and one from service lifecycle. That gives variety without scattering attention across every subsystem.

# Region A — rootless execution, namespaces, and mounts

## LF-01 — bootstrap mode parity

- **Question:** Which behavioral contracts differ across `mmdebstrap` root, unshare, fakechroot, and chrootless modes for the same package set and output format?
- **Why it is interesting:** Mode-specific paths combine package management, namespaces, ownership, hooks, temporary storage, and cleanup. Differences may expose real compatibility failures or reveal intentional boundaries that deserve clearer tests.
- **Likely targets:** `mmdebstrap`, `util-linux`, `shadow`/`uidmap`, `fakechroot`, package maintainer scripts.
- **First probe:** Generate the smallest identical tar or null-output case in each available mode; compare package set, archive metadata, ownership, hooks, diagnostics, and cleanup.
- **Environment:** Current CI for chrootless and selected unshare cases; privileged CI for root mode; source first for fakechroot limitations.
- **Promotion signal:** One mode violates an explicit contract, mutates the host unexpectedly, leaks resources, or produces unexplained output differences.
- **Stop signal:** Differences match documented mode semantics and tests cover them clearly.

## LF-02 — chrootless `DPKG_ROOT` containment

- **Question:** Which maintainer-script operations escape the intended target when packages are installed through `DPKG_ROOT` or `--force-script-chrootless`?
- **Why it is interesting:** The mmdebstrap manual warns that packages lacking root-directory support can modify the host because scripts execute outside a chroot. This is a direct host-integrity boundary.
- **Likely targets:** `mmdebstrap`, `dpkg`, Essential packages, `debhelper` helpers, maintainer scripts that invoke service, account, cache, or boot tooling.
- **First probe:** Build a throw-away target, instrument writes and process execution, install one minimal package set in chrootless mode, and classify every path touched outside the target.
- **Environment:** Current CI inside an additional disposable container or nested chroot; run unprivileged.
- **Promotion signal:** A package writes outside the target, invokes a host service action, reads host state as target state, or leaves partial target configuration without a precise diagnostic.
- **Stop signal:** All observed effects remain within the declared target and required host reads are documented.

## LF-03 — rootless ownership and idmapped mounts

- **Question:** Can idmapped mounts make rootless filesystem trees easier to inspect, edit, archive, and remove while preserving intended on-disk ownership?
- **Why it is interesting:** User namespaces often produce trees whose ownership appears shifted from the host. Idmapped mounts are designed to translate ownership at the mount boundary and may simplify rootless build workflows.
- **Likely targets:** Linux VFS idmapping, `util-linux` mount tools, `systemd-nsresourced`, `mmdebstrap`, container tooling.
- **First probe:** Create a small root-owned tree in a user namespace, expose it through an idmapped mount, and test stat, create, rename, archive, extract, and removal behavior from both namespace views.
- **Environment:** Privileged CI or a VM with idmapped-mount support; source first if the runner blocks mount operations.
- **Promotion signal:** A tool reports inconsistent ownership, loses IDs during copy/archive, mishandles unmapped IDs, or leaves trees that cannot be cleaned through the documented path.
- **Stop signal:** Ownership translation is consistent and tools preserve the declared IDs.

## LF-04 — mount propagation and teardown

- **Question:** Do bootstrap, container, and image tools fully detach nested mounts after success, failure, timeout, and interruption?
- **Why it is interesting:** A leaked bind, proc, sysfs, devpts, or overlay mount can block cleanup and contaminate later jobs.
- **Likely targets:** `mmdebstrap`, `systemd-nspawn`, `bubblewrap`, `util-linux`, image builders.
- **First probe:** Run a small mount-using operation under success, injected failure, SIGTERM, and timeout; compare `/proc/self/mountinfo`, loop devices, and mount namespaces before and after.
- **Environment:** Privileged CI or VM.
- **Promotion signal:** A mount remains reachable, cleanup depends on process exit ordering, host propagation occurs, or diagnostics omit the retained resource.
- **Stop signal:** Every path returns to the baseline mount and device set.

## LF-05 — pseudo-filesystem assumptions

- **Question:** Which tools assume `/proc`, `/sys`, `/dev`, `/run`, or cgroup files exist, are writable, or describe the host rather than the target?
- **Why it is interesting:** Chroots, containers, image builds, and early userspace commonly provide partial or synthetic pseudo-filesystems.
- **Likely targets:** package maintainer scripts, systemd utilities, initramfs tooling, `mmdebstrap`, `dpkg` helpers.
- **First probe:** Execute a focused operation with each pseudo-filesystem absent, read-only, minimally populated, or namespaced; record failure timing and host-state reads.
- **Environment:** Current CI for mocked paths; privileged CI for real mounts and namespaces.
- **Promotion signal:** Host state is mistaken for target state, writes cross the boundary, cleanup fails, or a late obscure error could become an early precise diagnostic.
- **Stop signal:** The tool detects the environment and follows a documented fallback.

## LF-06 — namespace capability lifecycle

- **Question:** After creating user, mount, PID, UTS, IPC, or network namespaces, which capabilities remain available, and which child operations rely on them unexpectedly?
- **Why it is interesting:** Capability checks depend on the governing user namespace. A process may appear root inside one namespace while lacking authority over another object.
- **Likely targets:** `util-linux` `unshare`/`nsenter`, `bubblewrap`, `mmdebstrap`, container launchers, `systemd-nspawn`.
- **First probe:** Build a capability matrix around mount, chown, mknod, sethostname, network configuration, and nested namespace creation.
- **Environment:** Privileged CI or VM.
- **Promotion signal:** A tool performs setup in the wrong namespace order, retains authority longer than required, or reports permission failures without naming the governing boundary.
- **Stop signal:** Capability transitions match the documented model and failure paths clean up fully.

# Region B — Debian packages, transactions, and builds

## LF-07 — maintainer-script interruption and idempotency

- **Question:** Can selected package `preinst`, `postinst`, `prerm`, and `postrm` scripts recover when interrupted between meaningful side effects?
- **Why it is interesting:** Debian Policy requires maintainer scripts to support error recovery and repeated execution. Real scripts manage accounts, services, caches, alternatives, diversions, and generated configuration.
- **Likely targets:** Essential and widely installed Debian packages, `debhelper` generated snippets, `dpkg` execution paths.
- **First probe:** Choose a small script with two or more observable side effects, inject termination after each step, rerun the package action, and compare final state with a clean installation.
- **Environment:** Current CI inside an expendable rootfs or container.
- **Promotion signal:** Re-execution fails, duplicates state, overwrites local configuration, leaves services inconsistent, or requires undocumented manual repair.
- **Stop signal:** Every interruption point converges on the clean final state.

## LF-08 — apt/dpkg transaction recovery

- **Question:** How well do apt and dpkg recover from interruption during download, unpack, trigger processing, configuration, and removal?
- **Why it is interesting:** Package transactions cross multiple durable states and may be interrupted by process termination, disk exhaustion, read-only filesystems, or maintainer-script failure.
- **Likely targets:** `apt`, `dpkg`, trigger consumers, package frontends.
- **First probe:** Use a tiny local repository and packages with controlled scripts; inject failure at each transaction stage and classify status database, locks, archives, triggers, and repair commands.
- **Environment:** Current CI in a disposable rootfs.
- **Promotion signal:** Recovery loses user data, produces contradictory package state, repeats unsafe side effects, retains locks, or offers a misleading repair path.
- **Stop signal:** Documented recovery commands restore a consistent state at every injection point.

## LF-09 — conffile and local-change preservation

- **Question:** Do upgrades, package splits, file moves, and maintainer-script generated configuration preserve local changes through all supported transitions?
- **Why it is interesting:** Configuration migration combines dpkg conffile semantics, maintainer scripts, prompts, diversions, and service reload behavior.
- **Likely targets:** `dpkg`, packages migrating configuration paths, `ucf`, `debhelper` helpers.
- **First probe:** Build two tiny package versions covering unchanged, locally modified, removed, moved, and generated configuration; test interactive and noninteractive upgrades.
- **Environment:** Current CI.
- **Promotion signal:** Local content is overwritten, abandoned silently, duplicated, or applied to the wrong path.
- **Stop signal:** Each transition preserves local intent and leaves an understandable result.

## LF-10 — triggers, ordering, and deferred work

- **Question:** Do dpkg triggers and package-generated deferred actions converge correctly after coalescing, interruption, package removal, and repeated activation?
- **Why it is interesting:** Trigger consumers update shared caches and indexes. Ordering mistakes can leave stale global state even when individual packages configure successfully.
- **Likely targets:** `dpkg`, `man-db`, `install-info`, icon/font/cache tools, `initramfs-tools`, `systemd` package helpers.
- **First probe:** Create a minimal trigger producer and consumer, then vary activation count, package order, interruption, and consumer failure.
- **Environment:** Current CI.
- **Promotion signal:** A trigger is lost, executed against incomplete state, repeated unsafely, or left pending without a clear repair route.
- **Stop signal:** Deferred work converges and status records explain the state.

## LF-11 — merged-`/usr` path assumptions

- **Question:** Which scripts and tools still distinguish `/bin` from `/usr/bin`, resolve symlinks too early, or mishandle package transitions on merged-`/usr` systems?
- **Why it is interesting:** Debian requires the merged layout, while path-sensitive code can still encode historical assumptions.
- **Likely targets:** maintainer scripts, initramfs tools, shell scripts, package build rules, path canonicalization utilities.
- **First probe:** Run selected tools in equivalent merged and synthetic split layouts; compare path discovery, archive contents, package installation, and generated configuration.
- **Environment:** Current CI for synthetic roots; VM for boot-sensitive cases.
- **Promotion signal:** Equivalent paths produce different functional results, symlink handling escapes a target root, or upgrades fail across the transition.
- **Stop signal:** Differences are cosmetic or explicitly required by policy.

## LF-12 — reproducible package variance

- **Question:** Which outputs change when build time, path, locale, timezone, hostname, user name, file order, and parallelism vary?
- **Why it is interesting:** Debian Policy defines reproducible package expectations, and the Reproducible Builds project provides mature variance categories and tools.
- **Likely targets:** Debian source packages, upstream build systems, `reprotest`, `diffoscope`, `strip-nondeterminism`, language-specific generators.
- **First probe:** Select a small package with a short build; run two builds varying one factor at a time; classify timestamps, paths, ordering, randomness, and embedded environment data.
- **Environment:** Current CI, preferably with local build dependencies cached or pinned.
- **Promotion signal:** A small source-level change or tool fix removes a deterministic difference with clear general value.
- **Stop signal:** Variation comes solely from declared toolchain inputs or is already normalized downstream.

## LF-13 — foreign architecture and binfmt boundaries

- **Question:** How do bootstrap and package tools behave when the target architecture requires qemu-user, `binfmt_misc`, cross tools, or architecture-specific maintainer scripts?
- **Why it is interesting:** Architecture detection and execution capability can fail late, produce host/target confusion, or leave partially configured roots.
- **Likely targets:** `mmdebstrap`, `qemu-user-static`, `binfmt-support`, `dpkg`, `arch-test`, package scripts.
- **First probe:** Create one small foreign-architecture root in extract-only and configured modes; vary binfmt presence and executable availability.
- **Environment:** Privileged CI or VM.
- **Promotion signal:** Host binaries run against target data, architecture errors appear after destructive work, or cleanup differs from native mode.
- **Stop signal:** Capability checks fail early and configured output matches the declared architecture.

# Region C — filesystems, archives, and disk images

## LF-14 — archive extraction and metadata contracts

- **Question:** How do bootstrap and image tools handle traversal paths, symlink races, hard links, sparse files, xattrs, ACLs, capabilities, device nodes, and numeric ownership?
- **Why it is interesting:** Root filesystem construction treats archives as executable filesystem descriptions. Metadata loss or path escape can affect security and correctness.
- **Likely targets:** `mmdebstrap` tar filters, GNU tar, `libarchive`, `dpkg-deb`, container-image unpackers.
- **First probe:** Build a canonical archive corpus with one feature per case and extract under root, user namespace, and restricted target-directory conditions.
- **Environment:** Current CI for ordinary metadata; privileged CI for device nodes, capabilities, and selected xattrs.
- **Promotion signal:** Extraction escapes the target, follows an unsafe link, silently drops required metadata, or behaves inconsistently across documented modes.
- **Stop signal:** Every unsupported feature is rejected precisely and supported metadata survives round-trip.

## LF-15 — OverlayFS copy-up, hard links, xattrs, and rename

- **Question:** Which application assumptions break when OverlayFS changes inode identity, copies up metadata or data, handles hard links, or redirects directories?
- **Why it is interesting:** OverlayFS deliberately differs from ordinary filesystems in inode reporting and copy-up behavior. Containers and package operations exercise these edges heavily.
- **Likely targets:** Linux OverlayFS, container runtimes, package managers, file scanners, backup tools.
- **First probe:** Create lower/upper fixtures covering hard links, open descriptors, xattrs, rename, chmod, chown, and copy-up; observe inode identity and data consistency.
- **Environment:** Privileged CI or VM.
- **Promotion signal:** A userspace tool loses a link relationship, trusts unstable inode identity, drops security metadata, or mishandles renamed directories.
- **Stop signal:** Behavior matches documented OverlayFS semantics and the consumer already accounts for it.

## LF-16 — rename, fsync, and crash durability

- **Question:** Which common update sequences actually survive simulated power loss with the intended file and directory state?
- **Why it is interesting:** Atomic rename gives namespace atomicity, while durable update often also requires syncing file content and parent directories.
- **Likely targets:** configuration writers, package databases, cache generators, editors, stateful daemons, ext4/XFS/btrfs test fixtures.
- **First probe:** Implement a tiny update sequence on a loopback filesystem, record writes with device-mapper log or fault tools, crash at selected points, and inspect recovered state.
- **Environment:** VM or kernel lab.
- **Promotion signal:** A project documents atomic replacement while its sequence can lose both old and new state, expose zero-length data, or retain inconsistent metadata.
- **Stop signal:** Recovered states stay within the documented contract.

## LF-17 — temporary files and directory contracts

- **Question:** Do tools honor explicit temporary-directory choices, create files safely, clean up after interruption, and report the exact failing path?
- **Why it is interesting:** Temporary storage crosses permissions, mount capacity, filesystem features, namespaces, environment inheritance, and cleanup.
- **Likely targets:** `mmdebstrap`, package builders, archive tools, image tools, compilers, test runners.
- **First probe:** Reuse a common matrix: missing, non-directory, unwritable, noexec, nosuid, tiny filesystem, different mount, symlinked path, interrupted process, and concurrent invocations.
- **Environment:** Current CI for most cases; privileged CI for mount options and capacity limits.
- **Promotion signal:** Silent fallback violates an explicit caller choice, insecure creation permits collision, cleanup leaks data, or errors name the wrong path.
- **Stop signal:** Each case follows a documented fallback or precise failure contract.

## LF-18 — disk-image dissection, growth, and cleanup

- **Question:** Do image tools correctly discover partitions, apply read-only policy, grow filesystems, attach loop devices, and unwind partial setup?
- **Why it is interesting:** A single operation can create loop devices, partition mappings, encrypted volumes, verity devices, mounts, and filesystem changes.
- **Likely targets:** `systemd-dissect`, `losetup`, `kpartx`, `cryptsetup`, image builders.
- **First probe:** Build tiny GPT images with valid, missing, conflicting, and damaged metadata; run inspect, mount, copy, grow, and forced-failure paths.
- **Environment:** Privileged CI or VM.
- **Promotion signal:** Read-only inspection mutates an image, partial setup leaks devices, policy selects the wrong partition, or cleanup order fails.
- **Stop signal:** Every operation leaves the device and mount set at baseline.

## LF-19 — verified and authenticated root images

- **Question:** Can image assembly and boot tooling produce, verify, update, and reject tampered dm-verity or dm-integrity roots with clear failure behavior?
- **Why it is interesting:** Verified roots connect build reproducibility, partition metadata, cryptographic roots, initramfs, and boot policy.
- **Likely targets:** `cryptsetup`, `systemd-veritysetup`, initramfs tooling, image builders, kernel device mapper.
- **First probe:** Build a tiny read-only filesystem and hash tree, verify clean reads, alter one data block and one hash block, and record userspace and kernel diagnostics.
- **Environment:** Privileged CI for device mapper; VM for boot-path claims.
- **Promotion signal:** Tampering produces ambiguous success, the wrong failure policy, leaked mappings, or an image whose verification metadata cannot be reproduced.
- **Stop signal:** Clean and corrupted cases follow the declared policy and clean up fully.

# Region D — services, processes, and resources

## LF-20 — systemd stop, timeout, and descendant cleanup

- **Question:** Under restart, stop timeout, process forking, reparenting, and signal resistance, which descendants survive and which cleanup guarantees hold?
- **Why it is interesting:** Service lifecycle behavior depends on cgroups, process tracking, signal selection, timeout policy, and unit state transitions.
- **Likely targets:** `systemd`, service unit authors, daemon wrappers, package-provided units.
- **First probe:** Create a test service that forks several descendant patterns, ignores selected signals, opens files, and mounts a temporary filesystem; exercise start, restart, stop, failure, and timeout.
- **Environment:** VM or a container booted with systemd as PID 1; selected user-unit probes may run in current CI.
- **Promotion signal:** Descendants survive outside the intended cgroup, resources remain attached, restart overlaps old and new workers, or unit state misrepresents reality.
- **Stop signal:** Process and resource cleanup match unit settings and diagnostics.

## LF-21 — tmpfiles and sysusers package lifecycle

- **Question:** Do declarative users, groups, directories, files, and cleanup rules behave safely across install, upgrade, removal, purge, and local administrator changes?
- **Why it is interesting:** `systemd-sysusers` and `systemd-tmpfiles` shift lifecycle work out of custom maintainer scripts, but package transitions and local ownership still create edge cases.
- **Likely targets:** systemd tools, `debhelper` integrations, packages adopting declarative files.
- **First probe:** Package a tiny service with sysusers and tmpfiles rules; vary pre-existing users, changed IDs, local files, removal, purge, and repeated execution.
- **Environment:** Current CI inside a disposable rootfs or VM.
- **Promotion signal:** Local data is removed, IDs drift, repeated execution changes state, package removal retains unsafe objects, or purge removes administrator-owned content.
- **Stop signal:** Lifecycle operations converge while preserving declared local ownership.

## LF-22 — cgroup v2 delegation and resource cleanup

- **Question:** Can delegated workloads create subgroups, apply controllers, hit limits, move processes, and disappear without leaving unusable controller state?
- **Why it is interesting:** cgroup v2 uses one hierarchy with controller enablement and delegation rules. Ordering and ownership errors can block nested managers or leave resource policy partially applied.
- **Likely targets:** systemd resource control, container managers, CI executors, user services.
- **First probe:** Create a delegated subtree, apply CPU, memory, pids, and I/O controls where available, induce limit hits and process exit, then verify controller and directory cleanup.
- **Environment:** Privileged CI or VM with writable delegated cgroups.
- **Promotion signal:** A manager cannot recover after partial setup, limit diagnostics identify the wrong layer, processes escape accounting, or empty groups remain undeletable.
- **Stop signal:** Delegation and teardown follow the kernel and manager contracts.

## LF-23 — cancellation, subprocess, and file-descriptor cleanup

- **Question:** When a Linux tool is interrupted, do all child processes, pipes, temporary files, locks, sockets, and inherited descriptors reach a clean final state?
- **Why it is interesting:** Build and administration tools commonly orchestrate many external commands. Signal forwarding and descriptor inheritance create subtle hangs and leaks.
- **Likely targets:** `mmdebstrap`, package builders, test runners, image tools, shell and Python orchestration code.
- **First probe:** Wrap each spawned command with observable PID and descriptor logging; interrupt at selected stages; inspect process trees, locks, open files, and retained paths.
- **Environment:** Current CI.
- **Promotion signal:** A child survives, a pipe prevents exit, a lock blocks rerun, output is reported as complete after cancellation, or cleanup deletes unrelated state.
- **Stop signal:** Cancellation converges quickly on a declared partial or rolled-back result.

## LF-24 — shutdown and soft-reboot persistence

- **Question:** Which runtime state, mounts, processes, logs, and generated files survive shutdown or userspace-only reboot, and do services declare those expectations correctly?
- **Why it is interesting:** Shutdown runs with many services and mounts already gone. Soft reboot preserves the kernel while replacing userspace, producing a different persistence boundary.
- **Likely targets:** systemd shutdown logic, journald, generators, services using `/run`, `/var`, or kernel-held state.
- **First probe:** Boot a small VM, create state in several lifetimes, perform ordinary reboot and soft reboot, and compare process, mount, journal, socket, and file state.
- **Environment:** VM.
- **Promotion signal:** A service trusts stale kernel or runtime state, shutdown hooks require unavailable paths, or logs fail to preserve the declared event boundary.
- **Stop signal:** Persistence matches documented lifetime rules.

# Region E — security and networking boundaries

## LF-25 — `no_new_privs`, seccomp, and Landlock composition

- **Question:** When self-restriction mechanisms are layered, which operations remain available and how do programs handle older kernels or partial feature support?
- **Why it is interesting:** These mechanisms restrict different boundaries and are inherited across process creation in different ways. Compatibility code can accidentally disable the whole sandbox or produce incomplete restrictions.
- **Likely targets:** sandbox launchers, package build tools, service managers, language runtimes, Landlock-enabled utilities.
- **First probe:** Create a small syscall and filesystem operation matrix under each mechanism alone and in combinations; vary available Landlock ABI and seccomp action support.
- **Environment:** Current CI for unprivileged cases; custom kernel only for feature-absence simulation beyond compatibility APIs.
- **Promotion signal:** A fallback silently removes unrelated protections, child processes gain access beyond the declared policy, or diagnostics claim protection that was never installed.
- **Stop signal:** Feature negotiation and enforcement match the declared policy.

## LF-26 — capability and credential transitions

- **Question:** Do setuid, file capabilities, ambient capabilities, bounding sets, securebits, and service-manager settings produce the intended authority before and after `execve()`?
- **Why it is interesting:** Linux credentials contain several capability sets whose transitions depend on executable metadata and process flags.
- **Likely targets:** systemd unit sandboxing, privilege-dropping daemons, container launchers, helper binaries.
- **First probe:** Build a tiny credential reporter and launcher; vary file capabilities, `no_new_privs`, ambient sets, UID changes, and exec chains.
- **Environment:** Privileged CI or VM.
- **Promotion signal:** A process retains authority after the documented drop point, loses required authority only in one launch path, or reports misleading effective privileges.
- **Stop signal:** All transitions match the explicit policy.

## LF-27 — network namespaces and DNS ownership

- **Question:** Who owns DNS configuration and resolver state when processes move among network namespaces, containers, VPNs, and systemd-resolved contexts?
- **Why it is interesting:** Connectivity can succeed while name resolution uses stale or host-global state. `/etc/resolv.conf` may be a file, symlink, bind mount, or generated view.
- **Likely targets:** `iproute2`, `systemd-resolved`, container tools, VPN clients, network test harnesses.
- **First probe:** Create two network namespaces with distinct DNS responders and route state; test resolver behavior under copied, bind-mounted, and generated resolver configuration.
- **Environment:** Privileged CI or VM.
- **Promotion signal:** Queries cross the intended namespace, stale configuration survives teardown, or tools overwrite administrator-managed resolver paths.
- **Stop signal:** Resolution follows the declared namespace and ownership model.

## LF-28 — nftables atomic update and rollback

- **Question:** Do complex nftables changes apply atomically, preserve counters and state as intended, and leave the prior ruleset intact after validation or runtime failure?
- **Why it is interesting:** Firewall updates are safety-critical and often generated from higher-level configuration.
- **Likely targets:** `nftables`, firewall managers, container network setup, package scripts.
- **First probe:** Use a network namespace and tiny traffic generator; submit valid and invalid batches, replace sets under traffic, and compare packet behavior and full rulesets before and after.
- **Environment:** Privileged CI or VM.
- **Promotion signal:** Partial policy becomes active, rollback loses state, generated handles target the wrong object, or concurrent updates race.
- **Stop signal:** Transactions are atomic and errors preserve the previous effective policy.

## LF-29 — netlink compatibility and fallback

- **Question:** How do userspace tools respond to missing attributes, new attributes, multipart dumps, asynchronous notifications, and kernel-version feature differences?
- **Why it is interesting:** Netlink is a broad kernel/userspace interface with evolving family specifications. Robust parsers must preserve unknown data rules and ordering assumptions.
- **Likely targets:** `iproute2`, `ethtool`, `nftables`, network managers, custom netlink libraries.
- **First probe:** Capture a small family exchange, replay reduced and extended messages through parser tests, and compare behavior across two kernel versions.
- **Environment:** Current CI for parser fixtures; VM for kernel-version comparison.
- **Promotion signal:** Unknown attributes break parsing, dumps lose objects, sequence handling accepts stale replies, or fallback silently changes semantics.
- **Stop signal:** Compatibility paths preserve known fields and reject malformed data precisely.

# Region F — boot, devices, and deeper kernel work

## LF-30 — initramfs dependency discovery and atomic update

- **Question:** Does initramfs generation include every required early-boot dependency and update `/boot` safely under failure, low space, unusual symlinks, and concurrent invocation?
- **Why it is interesting:** The initramfs locates and mounts the real root filesystem. Missing binaries, firmware, modules, configuration, or crypt metadata can make a machine unbootable.
- **Likely targets:** `initramfs-tools`, `dracut`, `cryptsetup-initramfs`, package hooks.
- **First probe:** Build a tiny VM image, vary one required dependency at a time, inject failure during image generation and replacement, then boot or inspect the archive.
- **Environment:** VM; selected archive-generation cases can run in current CI.
- **Promotion signal:** A successful command installs an unusable image, replaces the prior image before validation, omits a discovered dependency, or leaves `/boot` inconsistent.
- **Stop signal:** Generation fails before replacement and the produced image boots the declared configuration.

## LF-31 — udev and device hotplug races

- **Question:** Do rules and consumers behave correctly when devices appear, change, disappear, or emit events in unexpected order?
- **Why it is interesting:** Device setup spans kernel uevents, udev rules, helper programs, permissions, symlinks, and service activation.
- **Likely targets:** systemd-udevd, storage/network device rules, package-provided helpers.
- **First probe:** Use synthetic devices, loop devices, or a VM test driver; replay add/change/remove sequences and inspect nodes, links, permissions, and activated units.
- **Environment:** VM or kernel lab.
- **Promotion signal:** Removed devices leave authoritative symlinks, late events overwrite newer state, helpers act on reused device identities, or cleanup misses resources.
- **Stop signal:** Final state follows the latest event sequence and stale work is rejected.

## LF-32 — eBPF verifier and userspace-tool compatibility

- **Question:** Can a userspace BPF tool explain why a program fails across kernel versions and adapt safely to verifier, helper, map, and BTF differences?
- **Why it is interesting:** eBPF programs are checked by a complex verifier and frequently depend on kernel features discovered at load time.
- **Likely targets:** Linux BPF selftests, `bpftool`, libbpf-based tools, observability agents.
- **First probe:** Select a tiny program using one optional feature; load it on two kernels, capture verifier logs, and test userspace feature detection and fallback.
- **Environment:** VM or kernel lab.
- **Promotion signal:** The tool reports a generic failure, chooses an unsafe fallback, misdetects support, or produces incompatible generated objects.
- **Stop signal:** Feature negotiation yields equivalent safe behavior or a precise unsupported result.

## LF-33 — io_uring cancellation and resource release

- **Question:** Under cancellation, timeout, process exit, file close, and partial completion, which buffers, requests, descriptors, and user-visible results remain active?
- **Why it is interesting:** Asynchronous I/O creates lifetimes spanning submission, kernel processing, completion queues, registered resources, and process teardown.
- **Likely targets:** Linux io_uring, `liburing`, servers and storage tools adopting it.
- **First probe:** Create minimal read, write, accept, and timeout cases; cancel at defined points and record completion ordering, return codes, and registered-resource release.
- **Environment:** Current CI for basic cases; VM/kernel lab for version matrices and fault injection.
- **Promotion signal:** Cancellation reports completion inconsistently, resources remain pinned, fallback diverges from synchronous semantics, or teardown hangs.
- **Stop signal:** Lifetimes and completion results match the documented interface.

## LF-34 — block fault injection and recovery

- **Question:** How do filesystems and userspace tools react to delayed, dropped, corrupted, or selectively failing block I/O?
- **Why it is interesting:** Disk-full and generic I/O-error tests miss ordering-sensitive and intermittent failures. Device mapper provides controlled targets such as delay, flakey, dust, and log-writes.
- **Likely targets:** package databases, image builders, databases, filesystems, initramfs and boot tooling.
- **First probe:** Put a tiny workload on a loop-backed device-mapper target, inject one fault mode, and compare application diagnostics, on-disk state, retries, and cleanup.
- **Environment:** VM or kernel lab.
- **Promotion signal:** The application reports success before durable completion, loops indefinitely, corrupts its own metadata, or loses the last known-good state.
- **Stop signal:** Failure remains within the documented recovery contract.

# Cross-cutting note lanes

The following topics can begin as explanatory notes and feed several investigations:

- Linux credential model: real/effective/saved IDs, capability sets, and user namespaces.
- Mount namespaces, propagation types, and recursive teardown.
- File durability: write, fdatasync, fsync, rename, and directory sync.
- Debian package states and maintainer-script call sequences.
- dpkg triggers and shared-cache updates.
- `DPKG_ROOT`, chrootless installation, and target-versus-host state.
- OverlayFS inode identity, copy-up, whiteouts, and xattrs.
- cgroup v2 hierarchy, controller enablement, and delegation.
- systemd service process tracking and kill policy.
- initramfs composition and early-userspace responsibilities.
- netlink request, dump, notification, and sequencing behavior.
- reproducible build variance and `SOURCE_DATE_EPOCH`.

# Source orientation

These primary and project-maintained references informed the round:

- [Linux kernel documentation](https://www.kernel.org/doc/html/latest/)
- [cgroup v2](https://cdn.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)
- [filesystem idmappings](https://www.kernel.org/doc/html/next/filesystems/idmappings.html)
- [OverlayFS](https://www.kernel.org/doc/html/latest/filesystems/overlayfs.html)
- [`no_new_privs`](https://www.kernel.org/doc/html/latest/userspace-api/no_new_privs.html)
- [Landlock](https://cdn.kernel.org/doc/html/latest/userspace-api/landlock.html)
- [kernel networking documentation](https://www.kernel.org/doc/html/latest/networking/)
- [netlink family specifications](https://cdn.kernel.org/doc/html/latest/netlink/specs/index.html)
- [device-mapper documentation](https://www.kernel.org/doc/html/latest/admin-guide/device-mapper/index.html)
- [dm-verity](https://www.kernel.org/doc/html/latest/admin-guide/device-mapper/verity.html)
- [dm-integrity](https://docs.kernel.org/admin-guide/device-mapper/dm-integrity.html)
- [Debian Policy](https://www.debian.org/doc/debian-policy/)
- [Debian maintainer scripts and installation procedure](https://www.debian.org/doc/debian-policy/ch-maintainerscripts.html)
- [Debian source packages and reproducibility](https://www.debian.org/doc/debian-policy/ch-source.html)
- [Debian merged-`/usr`](https://wiki.debian.org/UsrMerge)
- [mmdebstrap manual](https://manpages.debian.org/testing/mmdebstrap/mmdebstrap.1.en.html)
- [update-initramfs manual](https://manpages.debian.org/trixie/initramfs-tools/update-initramfs.8.en.html)
- [Reproducible Builds documentation](https://reproducible-builds.org/docs/)
- [`SOURCE_DATE_EPOCH`](https://reproducible-builds.org/docs/source-date-epoch/)
- [systemd manual collection](https://www.freedesktop.org/software/systemd/man/)
- [systemd-tmpfiles](https://www.freedesktop.org/software/systemd/man/systemd-tmpfiles.html)
- [systemd namespace resource delegation](https://www.freedesktop.org/software/systemd/man/257/systemd-nsresourced.service.html)
- [systemd shutdown logic](https://www.freedesktop.org/software/systemd/man/254/systemd-halt.service.html)
- [systemd-dissect](https://www.freedesktop.org/software/systemd/man/252/systemd-dissect.html)

## Research boundary

This round establishes promising questions and first-probe designs from project documentation and the existing Linux Fieldwork execution model. It does not establish defects, affected versions, production impact, or upstream priority. Those claims belong in individual investigations tied to exact revisions and observed evidence.
