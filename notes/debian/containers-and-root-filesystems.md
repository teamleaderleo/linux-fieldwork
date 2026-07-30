# Containers and root filesystems

## In simple words

A container is a Linux process launched with a selected filesystem view, namespace membership, resource controls, capabilities, and syscall policy. A container image supplies files and launch configuration. The kernel supplies isolation and accounting.

`mmdebstrap` is useful here because it creates the filesystem half directly. It lets us inspect the product before Docker, Podman, containerd, or a VM runner adds its own behavior.

## The execution chain

A useful model is:

```text
Debian package indexes
  -> apt dependency solution
  -> dpkg unpack/configure
  -> root filesystem tree or tar archive
  -> image/layer conversion
  -> runtime creates namespaces and mounts
  -> runtime applies cgroups, capabilities and seccomp
  -> kernel executes the container process
```

Every arrow can introduce defects or nondeterminism.

## What Docker knowledge this develops

### Image contents

A Docker or OCI image contains ordered filesystem changes plus configuration. Root filesystem archives teach the lower-level questions:

- Which files came from which packages?
- Which numeric UID and GID own them?
- Which modes, links, device nodes and extended metadata survived archival?
- Which timestamps or generated files change between builds?
- Which package scripts ran while constructing the root?

### Namespace behavior

A runtime normally creates some combination of mount, PID, network, IPC, UTS, cgroup, time, and user namespaces. Rootless execution depends heavily on user namespaces and subordinate UID/GID delegation.

A process can appear as UID 0 inside a user namespace while mapping to an unprivileged host UID outside it. That distinction explains many confusing ownership, bind-mount, device-node, and capability failures.

### Cgroups

Namespaces alter what a process can see. Cgroups account for and limit CPU, memory, process counts, and I/O. Container debugging improves when visibility and resource control are treated as separate mechanisms.

### Capabilities and seccomp

UID 0 alone does not describe container privilege. The effective capability set, namespace ownership, `no_new_privs`, and seccomp filter decide which operations succeed. Mounting a filesystem, creating device nodes, loading a module, changing network state, and tracing another process each follow different checks.

### Filesystem boundaries

A container root can involve overlayfs layers, bind mounts, idmapped mounts, tmpfs, read-only mounts, and runtime-created files. A reproducible tar archive may still produce different runtime behavior after these mounts are assembled.

## Debugging order

When a container or rootless bootstrap fails, collect evidence in this order:

1. Exact command, artifact digest, package snapshot, architecture and kernel.
2. Process identity and UID/GID mappings.
3. Namespace handles and mount table.
4. Effective capabilities, `no_new_privs`, and seccomp mode.
5. Cgroup version, membership and limits.
6. Root filesystem metadata before runtime conversion.
7. Runtime-generated mounts and files.
8. First failing syscall or package operation.

Use `scripts/capture-linux-context.sh` for the host side. Use `tools/tar_manifest.py` and `tools/manifest_diff.py` for root filesystem archives.

## First experiments

- Build the same Debian root twice with a fixed package snapshot and `SOURCE_DATE_EPOCH`; compare complete manifests.
- Repeat in privileged and unshare modes; identify differences in ownership, devices, links, and timestamps.
- Convert one root into an OCI image and compare the image layer manifest with the source tar.
- Boot the same root under QEMU and run it through a rootless container runtime; separate build differences from runtime differences.
- Cross-build arm64 on amd64 and identify which behavior belongs to APT/dpkg, QEMU user emulation, binfmt, or the kernel.
