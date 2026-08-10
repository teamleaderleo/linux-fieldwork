# systemd-tmpfiles cross-network-namespace Unix socket liveness

Internal tracking: `teamleaderleo/linux-fieldwork#573`

## TL;DR

Current systemd source decides whether an aged filesystem Unix socket is live by loading absolute path strings from **one** `/proc/net/unix` — the network namespace of `systemd-tmpfiles` itself — into a cache. A listener in another network namespace can therefore remain alive while its shared filesystem socket path is classified exactly like a dead socket and deleted.

A disposable runtime probe reproduced that distinction with installed systemd-tmpfiles 257.9 on Linux 6.18.35 x86_64:

```text
same-net live     -> visible in outer /proc/net/unix -> retained
foreign-net live  -> absent from outer /proc/net/unix -> deleted
dead socket       -> absent from outer /proc/net/unix -> deleted
```

Current `systemd/systemd` main at `9b75d9bc66dc4f64e4fdd33603d199d374c0873b` still contains the same one-namespace pathname classifier in `src/tmpfiles/tmpfiles.c`, so the source owner remains current even though the executable reproduction used an older installed binary.

The most useful follow-up result is that `setns()` is unnecessary in the tested environment. `/proc/<pid>/net/unix` exposes the Unix table belonging to that PID's network namespace. A prototype can enumerate PIDs, deduplicate accessible network namespaces, read one Unix table per namespace, resolve each absolute socket pathname through `/proc/<pid>/root`, and cache the **filesystem `(device,inode)` identity** of the live socket.

The inode step is essential. A negative control created a live `/tmp/lf-alias/sock` behind a different mount namespace while leaving a distinct stale host inode at the exact same pathname. A naive union of all namespace path strings would falsely preserve the stale host socket. The identity prototype correctly classified the host inode as dead while retaining live sockets from foreign network namespaces when they referred to the same filesystem inode.

The initial design still has a permission boundary: reduced-capability container root can read some other users' `/proc/<pid>/net/unix` while receiving `EACCES` for `/proc/<pid>/ns/net` and `/proc/<pid>/root`. Same-uid user-mode access worked. A production candidate needs an explicit degraded-mode policy for entries whose Unix table is readable but whose filesystem identity cannot be verified.

## Explain like I'm five

A Unix socket can look like a little file such as `/tmp/app.sock`. systemd-tmpfiles periodically removes old files from temporary directories, but it tries to spare socket files that still have a server listening.

Today it asks one list: “which Unix sockets are alive in **my** network namespace?” If the server lives in another network namespace, that list omits the socket even when both processes see the same socket file. tmpfiles can then age-delete the pathname underneath the still-running server.

Literal example:

```text
listener alive in another netns
        ↓
shared /tmp/demo.sock still exists
        ↓
host /proc/net/unix omits it
        ↓
tmpfiles sees old socket + no liveness entry
        ↓
unlink /tmp/demo.sock
```

The stronger classifier asks each visible network namespace for its sockets and then checks which **actual filesystem inode** each pathname names. That extra identity check prevents a socket with the same spelling in an unrelated mount namespace from protecting the wrong host file.

## Why care

The upstream report is an X11 case: an Xwayland server isolated with Bubblewrap publishes `/tmp/.X11-unix/X0` for host clients, but its separate network namespace hides the live socket from host `/proc/net/unix`. tmpfiles can eventually remove that pathname while the server remains alive.

This is a cleanup-ownership error. The server owns a live kernel socket; tmpfiles owns age-based cleanup of the directory; network namespace visibility causes the cleanup process to lose the evidence that should veto deletion.

The same mechanism can affect other filesystem AF_UNIX sockets created by isolated services that intentionally publish a socket through a shared or bind-mounted directory.

## Current state

- State: `EXECUTING`
- Exact source head reviewed: `systemd/systemd@9b75d9bc66dc4f64e4fdd33603d199d374c0873b`
- Runtime binary: systemd-tmpfiles 257.9 (`257.9-1~deb13u1`)
- Runtime kernel: Linux 6.18.35 x86_64
- Latest evidence: three-way tmpfiles reproduction + `/proc/<pid>/net/unix` visibility + mount-alias negative control + inode classifier matrix + scan timing
- First incomplete step: decide degraded behavior for namespaces whose socket table is visible but `/proc/<pid>/root` identity resolution is denied
- Cleanup state: disposable listeners/namespaces exited
- Next safe action: map the smallest current-source candidate around `load_unix_sockets()` and a focused test seam
- External-contact state: no upstream interaction authorized or made

