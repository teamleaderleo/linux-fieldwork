# Candidate design notes — cross-netns Unix socket liveness

Companion to [`README.md`](README.md) and internal issue `teamleaderleo/linux-fieldwork#573`.

## TL;DR

Current systemd already has helper APIs that can keep a candidate compact:

- `proc_dir_open()` / `proc_dir_read_pidref()` enumerate processes without hand-rolling `/proc` directory parsing;
- `pidref_namespace_open()` can request a process network-namespace fd and root fd;
- namespace fds can provide an exact namespace identity for deduplication;
- the socket candidate already has statx metadata in `dir_cleanup()`, so live-socket lookup can move from pathname membership to filesystem identity membership.

Linux current source confirms that `/proc/<pid>/net/*` is backed by the target task's `nsproxy->net_ns` and the per-network-namespace `net->proc_net` tree. This is why `/proc/<pid>/net/unix` can expose a foreign namespace's Unix table without entering it.

The first candidate data model should keep exact identities separate from permission-degraded observations. A useful sketch is:

```text
verified live socket IDs:      (filesystem device, inode)
unverified live pathnames:     absolute path strings seen in readable foreign tables
```

The second set is only for cases where the Unix table is readable but `/proc/<pid>/root/<path>` identity resolution is denied. Whether those unresolved pathnames should veto deletion is a product-policy decision: doing so favors preserving a possibly-live socket and accepts false retention when another mount namespace uses the same pathname.

## Reusable systemd helpers

Current `src/basic/process-util.h` exposes:

```c
int proc_dir_open(DIR **ret);
int proc_dir_read(DIR *d, pid_t *ret);
int proc_dir_read_pidref(DIR *d, PidRef *ret);
```

Current `src/basic/namespace-util.h` exposes:

```c
int pidref_namespace_open(
        const PidRef *pidref,
        int *ret_pidns_fd,
        int *ret_mntns_fd,
        int *ret_netns_fd,
        int *ret_userns_fd,
        int *ret_root_fd);
```

It also exposes type-specific namespace opening and same-namespace helpers.

That suggests an implementation can use project-native process/namespace identity types instead of introducing a custom `/proc` walker solely for tmpfiles.

Primary current sources:

- https://github.com/systemd/systemd/blob/9b75d9bc66dc4f64e4fdd33603d199d374c0873b/src/basic/process-util.h
- https://github.com/systemd/systemd/blob/9b75d9bc66dc4f64e4fdd33603d199d374c0873b/src/basic/namespace-util.h

## Linux proc-net ownership

Current Linux `fs/proc/proc_net.c` resolves `/proc/<pid>/net` by looking up the target task and taking `task->nsproxy->net_ns`. Its per-network-namespace initializer creates the `net->proc_net` hierarchy used for those lookups.

Primary source:

- https://github.com/torvalds/linux/blob/d58772d8520c7ef247c4b95c9bd76d3a25da9ff5/fs/proc/proc_net.c

This source supports the observed discriminator:

```text
/proc/net/unix                    -> tmpfiles process netns
/proc/<foreign-pid>/net/unix      -> foreign process netns
```

No namespace transition is required merely to read the table when procfs permissions allow it.

## Observed proc-file dedup clue

In the runtime environment:

```text
same network namespace:
/proc/self/net/unix       dev:ino = 28:4026531922
/proc/225/net/unix        dev:ino = 28:4026531922
/proc/266/net/unix        dev:ino = 28:4026531922

foreign network namespace:
/proc/<foreign>/net/unix  dev:ino = 28:4026532217
```

Linux source explains why these files are selected from a per-netns proc tree. This could be useful as an opportunistic duplicate-table detector in restricted environments where `/proc/<pid>/ns/net` cannot be statted.

Do not make this observed proc-file inode behavior the sole namespace identity contract without a stronger kernel-interface justification. A successfully opened namespace fd remains the clearer primary identity when available.

## Candidate load algorithm

One bounded design is:

