# runc target map

## In simple words

runc is a small userspace runtime with unusually dense Linux boundary code: namespaces, cgroups, mounts, process creation, signals, seccomp, file descriptors, and systemd integration meet kernel APIs directly. Small local assumptions can therefore change process placement, readiness, cleanup, or compatibility.

Current fieldwork should favor bounded invariants with tiny discriminators: same input across a fallback, same notification with fields reordered, same resource count before and after a lifecycle, and same semantics before and after a refactor.

## Current source identity

- Canonical project: opencontainers/runc
- Canonical branch: `main`
- Resolved upstream commit during the 2026-08-11 scout: `0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`
- Owned fork: `teamleaderleo/runc`
- Owned fork `main` at scout time: same resolved commit
- Key dependency for current cgroup work: `github.com/opencontainers/cgroups v0.0.8`

Refresh both upstream and fork identities before any source write or publication decision.

## Relevant programmes

- `services-resources` — cgroups, process/resource lifecycle, fd ownership, systemd readiness
- `rootless-execution` — namespace and cgroup-mode parity, fallback behavior
- `security-networking` — containment and authority boundaries where relevant
- `ecosystem-contributions` — bounded upstream candidates after exact reproduction and explicit authorization

## Active investigations

### sd_notify READY field ordering

[`../../investigations/runc-sd-notify-ready-order/README.md`](../../investigations/runc-sd-notify-ready-order/README.md)

Current main splits an sd_notify datagram into newline-separated fields but tests `READY=` against the complete datagram. A reduced executable probe shows that READY is recognized first and missed second. History traces the whole-datagram predicate to the 2018 create/start notification refactor.

Primary source history:

- [runc PR 1308](https://redirect.github.com/opencontainers/runc/pull/1308)
- [runc PR 1807](https://redirect.github.com/opencontainers/runc/pull/1807)
- [runc PR 3291](https://redirect.github.com/opencontainers/runc/pull/3291)

### sd_notify barrier descriptor lifetime

[`../../investigations/runc-sd-notify-barrier-fd-lifetime/README.md`](../../investigations/runc-sd-notify-barrier-fd-lifetime/README.md)

The successful barrier helper leaves the pipe read end and the descriptor produced by `UnixConn.File()` without explicit success-path closes. A reduced probe with GC disabled observes `+2` descriptors after one successful barrier. Full runc test-package reproduction is the next gate.

Primary source history:

- [runc PR 3291](https://redirect.github.com/opencontainers/runc/pull/3291)
- [runc PR 5243](https://redirect.github.com/opencontainers/runc/pull/5243)

### cgroup-v2 fallback containment parity

[`../../investigations/runc-exec-cgroup-v2-fallback-containment/README.md`](../../investigations/runc-exec-cgroup-v2-fallback-containment/README.md)

The cgroup-fd path and post-start `Manager.AddPid` fallback clean traversal-shaped subpaths differently. Source inspection predicts different targets for a prefix-colliding sibling input; a privileged two-road execution is required before calling the v2 case demonstrated.

Primary source history:

- [runc PR 3381](https://redirect.github.com/opencontainers/runc/pull/3381)
- [runc issue 5351](https://redirect.github.com/opencontainers/runc/issues/5351)
- [runc PR 4822](https://redirect.github.com/opencontainers/runc/pull/4822)
- [runc PR 4812](https://redirect.github.com/opencontainers/runc/pull/4812)

## Retained review lesson

[`../../notes/processes/history-can-change-the-repair-boundary.md`](../../notes/processes/history-can-change-the-repair-boundary.md) records the earlier `MaxCPU` episode around [runc issue 5388](https://redirect.github.com/opencontainers/runc/issues/5388), [PR 5389](https://redirect.github.com/opencontainers/runc/pull/5389), [PR 5392](https://redirect.github.com/opencontainers/runc/pull/5392), and the introducing [PR 5343](https://redirect.github.com/opencontainers/runc/pull/5343).

The reusable lesson is to inspect the refactor that caused two values, types, or helpers to meet before deciding which side owns the repair.

## High-yield source areas

### Process creation and fallback

Start with `libcontainer/process_linux.go` and nearby integration tests. Compare early kernel-assisted paths with later fallback paths. Ask whether the same input preserves identity, cgroup placement, affinity, errors, and cleanup.

### systemd notification proxy

Start with `notify_socket.go` and `notify_socket_test.go`. Useful invariants include field-order independence, sender/process identity, barrier completion, fd lifetime, timeout behavior, and attached versus detached process lifetime.

### cgroups

Read runc and opencontainers/cgroups together. A manager abstraction can move path validation, systemd authority, rootless behavior, and fallback ownership across repository boundaries.

### Mount and namespace transitions

Prefer exact caller/callee maps around host-side fd opening, namespace entry, pivot/chroot, mount propagation, and cleanup. Compare direct and mediated paths before proposing a local fix.

### State and serialization migrations

When runc changes pointer/scalar/fixed types into slices, dynamic masks, optional values, or new state representations, audit zero values, JSON round trips, equality, allocation boundaries, and every old nil/empty assumption.

## Review heuristics specific to runc

1. Trace the kernel primitive and the fallback together.
2. When a helper moved into opencontainers/cgroups, compare the old runc contract with the library's contract.
3. For path checks, use component identity as the invariant; raw string prefixes deserve immediate challenge.
4. For process liveness, distinguish PID number, process identity, fd ownership, and cgroup membership.
5. For refactors, inspect the pre-refactor meaning and the exact commit that connected the pieces.
6. For tests, pin semantic boundaries and lifecycle cleanup instead of allocator or runtime side effects.
7. Search active issues and PRs immediately before writing upstream; several attractive bugs can already have a live maintainer fix.

## Current stop / promotion rules

Promote a runc candidate when it has:

- exact upstream source identity;
- one bounded invariant;
- a losing baseline or source-level discriminator;
- a negative control;
- history/intent checked;
- exact owner of the repair identified;
- full-source or privileged runtime execution where the claim requires it;
- cleanup and rerun recorded;
- refreshed overlap search.

Keep source-only mismatches in `SCOPING` when the runtime path or capability discriminator remains unexecuted.

## Authority

This target map grants no permission to contact runc or any dependency maintainer. Owned-fork branches and internal fieldwork records remain separate from upstream issues, comments, reviews, or pull requests. External interaction requires an explicit human decision.
