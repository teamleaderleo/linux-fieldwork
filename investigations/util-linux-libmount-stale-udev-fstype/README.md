# libmount stale udev filesystem type after in-place reformat

## TL;DR

Current util-linux issue `#4527` reports a 2.42.2 regression: after an ext3 filesystem is reformatted in place as ext4, `blkid` sees ext4 but automatic `mount` still asks the kernel to mount it as ext3. Current util-linux `d26ad4d8c2f0b25c97cc860ea8b2059e65f54c5e` still prefers udev tag data and returns before direct blkid probing.

The strongest candidate is not to discard the udev optimization globally. Instead, remember when the filesystem type was auto-guessed. If the type-specific mount syscall fails, directly probe the source; retry only when the direct type differs from the guessed type. Explicit `-t` and fstab types remain authoritative.

A live loop-device reproducer is running before this candidate is promoted.

## Why care

The filesystem on disk can be valid and correctly identified by blkid while `mount /dev/device /mnt` fails because a cached `ID_FS_TYPE` was stale. This is a correctness regression at the boundary between udev metadata and direct device state.

Literal sequence:

```text
ext3 on disk -> udev ID_FS_TYPE=ext3
mkfs.ext4 rewrites the same block device
blkid TYPE=ext4
udev database still says ext3
libmount promotes ext3 to the one authoritative type
mount(2, type=ext3) -> EINVAL
```

## Exact public source

- issue: `util-linux/util-linux#4527`
- current source reviewed: `d26ad4d8c2f0b25c97cc860ea8b2059e65f54c5e`
- reported good release: util-linux 2.41.3
- reported bad release: util-linux/libmount 2.42.2
- introducing direction: commit `8bdc2546d38979ca65fa9bfd1bbd6e7b985c69db`, which made libmount read tags from the udev database first and use direct blkid only as fallback

## Current source mechanism

`libmount/src/cache.c` maps udev `ID_FS_TYPE` to libmount `TYPE`.

`mnt_cache_read_tags()` returns successfully after a successful udev read, so direct blkid is not consulted. `mnt_get_fstype(dev, ..., cache)` therefore returns the cached `TYPE`.

`mnt_context_guess_fstype()` installs that value into `cxt->fs` when the caller did not explicitly provide a filesystem type.

`mnt_context_do_mount()` behaves differently depending on that field:

- one type present: try only that type;
- no type present: use the existing filesystem-pattern retry path.

So the regression is not merely "udev can be stale." It is that a stale external hint is promoted into the one authoritative mount type with no recovery path.

## udev freshness boundary

Current systemd-udevd can synthesize a `change` event on `IN_CLOSE_WRITE`, but only for devices that have an inotify watch enabled. `UdevEvent.inotify_watch` initializes false and the worker adds the watch only when rules request it. The current persistent-storage rule imports blkid properties but does not itself request `OPTIONS+="watch"`.

Therefore libmount cannot generally assume every writer close causes `ID_FS_TYPE` to be refreshed.

`udevadm settle` only waits for already queued events. The runtime experiment explicitly tests whether settle without a new event changes the stale database.

## Runtime discriminator

The isolated workflow uses one loop device:

1. create ext3;
2. emit a change event and settle; require udev `ID_FS_TYPE=ext3`;
3. rewrite the same device as ext4;
4. require direct `blkid TYPE=ext4`;
5. inspect udev immediately;
6. run `udevadm settle` without emitting an event and inspect again;
7. run current built `mount` with no `-t`;
8. run explicit `mount -t ext4` as a positive control;
9. explicitly emit a change event, settle, require udev `TYPE=ext4`;
10. require automatic mount to succeed after that refresh.

The result distinguishes stale metadata from a generic ext4 or mount failure and directly answers the maintainer's `udevadm settle` question.

## Candidate design

See `retry-guessed-fstype.patch`.

### State

Add a private context bit indicating that the current single filesystem type came from `mnt_context_guess_fstype()` rather than an explicit type.

### Failure path

After `do_mount(cxt, NULL)` returns a positive mount-syscall error for a guessed single type:

1. obtain the prepared source path;
2. call `mnt_get_fstype(src, ..., NULL)` so the cache/udev optimization is bypassed;
3. if direct probing returns the same type, preserve the original failure;
4. if direct probing returns a different type, retry with existing `do_mount(cxt, direct_type)` machinery.

A conservative first version can limit the direct recheck to `EINVAL`, which is the reported ext3-on-ext4 failure.

## Why this candidate is preferable to the obvious alternatives

### Always ignore udev TYPE

Correct but gives up the new no-probe fast path on every auto-type mount.

### Always probe TYPE even when udev has it

Also correct, but similarly makes the optimization ineffective for the most common mount-type lookup.

### Require mkfs/udev to emit a change event

Useful ecosystem hygiene, but libmount cannot rely on every block-device writer, filesystem tool, rescue environment, container, or udev ruleset providing that event.

### Retry every available filesystem after failure

Broader than needed. A direct probe gives a specific new type and avoids trial mounting unrelated filesystems.

## Cross-context controls

- explicit `mount -t ext3` against ext4 must still fail as requested; do not override user intent;
- correct udev guess must mount without direct reprobe;
- guessed type with genuine corruption and matching direct probe must preserve the first failure;
- no detectable filesystem type must keep the existing `/etc/filesystems`/`/proc/filesystems` fallback;
- stale ext3 -> ext4 should retry ext4 only after the ext3 failure;
- stale ext3 -> ext2 should behave analogously if direct blkid reports ext2;
- udev-disabled builds must remain behaviorally compatible; their direct guess should simply compare equal on a failure.

## Evidence boundary

The source mechanism and udev watch contract are demonstrated. The loop-device current-head reproduction and candidate execution are separate gates and must not be claimed until their hosted receipts complete.

## Authority

No util-linux issue comment, pull request, review, email, or other canonical upstream interaction has been made.