1. Keep the current namespace table as a cheap first source.
2. Enumerate process `PidRef`s using `proc_dir_open()` / `proc_dir_read_pidref()`.
3. For each process, try to acquire network-namespace and root identity using project helpers.
4. Deduplicate successfully identified network namespaces.
5. Read one `/proc/<pid>/net/unix` table for each namespace representative.
6. For every absolute filesystem socket pathname:
   - resolve/stat it relative to the representative process root;
   - cache `(device,inode)` when successful;
   - classify permission-denied identity resolution separately instead of pretending it is an exact match.
7. Mark a namespace as completed only after its Unix table was successfully read, so a PID-exit race does not hide a later representative.
8. In `dir_cleanup()`, compare a socket candidate's statx filesystem identity against the verified live set.
9. Apply the selected degraded-mode rule to unresolved path observations.

This keeps active socket probing, `setns()`, and arbitrary fd scanning out of the first candidate.

## Why exact socket-file identity belongs in the cache

The mount-alias control proved pathname-only global liveness is wrong:

```text
host stale /tmp/lf-alias/sock          dev=65024 ino=572499
foreign live /tmp/lf-alias/sock        dev=32    ino=2
```

Both network tables can contain the same absolute pathname string while the filesystem objects differ.

Conversely, a foreign network namespace can point at the **same** shared filesystem socket inode as tmpfiles. The identity matrix demonstrated that `(device,inode)` separates these cases exactly in the tested fixtures.

## Degraded permission mode

The local container exposed three useful classes.

### Full identity access

Same-uid user mode could stat the foreign process netns and root and read its Unix table.

### Table readable, identity denied

Reduced-capability uid 0 could read several uid-1000 `/proc/<pid>/net/unix` tables but received `EACCES` for `/proc/<pid>/ns/net` and `/proc/<pid>/root`.

### Current namespace

The existing `/proc/net/unix` path remains available and provides complete liveness for sockets in tmpfiles' own network namespace regardless of individual process-root access.

### Possible conservative policy

A candidate could maintain:

```text
verified_ids
unverified_paths
```

If a foreign Unix table exposes `/tmp/foo.sock` but process-root stat fails specifically for an authority reason, place the pathname in `unverified_paths`. Cleanup can then choose to preserve a candidate whose exact path appears there.

Tradeoff:

```text
benefit: avoid unlinking a potentially live inaccessible foreign-netns socket
cost:    an unrelated mount namespace can keep a stale same-path socket around
```

That cost is narrower than using global pathname matching universally because exact identities still own the normal path.

This investigation leaves the policy open for human/systemd design review. Another defensible choice is to preserve current behavior for unresolved namespaces and document the remaining reduced-capability boundary.

## Smallest test seam

The candidate needs a fixture that can make the classifier lose.

Minimum cases:

```text
A. same netns, shared inode
   expected: live

B. foreign netns, shared inode
   expected: live

C. dead socket
   expected: dead

D. foreign netns, same pathname, different mount inode
   expected: host stale inode dead

E. representative exits before table read, sibling remains
   expected: sibling recovers namespace

F. same-uid user mode
   expected: live

G. table readable but root identity denied
   expected: explicit selected degraded result
```

A synthetic implementation can test the socket-index loader independently from age timestamps. An integration test should then prove tmpfiles cleanup retains B and removes C/D.

## Reopen conditions

Revisit this design if any of these are established:

- `/proc/<pid>/root/<socket-path>` cannot reliably identify the filesystem socket inode for a relevant supported pathname class;
- systemd already has a stronger global Unix-socket enumeration interface that crosses network namespaces safely;
- procfs security policy makes representative enumeration unusable on ordinary host deployments;
- the scan becomes materially expensive on realistic large PID/netns/socket populations;
- `--root` or `--image` semantics require a different identity authority from the host process table;
- a kernel interface appears that can query filesystem Unix socket liveness globally by inode without active connection.

## Authority

This is internal design research. No upstream comment, issue mutation, pull request, review, or other contact has been authorized or made.