## Intent and precedent

Upstream issue:

- https://github.com/systemd/systemd/issues/42771

The reporter observed the issue with systemd 259.6 on Fedora 44 and a 6.19 kernel. Their concrete X11 reproduction uses Bubblewrap with a separate network namespace. The issue remains open and is labeled `bug`, `needs-discussion`, and `tmpfiles`.

Discussion already rejected “connect to every socket” as a general liveness probe: arbitrary Unix sockets may react to connections, and datagram sockets have different semantics. The reporter suggested enumerating network namespaces and reading their Unix tables, while noting anonymous namespaces are absent from named-netns directories such as `/run/netns`.

One maintainer questioned publishing a socket from a namespaced process into a host-owned directory and suggested creating/binding it outside first. That is a deployment alternative, not a source-level explanation that makes tmpfiles' current liveness classifier complete: the supported filesystem can still contain a live socket whose owning network namespace differs from tmpfiles'.

## Current source owner

At current main, `Context` contains:

```c
Set *unix_sockets;
```

`load_unix_sockets()`:

1. opens `/proc/net/unix`;
2. skips its header;
3. extracts absolute pathname entries;
4. stores those path strings in `c->unix_sockets`;
5. caches the result for the rest of the run.

`unix_socket_alive()` then does:

```c
return set_contains(c->unix_sockets, fn);
```

If loading `/proc/net/unix` fails, it conservatively assumes the socket is alive.

During directory cleanup, socket files receive this special veto before age evaluation:

```c
if (S_ISSOCK(sx.stx_mode) && unix_socket_alive(c, sub_path)) {
        log_debug("Skipping \"%s\": live socket.", sub_path);
        continue;
}
```

So the source-level invariant is clear: a socket that is live according to the liveness cache must survive cleanup. The defect is that the cache's observation boundary is only tmpfiles' current network namespace.

Primary current source:

- https://github.com/systemd/systemd/blob/9b75d9bc66dc4f64e4fdd33603d199d374c0873b/src/tmpfiles/tmpfiles.c

## Question

Can tmpfiles recognize a live filesystem AF_UNIX socket across visible network namespaces while preserving these properties?

- no active connection to the socket;
- no assumption that one pathname string means the same filesystem object in every mount namespace;
- dead sockets still age out;
- same-network-namespace behavior stays intact;
- user mode works for same-user isolated processes;
- PID exit races do not suppress another representative from the same network namespace;
- scan cost remains bounded enough for startup/cleanup use;
- reduced `/proc` visibility has an explicit policy instead of silently producing overconfident liveness results.

## Source

- Project: `systemd/systemd`
- Requested revision: current `main` observed during this pass
- Resolved commit: `9b75d9bc66dc4f64e4fdd33603d199d374c0873b`
- Candidate source commit: none
- Local project checkout: none
- Source access: connected GitHub repository

## Environment

Runtime reproduction:

```text
systemd-tmpfiles: 257.9-1~deb13u1
kernel: Linux 6.18.35 x86_64
python: 3.13.5
unshare: available
socat: available (the retained probe uses Python instead)
outer uid: 0
```

The outer container lacks host `CAP_SYS_ADMIN`, while unprivileged user/network namespaces are available. The reproduction uses `unshare -Urn` for a disposable foreign network namespace and a shared filesystem pathname.

The tmpfiles cleanup is scoped to a unique `/tmp/lf-*` directory through both a dedicated config file and `--prefix`, so the probe cannot age-clean unrelated `/tmp` content.

## Baseline reproduction

Retained helper: [`reproduce.sh`](reproduce.sh).

The config is equivalent to:

```text
D /tmp/lf-tmpfiles-cross-netns.* 0777 root root 1s
```

The probe creates three socket inodes:

