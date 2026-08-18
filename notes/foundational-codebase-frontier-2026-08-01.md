# Foundational codebase frontier — 2026-08-01

## In simple words

Linux is held together by a lot of small, serious programs between applications and the kernel. They decide who a user is, which kernel driver loads, how process data is interpreted, which capabilities survive execution, and how network requests are encoded.

This note records a directed shortlist after the long mmdebstrap run. It is not a promise to investigate everything. Each candidate has a small source owner, a realistic local test surface, a negative control, and a reason it could change an actual Linux decision.

## Selection rules

Prefer codebases with:

- a foundational operation rather than a desktop-only feature;
- exact current source and active maintenance;
- a small fixture that can make the mechanism lose;
- local, container, fake-root, or fake-syscall execution;
- compatibility boundaries across kernel/userspace, files, processes, or distributions;
- a useful result even when no bug is found.

Avoid starting with a giant subsystem unless one source owner and one discriminator are already named.

## 1. kmod — active now

- Canonical repository: `https://git.kernel.org/pub/scm/utils/kernel/kmod/kmod.git`
- GitHub mirror: `https://github.com/kmod-project/kmod`
- Master observed: `5086df53090b2fe9fa1c31351c05a78a12a4ba71`
- Target map: [`../targets/kmod/map.md`](../targets/kmod/map.md)
- Active investigation: [`../investigations/kmod-modprobe-options-config-path/`](../investigations/kmod-modprobe-options-config-path/)

Why it is interesting:

- sits directly on driver loading, initramfs generation, aliases, blacklists, dependencies, signatures, and module removal;
- tests can fake root filesystems, `init_module()`, `delete_module()`, and `uname()`;
- current testsuite work is actively consolidating command and library coverage;
- small configuration or index mistakes can silently select different kernel policy.

First result:

A spaced `-C` configuration path is honored by the parent `modprobe` but serialized without quoting into `MODPROBE_OPTIONS`; a nested install-rule `modprobe` silently uses default configuration and exits `0`.

## 2. shadow — account and subordinate-ID state

- Repository: `https://github.com/shadow-maint/shadow`
- Latest stable release observed: `4.19.4`, 2026-03-02
- Suggested target state: `inbox`, then map before source changes

Why it is interesting:

- owns `useradd`, `usermod`, `groupadd`, `passwd`, `chpasswd`, `newusers`, subordinate-ID files, account databases, and related locking/update code;
- directly intersects rootless containers, `/etc/subuid`, `/etc/subgid`, chroot/prefix handling, home-directory creation, and package lifecycle;
- recent releases include regressions and corrections around password-hash acceptance, usermod behavior, path prefix/chroot handling, and stricter account-name rules;
- many commands support disposable alternate roots or prefix paths, allowing controlled tests without editing the host account database.

High-yield first questions:

- exact username matching and malformed-line behavior across subuid/subgid readers and writers;
- interrupted commonio database replacement: lock, temp file, mode, ownership, fsync, rename, and recovery;
- `--root` versus `--prefix` path identity and SELinux/file-context behavior;
- partial failure during user/group plus home-directory updates.

Best first discriminator:

Use a disposable prefix containing passwd, shadow, group, gshadow, subuid, and subgid fixtures. Compare a successful update, a deliberately interrupted replacement, and a same-prefix-name negative control. Require complete-tree metadata and lock cleanup, not just command status.

## 3. procps-ng — hostile and changing `/proc`

- Repository: `https://gitlab.com/procps-ng/procps.git`
- Latest release observed: `4.0.6`, 2026-01-29
- Suggested target state: `inbox`

Why it is interesting:

- owns `ps`, `pgrep`, `pidwait`, `top`, `free`, `vmstat`, `pmap`, `w`, `watch`, and libproc2;
- `/proc` files can disappear, change between reads, deny access, omit fields, contain large values, or represent a process that has been recycled;
- recent work includes openat-based `/proc/<pid>` access, race/segfault fixes, pidfd signaling, environment permission handling, missing-field behavior, and terminal/session corrections;
- many parsers can be tested with fixture trees, namespaces, short-lived child processes, and permission controls.

High-yield first questions:

- PID identity across read-open-read sequences and pidfd fallbacks;
- partial or permission-denied `environ`, `stat`, `status`, `maps`, and `smaps` data;
- JSON/text or library/CLI parity when one field is unavailable;
- process exit/reuse during `pgrep`, `pidwait`, `pmap`, and `ps` collection;
- terminal/session identity when utmp, logind, and `/proc` disagree.

Best first discriminator:

Spawn a controlled process tree, repeatedly replace accessibility and lifetime boundaries, and compare CLI output, libproc2 output, status, diagnostics, and stale-PID controls. Preserve the first event in time rather than classifying only the final state.

## 4. libcap — capability representation and launch boundaries

- Canonical source family: `https://git.kernel.org/pub/scm/libs/libcap/libcap.git`
- Suggested target state: `inbox`; resolve exact current head before work

Why it is interesting:

- capability text/binary conversion, file xattrs, ambient/inheritable/permitted/effective sets, and capability-aware process launch are small but security-critical surfaces;
- tests can combine ordinary users, user namespaces, file capabilities on disposable filesystems, and no-new-privs controls;
- representation changes can appear correct in text while losing unknown bits, rootid, xattr revision, or launch-state semantics.

High-yield first questions:

- text → binary → text round trips with unknown, duplicate, reordered, and empty sets;
- file capability revision/rootid preservation under copy, rename, archive, and overlay operations;
- ambient capability behavior across exec, interpreter scripts, no_new_privs, and uid/gid changes;
- launcher error/cleanup behavior when the target exec fails.

Best first discriminator:

Use a user namespace and disposable files to compare libcap API state, `getcap`/`setcap` text, raw xattr bytes, child `/proc/self/status`, exec failure, and clean rerun.

## 5. iproute2 — netlink, extended errors, JSON, and batches

- Canonical source family: `https://git.kernel.org/pub/scm/network/iproute2/iproute2.git`
- Suggested target state: `inbox`
- Natural programme fit: LF-29 netlink compatibility/fallback and LF-27 network-namespace ownership

Why it is interesting:

- owns common userspace encoding and decoding for routes, links, addresses, traffic control, namespaces, and netlink diagnostics;
- behavior spans kernel feature negotiation, extended acknowledgements, batch files, text/JSON output, retries, and partial application;
- most tests can run inside disposable network namespaces without affecting host networking.

High-yield first questions:

- text versus JSON parity for unknown or partially supported attributes;
- batch-file first failure, later continuation, rollback expectations, and exit status;
- extended-ack offset/message ownership when the kernel rejects nested attributes;
- fallback behavior across kernels with different netlink capabilities;
- namespace cleanup when a command is interrupted.

Best first discriminator:

Create a disposable namespace and run a batch containing one valid operation, one deliberately unsupported/malformed operation, and one later valid operation. Record netlink extack, status, text/JSON receipts, final namespace state, cleanup, and rerun.

## Deliberately deferred giants

### Linux kernel

Foundational, but too broad without a named subsystem and fixture. Enter through one of the userspace boundaries above, then follow the exact syscall/netlink/filesystem owner into the kernel when necessary.

### systemd

Already present in the registry and has mapped lanes. Continue through a bounded service/cgroup/tmpfiles/sysusers question rather than a generic codebase tour.

### glibc and musl

Excellent foundational targets, but start only with a narrow API boundary such as NSS enumeration, resolver cancellation, `posix_spawn` file actions, locale parsing, or dynamic-loader environment handling.

## Recommended order

1. Continue kmod until the exact-master baseline and native test answer whether the finding survives current source.
2. Start shadow with a disposable account-database transaction and subordinate-ID identity matrix.
3. Start procps-ng with a changing-process/permission fixture.
4. Use libcap when the runtime can supply a controlled user namespace and file-capability filesystem.
5. Use iproute2 when disposable network namespaces and at least two kernel generations are available.

## Stop rule

This frontier note is complete when it changes selection from “pick a famous project” to “pick one exact owner and discriminator.” Reopen it when:

- a candidate target becomes inactive or changes repository;
- a new investigation reveals a better adjacent owner;
- the available runtime gains a capability that unlocks a previously blocked probe;
- two separate findings show the same reusable defect class in another foundational project.

## Authority

Internal Linux Fieldwork planning only. No upstream contact is authorized or performed.
