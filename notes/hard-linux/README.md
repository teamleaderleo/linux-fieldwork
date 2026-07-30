# Hard Linux notes

This notebook follows mechanisms beneath distributions and container products.

## Current threads

- [Containers and root filesystems](containers-and-root-filesystems.md) — how namespaces, cgroups, mounts, capabilities, seccomp, and root filesystem archives meet.
- [Rootless bootstrap campaign](../../campaigns/0001-rootless-bootstrap/README.md) — reproducible Debian roots built without a permanently privileged build process.

## Note standard

Each note should answer five questions:

1. Which kernel or userspace mechanism owns the behavior?
2. Which process owns the relevant state?
3. Which namespace, mount, capability, cgroup, file descriptor, or package database boundary is crossed?
4. Which observation separates the competing explanations?
5. Which small command can reproduce the behavior?

Keep commands and observed output beside the explanation. Record the kernel, distribution, architecture, user namespace settings, subordinate ID ranges, mount options, cgroup mode, and container runtime when they influence the result.
