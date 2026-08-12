# crun propagation fallback can use the pre-overmount fd path

Date: 2026-08-12

Internal tracking: `teamleaderleo/linux-fieldwork#602`

Related programme lane: `LF-04` — mount propagation and teardown.

## TL;DR

Current crun `main` reopens a mount target after placing a new mount because the old target fd still refers to the mount underneath the overmount. The new `mount_setattr()` propagation path correctly uses the reopened fd. However, if that operation fails, the legacy `mount(2)` fallback still uses `real_target`, a `/proc/self/fd/...` pathname captured from the **old pre-overmount fd**.

A disposable Linux 6.18.35 x86_64 user+mount namespace reproduced the mount-object identity consequence directly. Two stacked tmpfs mounts were marked shared. Applying `MS_PRIVATE` through the pre-overmount fd changed the hidden lower mount from `shared` to private while the visible top mount remained shared. Applying the same operation through the reopened fd changed the visible top mount instead.

The history boundary is unusually clean. In the parent of `9259e891acd25e49ae96cce8b595eb1a46be73e7`, crun refreshed `real_target` immediately after reopening the target:

```c
targetfd = fd;
get_proc_self_fd_path (target_buffer, targetfd);
real_target = target_buffer;
```

The June 2026 new-mount-API change retained the reopen but dropped the `real_target` refresh while also adding a `mount_setattr()`-first propagation path with a legacy fallback. The stale path remains present at current `main` (`86e7e3eaf8e8d15e6e9983faddeffd0ea0771a94`).

**Current recommendation:** restore the post-overmount `real_target` refresh from the reopened fd, then force the propagation path into its legacy fallback and verify that the visible mount—not the hidden lower mount—receives the requested propagation state.

No upstream contact is authorized or has been made.

## Explain like I'm five

Imagine a folder has one floor, and crun keeps a handle to that floor. Then crun installs a new floor on top and correctly gets a new handle to the top floor.

Later it wants to change a property such as “shared” or “private.” It first tries the modern Linux operation using the new handle. If that modern operation fails, the fallback accidentally uses the old handle's `/proc/self/fd/...` path.

The command reports success, but it changes the floor hidden underneath instead of the floor the container can see.

## Why care

Mount propagation controls whether mount and unmount events can flow between mount trees. Applying the requested propagation state to the wrong mount object can leave the visible container mount with a different sharing relationship than the OCI configuration requested, while silently mutating a hidden lower mount.

This is especially relevant on fallback paths:

- kernels or build environments where `mount_setattr()` is unavailable;
- syscall mediation that blocks `mount_setattr()` but still permits legacy `mount(2)`;
- other real `mount_setattr()` failures, because current code falls back after any error from the propagation attempt.

The result is a wrong-result/identity defect, not a claim of privilege escalation. The present evidence is local, synthetic, and disposable.

## Question

After crun overmounts a target and reopens it, does a failed `mount_setattr()` propagation attempt cause the legacy fallback to operate on the hidden pre-overmount mount instead of the visible new mount?

## Source boundary

### Current source

- Project: `containers/crun`
- Requested revision: current `main`
- Resolved commit: `86e7e3eaf8e8d15e6e9983faddeffd0ea0771a94`
- Release at that head: 1.29 merge/tag sequence
- Relevant file: `src/libcrun/linux.c`
- Relevant helper: `do_mount()`

### Introduction boundary

- Suspected introduction: `9259e891acd25e49ae96cce8b595eb1a46be73e7`
- Parent: `a98380bed173fed6df24932c689daef24421bb66`
- Commit subject: `linux: use new mount API in do_mount when available`

Direct source references are safe in this tracked repository file:

- https://github.com/containers/crun/commit/9259e891acd25e49ae96cce8b595eb1a46be73e7
- https://github.com/containers/crun/blob/86e7e3eaf8e8d15e6e9983faddeffd0ea0771a94/src/libcrun/linux.c

## Source walk

### 1. The original target fd becomes stale after overmount

At entry to `do_mount()`, when `targetfd >= 0`, crun builds `real_target` from that fd:

```c
get_proc_self_fd_path (target_buffer, targetfd);
real_target = target_buffer;
```

The initial mount is then placed over that target.

Current source explicitly recognizes what this does to fd identity:

```c
/* We need to reopen the path as the previous targetfd is underneath the new mountpoint.  */
fd = open_mount_target (container, target, err);
...
targetfd = fd;
```

The reopened `targetfd` points at the visible new mount. The original fd, and a proc-fd magic path built from it, continue to identify the hidden lower mount.

### 2. The modern propagation operation uses the right fd

For `MS_SHARED`, `MS_PRIVATE`, `MS_SLAVE`, or `MS_UNBINDABLE`, current source first executes:

```c
ret = do_mount_setattr (false, target, targetfd, 0,
                        mountflags & ALL_PROPAGATIONS, &tmp_err);
```

At this point `targetfd` is the reopened fd, so the modern path addresses the visible mount.

### 3. The fallback uses `real_target`

If that call fails, crun discards the temporary error and executes:

```c
ret = mount (NULL, real_target, NULL,
             mountflags & ALL_PROPAGATIONS, NULL);
```

At current head, `real_target` has not been rebuilt after `targetfd = fd`. It therefore still names the proc-fd path captured from the pre-overmount fd.

### 4. The parent did refresh it

In parent `a98380bed173fed6df24932c689daef24421bb66`, immediately after reopening the target, the code did:

```c
targetfd = fd;
get_proc_self_fd_path (target_buffer, targetfd);
real_target = target_buffer;
```

Its propagation operation then used `real_target`, so the legacy propagation call addressed the reopened mount.

The June new-mount-API change removed that refresh while adding the `mount_setattr()`-first propagation branch and fallback.

## Adjacent-context control: ordinary remounts

The stale `real_target` variable looks broader than the propagation block, so the remount path was checked separately.

`do_remount()` does **not** blindly trust the caller's pathname when a target fd is available. It first tries `do_mount_setattr()` through the fd and, on fallback, rebuilds its own proc-fd pathname:

```c
if (targetfd >= 0)
  {
    ...
    get_proc_self_fd_path (target_buffer, targetfd);
    real_target = target_buffer;
  }
```

Therefore this investigation does not claim that ordinary remount fallback shares the same stale-path defect. The currently demonstrated wrong-object path is the propagation fallback inside `do_mount()`.

## Environment

Runtime reduction environment:

```text
Linux 6.18.35 x86_64
Python 3.13.5
initial uid: 0
outer Seccomp: 0
outer CapEff: 00000000a00425fb
```

The outer container did not need host mount state. The probe ran inside:

```sh
unshare -Urnm sh -c 'mount --make-rprivate / && python3 probe.py'
```

Namespace-local mount capability was sufficient. Namespace exit owned cleanup.

## Reproduction

Tracked probe: [`probe.py`](probe.py).

From this investigation directory:

```sh
unshare -Urnm sh -c 'mount --make-rprivate / && python3 probe.py'
```

The fixture does this:

1. create a tmpfs at a disposable target and mark it shared;
2. open `old_fd` to that mount and record its `mnt_id`;
3. overmount the same pathname with a second tmpfs and mark it shared;
4. open `new_fd` and record the new mount's different `mnt_id`;
5. emulate the stale fallback by applying `MS_PRIVATE` through `/proc/self/fd/<old_fd>`;
6. inspect both mount IDs;
7. apply the same operation through `/proc/self/fd/<new_fd>` as a negative/control path.

## Results

Observed output:

```text
old-before 95 shared:1 95 77 0:31 / /tmp/crun-fd-rklob63b/target rw,relatime shared:1 - tmpfs tmpfs rw,mode=755
new-before 96 shared:2 96 95 0:32 / /tmp/crun-fd-rklob63b/target rw,relatime shared:2 - tmpfs tmpfs rw,mode=755
old-hidden-before 95 shared:1
old-after-fallback 95 private 95 77 0:31 / /tmp/crun-fd-rklob63b/target rw,relatime - tmpfs tmpfs rw,mode=755
new-after-fallback 96 shared:2 96 95 0:32 / /tmp/crun-fd-rklob63b/target rw,relatime shared:2 - tmpfs tmpfs rw,mode=755
new-after-control 96 private 96 95 0:32 / /tmp/crun-fd-rklob63b/target rw,relatime - tmpfs tmpfs rw,mode=755
```

### Interpretation

