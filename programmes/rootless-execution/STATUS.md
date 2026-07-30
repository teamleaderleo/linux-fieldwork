# Rootless Execution, Namespaces, and Mounts

## In simple words

This programme studies how Linux tools construct isolated roots, cross namespace boundaries, translate ownership, mount pseudo-filesystems, and clean up resources. The immediate work focuses on host-versus-target containment and ownership behavior.

## Current direction

- **Mapped:** [LF-02 — chrootless `DPKG_ROOT` containment](lanes/LF-02-chrootless-dpkg-root-containment/brief.md)
- **Mapped:** [LF-03 — rootless ownership and idmapped mounts](lanes/LF-03-rootless-ownership-idmapped-mounts/brief.md)
- **Inbox:** LF-01 — bootstrap mode parity
- **Inbox:** LF-04 — mount propagation and teardown
- **Inbox:** LF-05 — pseudo-filesystem assumptions
- **Inbox:** LF-06 — namespace capability lifecycle

## First sequence

Begin with LF-02 on the existing imported `mmdebstrap` tree. Run a capability check before LF-03. Promote another lane only when one of those produces a clear branch or reaches its stop condition.

## Candidate targets

`mmdebstrap`, `dpkg`, `util-linux`, `uidmap`, `bubblewrap`, `systemd-nspawn`, Linux VFS and namespace interfaces.

## Authority

Programme mapping grants no upstream-contact authority.