1. `same` — live listener in tmpfiles' network namespace;
2. `foreign` — live listener under `unshare -Urn`, sharing the filesystem path;
3. `dead` — listener exits and leaves its socket inode behind.

After waiting beyond the one-second age threshold, outer `/proc/net/unix` showed:

```text
same    visible=yes
foreign visible=no
dead    visible=no
```

Observed cleanup:

```text
same after=socket
foreign after=gone
dead after=gone
```

Relevant debug output included:

```text
Skipping "/tmp/lf-tmpfiles-sockets/same": live socket.
Removing "/tmp/lf-tmpfiles-sockets/foreign"
Removing "/tmp/lf-tmpfiles-sockets/dead"
```

The foreign listener process remained alive when its pathname disappeared.

This is the distinguishing result. The same-age, same-filesystem socket survives or disappears solely according to the network namespace from which the listener is visible to `/proc/net/unix`.

## `/proc/<pid>/net/unix` discriminator

A listener in a foreign network namespace produced:

```text
self-net=net:[4026531833]
child-net=net:[4026532189]
host /proc/net/unix:              socket absent
/proc/<child>/net/unix:           socket present
```

No `setns()` call was needed to read the child's Unix table in this environment.

This gives a smaller mechanism than entering each namespace: enumerate visible process entries and read one representative `/proc/<pid>/net/unix` for each network namespace.

## Why pathname union is insufficient

A second fixture kept a stale host socket inode at:

```text
/tmp/lf-alias/sock
```

Then a child received both a new user/network namespace and a new mount namespace, mounted tmpfs over `/tmp/lf-alias`, and created a **different live socket inode** at the same absolute pathname.

Observed identities:

```text
host pathname:       device 65024, inode 572499
child-root pathname: device 32,    inode 2
```

The child's `/proc/<pid>/net/unix` still printed the string `/tmp/lf-alias/sock`.

Therefore this algorithm is unsafe:

```text
union pathname strings from every /proc/<pid>/net/unix
→ if cleanup pathname string appears anywhere, call it live
```

It can preserve a stale host socket because an unrelated mount namespace happens to use the same spelling.

## Exact filesystem identity prototype

Retained helper: [`socket-identity-scan.py`](socket-identity-scan.py).

For each accessible network namespace representative, the prototype:

1. reads `/proc/<pid>/net/unix`;
2. keeps absolute pathname sockets;
3. resolves the pathname through that process's root as `/proc/<pid>/root/<absolute-path>`;
4. stats that object without following the final symlink;
5. stores `(st_dev, st_ino)` in a live-socket identity set.

A namespace is marked as seen only **after** its Unix table was successfully read. If a representative PID disappears first, a later PID from the same namespace can still provide the table.

Classifier matrix:

```text
same-net live shared inode       identity_live=True
foreign-net live shared inode    identity_live=True
dead socket                      identity_live=False
same path / different mount      identity_live=False
```

The alias child socket itself had a distinct live identity, while the stale host inode remained absent from the live identity set.

### Candidate seam

`dir_cleanup()` already has `statx` data for each socket candidate. A production design can compare the candidate's device/inode identity with the cached live-socket identity set instead of asking only whether its pathname string appears in one namespace table.

This is a design direction, not a finished patch. The exact systemd hash type, statx mask, root/path resolution helper, and error policy need current-tree implementation review.

## Performance probe

A Python prototype measured the proc scan plus one Unix-table parse per successfully deduplicated network namespace.

Path-oriented scan medians in this container:

```text
baseline, 1 visible netns       ~0.086 ms
10 additional netns             ~0.258 ms
50 additional netns             ~0.983 ms
100 additional netns            ~1.905 ms
```

A second prototype added the `/proc/<pid>/root/<socket-path>` stat needed for exact filesystem identities and ran with one live foreign-netns socket per extra namespace.

Completed 10-namespace result:

```text
median ~0.257 ms
10 socket identities resolved
```

The attempted larger live-socket batch exceeded the surrounding execution window during fixture setup, so no 50/100-socket identity timing is claimed.

These are Python microbenchmarks in one container, not systemd C benchmarks. They do show that “enumerating a handful of namespaces is automatically too expensive” is unsupported by this fixture. A C implementation can still lose on machines with very large PID/netns populations, so a candidate should retain a scale test.

