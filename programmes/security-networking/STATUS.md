# Security and Networking Boundaries

## In simple words

This programme studies authority transitions, sandbox composition, network namespace ownership, firewall transactions, and kernel/userspace protocol compatibility.

## Current direction

- **Inbox:** LF-25 — `no_new_privs`, seccomp, and Landlock composition
- **Inbox:** LF-26 — capability and credential transitions
- **Inbox:** LF-27 — network namespaces and DNS ownership
- **Inbox:** LF-28 — nftables atomic update and rollback
- **Inbox:** LF-29 — netlink compatibility and fallback

## First sequence

Begin only after a runner capability survey. LF-25 and parser-only parts of LF-29 offer the lightest entry. Network namespace and nftables work require isolated privileged execution.

## Candidate targets

Linux security APIs, systemd sandboxing, `iproute2`, `systemd-resolved`, nftables, network managers, container launchers, netlink libraries.

## Authority

Programme mapping grants no upstream-contact authority.