The discriminator is mount identity, not pathname text:

- old fd → mount ID 95;
- visible reopened fd → mount ID 96.

After the stale-fd fallback, mount 95 changed from shared to private, while visible mount 96 remained shared. The control through the reopened fd then changed mount 96 to private.

This directly demonstrates that `/proc/self/fd/<pre-overmount-fd>` still addresses the hidden lower mount for a propagation change.

## Competing explanations checked

### “Maybe `/proc/self/fd/N` resolves to the visible pathname after overmount”

Rejected by the mount-ID result. The operation through the old proc-fd path changed mount ID 95, not visible mount ID 96.

### “Maybe crun never notices that the old fd is below the new mount”

Rejected by source. Current code explicitly says the previous `targetfd` is underneath the new mountpoint and reopens it.

### “Maybe every later fallback is stale, so the fix needs to be broad”

Not supported. `do_remount()` rebuilds the proc-fd pathname from its fd before legacy fallback. The demonstrated defect is narrower.

### “Maybe this predates the new mount API”

The immediate parent refreshed `real_target` after reopening, so its propagation operation used the new fd-derived proc path. The current stale-path behavior appears at the June 2026 change boundary.

## Candidate

The smallest source candidate is to restore the parent behavior after the post-overmount reopen:

```c
targetfd = fd;
get_proc_self_fd_path (target_buffer, targetfd);
real_target = target_buffer;
```

This keeps the modern fd-based paths unchanged and corrects any subsequent legacy use of `real_target` to identify the visible mount.

A more localized alternative is to build a fresh proc-fd pathname only inside the propagation fallback. The parent behavior is preferable as a first candidate because it re-establishes the existing invariant: after crun knows the old fd is underneath the overmount and obtains a new fd, both fd and path representations should refer to the same visible mount.

## Candidate gates

Before promoting a fix:

1. compile current crun with only the minimal refresh restored;
2. run existing mount tests;
3. force `do_mount_setattr()` propagation to fail after a successful initial mount;
4. prove the legacy propagation fallback changes the visible reopened mount ID;
5. verify `MS_SHARED`, `MS_PRIVATE`, and at least one of `MS_SLAVE` / `MS_UNBINDABLE`;
6. verify bind and filesystem-mount callers if both reach the fallback;
7. rerun an ordinary remount control to ensure its existing fd-based fallback remains unchanged;
8. confirm the final diff is limited to the intended source/test change.

A strong injected-failure control is an outer seccomp filter that blocks only `mount_setattr()` while permitting legacy `mount(2)`. A Linux 5.2–5.11 environment would exercise a similar compatibility class naturally because `open_tree()` predates `mount_setattr()`.

## Evidence boundary

Demonstrated:

- exact current crun source contains the reopen/stale-path mismatch;
- the immediate parent refreshed `real_target` from the reopened fd;
- the June 2026 new-mount-API commit is the observed history boundary;
- a pre-overmount O_PATH fd and reopened post-overmount fd identify distinct mount IDs;
- propagation via the old proc-fd path mutates the hidden lower mount;
- propagation via the reopened fd mutates the visible mount;
- `do_remount()` has its own fd-to-proc-path refresh and is not included in the current claim.

Not yet demonstrated:

- a compiled crun binary reproducing the wrong visible propagation state end to end;
- all propagation modes;
- a complete crun test-suite result for a candidate;
- prevalence of fallback-triggering kernels or seccomp profiles in production;
- any security impact beyond wrong propagation semantics.

## Cleanup

The runtime fixture used a fresh disposable user+mount namespace. Namespace exit removed both tmpfs mounts and all propagation state. No host mount namespace was modified.

## Current disposition

- State: `EXECUTING`
- Exact current source: `containers/crun@86e7e3eaf8e8d15e6e9983faddeffd0ea0771a94`
- Introduction boundary: `9259e891acd25e49ae96cce8b595eb1a46be73e7`
- Tracked runtime probe: `probe.py`
- Current answer: propagation fallback can address the hidden pre-overmount mount through stale `real_target`
- Candidate direction: restore the reopened-fd `real_target` refresh
- Cleanup state: complete
- Next safe action: prepare and test a minimal owned-fork candidate if an owned crun fork is available
- External-contact state: no upstream interaction authorized or made