## Permission boundary

The environment exposed a useful split.

### Same-user user mode

A uid-1000 process created a socket in its own user+network namespace. Another uid-1000 process could successfully:

```text
stat /proc/<pid>/ns/net
stat /proc/<pid>/root/<socket-path>
read /proc/<pid>/net/unix
```

So the identity mechanism is viable for the tested same-user `systemd-tmpfiles --user` style case.

### Reduced-capability container root

The container's uid 0 could read several uid-1000 processes' `/proc/<pid>/net/unix` and `mountinfo`, but received `EACCES` for `/proc/<pid>/ns/net` and `/proc/<pid>/root`.

That environment can know **a pathname is live somewhere** while being unable to prove whether the foreign pathname maps to the same filesystem inode being cleaned.

A production candidate needs an explicit degraded mode. One plausible conservative model is to keep two classes:

- verified live filesystem identities;
- unresolved live pathname observations when identity resolution is denied.

An unresolved matching pathname could veto deletion, accepting a false-preservation risk only where the process lacks enough authority to distinguish mount aliases. Another design may choose a different boundary. This investigation does not select that policy yet.

## Adjacent contexts checked

### Mount namespace alias

Result: decision-changing. Path strings alone fail; exact filesystem identity is required for a general all-netns scan.

### Same-user user mode

Result: identity access succeeds in the tested case.

### Reduced-capability root

Result: identity access can fail while the network table remains readable. Requires explicit degraded behavior.

### PID exit during scan

Design control: deduplicate a namespace only after successfully reading its table. `ENOENT` before that point leaves later representatives eligible.

### Active probing

Rejected as the initial direction. Connecting to arbitrary stream or datagram Unix sockets can have application-visible side effects and does not preserve the current passive-classifier character.

## Interpretation

The upstream issue is reproducible and its source owner is narrow: the liveness cache observes only one network namespace and keys liveness by pathname.

The first research hypothesis — “just union all `/proc/<pid>/net/unix` pathnames” — fails the mount-alias negative control. That failure is valuable because it prevents a superficially simple fix from widening false preservation across containers/chroots/mount namespaces.

The stronger hypothesis survives the tested matrix: enumerate accessible Unix tables, resolve each pathname through the process root, and key liveness by the socket file's actual device/inode identity.

The remaining blocker is policy under incomplete `/proc` authority, not the central identity mechanism.

## Evidence boundary

Demonstrated here:

- current systemd main still uses one `/proc/net/unix` pathname cache;
- installed systemd-tmpfiles 257.9 reproduces the same-net/foreign-net/dead distinction;
- `/proc/<pid>/net/unix` provides a foreign network namespace's Unix table in the tested environment;
- a naive cross-netns pathname union has a concrete false-positive across mount namespaces;
- `/proc/<pid>/root/<path>` filesystem identity distinguishes the shared-inode and alias cases;
- the prototype correctly classified four meaningful controls;
- small-to-100-network-namespace path scans and a 10-live-socket identity scan are inexpensive in this Python/container fixture;
- same-uid user-mode identity access succeeds here;
- reduced-capability container root can encounter an identity-resolution permission gap.

Still open:

- build and run current systemd main;
- choose and review degraded behavior for inaccessible process roots/namespaces;
- verify current systemd helper APIs that minimize bespoke `/proc` traversal;
- stress PID exit/reuse while scanning;
- inspect hidepid/procfs configurations;
- test chroot/`--root`/`--image` cleanup semantics;
- test a large real process/socket population;
- implement exact C data types and statx comparison;
- add a current-tree integration test that creates the foreign network namespace without requiring unsafe host cleanup.

## Next step

Prepare a source-level candidate design against current systemd with this minimum test matrix:

```text
same netns + same inode         -> retained
foreign netns + shared inode    -> retained
foreign netns + alias pathname  -> stale host inode removable
dead socket                     -> removable
representative PID exits        -> later representative can recover namespace
same-user user mode             -> retained
identity permission denied      -> explicit documented degraded result
```

Keep upstream contact separate. No upstream issue comment, PR, review, or other interaction has been authorized or made.
