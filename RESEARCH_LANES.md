# Research Lanes

## In simple words

This is the short working index for choosing Linux Fieldwork investigations. The detailed first landscape round maps 34 possible lanes. The list below highlights the strongest places to begin with the current repository and keeps deeper VM and kernel work visible for later.

See [`research/2026-07-30-linux-landscape.md`](research/2026-07-30-linux-landscape.md) for full questions, first probes, target ideas, environment requirements, promotion signals, and stop signals.

## Ready to scout

### 1. Chrootless `DPKG_ROOT` containment — LF-02

Trace every write and process action while installing a minimal package set through chrootless dpkg. Look for host mutations, host-versus-target confusion, service actions, and late failure.

**Likely first target:** the imported `mmdebstrap` tree plus a deliberately small package set.

### 2. Maintainer-script interruption and idempotency — LF-07

Choose a package script with several observable side effects, terminate it after each step, rerun the package operation, and compare the result with a clean installation.

**Likely first targets:** small Debian packages using debhelper-generated service, account, cache, or configuration snippets.

### 3. Reproducible package variance — LF-12

Build a small package twice while varying time, path, locale, timezone, hostname, file order, or parallelism. Use diffoscope-style analysis to find the first meaningful difference.

**Likely first targets:** short builds with generated manuals, archives, documentation, or embedded version data.

### 4. Archive extraction and metadata contracts — LF-14

Create a canonical archive corpus covering traversal paths, symlinks, hard links, sparse files, xattrs, ACLs, capabilities, device nodes, and numeric ownership. Compare behavior across rootless and privileged extraction paths.

**Likely first target:** `mmdebstrap` tar filtering and import/export behavior.

### 5. Cancellation and descendant cleanup — LF-23

Interrupt orchestration tools while they own children, pipes, locks, temporary files, and output paths. Verify that reruns start from a clean state.

**Likely first target:** the existing mmdebstrap runner and its child-process paths.

### 6. Merged-`/usr` path assumptions — LF-11

Compare equivalent operations inside merged and synthetic split root filesystems. Focus on symlink resolution, package scripts, initramfs paths, and target-root escapes.

**Likely first targets:** Debian maintainer scripts and bootstrap hooks.

## Ready after a capability check

### 7. Rootless ownership and idmapped mounts — LF-03

Test whether idmapped mounts provide a reliable host view of rootless trees while preserving intended on-disk ownership.

**Needs:** mount and user-namespace support on the runner or a small VM.

### 8. OverlayFS copy-up and metadata behavior — LF-15

Exercise hard links, xattrs, rename, chmod, chown, open descriptors, and inode identity across lower and upper layers.

**Needs:** privileged mount access.

### 9. cgroup v2 delegation and cleanup — LF-22

Create a delegated subtree, apply resource controls, hit limits, move processes, and verify complete teardown.

**Needs:** a writable delegated cgroup hierarchy or a VM.

### 10. Network namespace DNS ownership — LF-27

Create isolated namespaces with different DNS responders and compare resolver behavior under copied, generated, and bind-mounted configuration.

**Needs:** network namespace and virtual-interface privileges.

### 11. nftables atomic update and rollback — LF-28

Apply valid and invalid ruleset batches under traffic and verify that errors preserve the previous effective policy.

**Needs:** network namespace and netfilter privileges.

## VM queue

- **LF-20:** systemd stop, timeout, restart, and descendant cleanup.
- **LF-24:** shutdown and soft-reboot persistence.
- **LF-30:** initramfs dependency discovery and atomic replacement.
- **LF-18:** disk-image dissection, growth, and device cleanup.
- **LF-19:** dm-verity and dm-integrity image assembly.
- **LF-31:** udev and hotplug event ordering.
- **LF-16:** rename, fsync, and crash durability.
- **LF-34:** block fault injection and recovery.

## Kernel and version-matrix queue

- **LF-25:** `no_new_privs`, seccomp, and Landlock composition.
- **LF-29:** netlink compatibility and fallback.
- **LF-32:** eBPF verifier and userspace-tool compatibility.
- **LF-33:** io_uring cancellation and resource release.

## Selection rule

Choose one lane whose first probe fits the available environment. Begin with source and test mapping, then open an investigation only when the probe has distinguishing outcomes and a meaningful consequence.

A good active mix is:

- one Debian package-transaction lane;
- one namespace or filesystem lane;
- one service or process-lifecycle lane;
- one short reproducibility or archive lane.

Keep the rest mapped until an active lane closes or branches into a clearly different question.
