# libmount stale udev filesystem type after in-place reformat

## TL;DR

Current util-linux issue `#4527` reports a 2.42.2 regression: after an ext3 filesystem is reformatted in place as ext4, `blkid` sees ext4 but automatic `mount` still asks the kernel to mount it as ext3. Current util-linux `d26ad4d8c2f0b25c97cc860ea8b2059e65f54c5e` still prefers udev tag data and returns before direct blkid probing.

Current systemd does enable `OPTIONS+="watch"` for ordinary block devices in `60-block.rules`, so the strongest model is an asynchronous freshness race: mkfs closes the block device, udev is expected to synthesize and process a change event, but a mount started before that refresh can still consume the old `ID_FS_TYPE`.

The leading libmount candidate does not discard the udev optimization globally. Instead, remember when the filesystem type was auto-guessed. If the type-specific mount syscall fails with `EINVAL`, directly probe the source; retry only when the direct type differs from the guessed type. Explicit `-t` and fstab types remain authoritative.

A live loop-device reproducer is running before this candidate is promoted.

## Why care

The filesystem on disk can be valid and correctly identified by blkid while `mount /dev/device /mnt` fails because a udev `ID_FS_TYPE` hint has not caught up yet. This is a correctness regression at the boundary between asynchronous device metadata and direct device state.

Literal race:

```text
udev ID_FS_TYPE=ext3
mkfs.ext4 rewrites and closes the block device
udev close-write/change processing is asynchronous
mount starts before refreshed ID_FS_TYPE is committed
libmount reads ext3 from udev and promotes it to the one type
mount(2, type=ext3) -> EINVAL
```

## Exact public source

- issue: `util-linux/util-linux#4527`
- current source reviewed: `d26ad4d8c2f0b25c97cc860ea8b2059e65f54c5e`
- reported good release: util-linux 2.41.3
- reported bad release: util-linux/libmount 2.42.2
- introducing direction: commit `8bdc2546d38979ca65fa9bfd1bbd6e7b985c69db`, which made libmount read tags from the udev database first and use direct blkid only as fallback

## Current libmount mechanism

`libmount/src/cache.c` maps udev `ID_FS_TYPE` to libmount `TYPE`.

`mnt_cache_read_tags()` returns successfully after a successful udev read, so direct blkid is not consulted. `mnt_get_fstype(dev, ..., cache)` therefore returns the cached `TYPE`.

`mnt_context_guess_fstype()` installs that value into `cxt->fs` when the caller did not explicitly provide a filesystem type.

`mnt_context_do_mount()` behaves differently depending on that field:

- one type present: try only that type;
- no type present: use the existing filesystem-pattern retry path.

So the regression is not merely "udev can be stale." It is that an asynchronous external hint is promoted into the one authoritative mount type with no recovery path.

## udev freshness boundary

Current systemd's `60-block.rules` enables `OPTIONS+="watch"` for normal loop, NVMe, SCSI, virtio, and other block devices. `systemd-udevd` responds to `IN_CLOSE_WRITE` on watched devices by synthesizing a change event, which causes persistent-storage blkid rules to refresh `ID_FS_*` properties.

This means the expected healthy steady state is fresh udev metadata. It does **not** make the database synchronously fresh at the instant a writer closes. The close notification, synthesized event, worker execution, blkid probe, and database update are separate asynchronous steps.

`udevadm settle` is therefore an important discriminator. The runtime experiment now measures three points separately:

1. automatic mount immediately after `mkfs.ext4`;
2. automatic mount after `udevadm settle` but without an explicit trigger;
3. automatic mount after an explicit change event plus settle.

Possible outcomes distinguish a race that settle closes from an event that was never observed or from an environment where udev refreshes before mount can race it.

## Runtime discriminator

The isolated workflow uses one loop device:

1. create ext3;
2. emit a change event and settle; require udev `ID_FS_TYPE=ext3`;
3. rewrite the same device as ext4;
4. require direct `blkid TYPE=ext4`;
5. inspect udev immediately;
6. attempt automatic mount immediately;
7. run explicit `mount -t ext4` as a positive filesystem control;
8. run `udevadm settle` without emitting another event;
9. inspect udev and retry automatic mount;
10. explicitly emit a change event, settle, require udev `TYPE=ext4`, and require automatic mount success.

Classifications:

- `CONFIRMED_RACE_SETTLE_REFRESHES`: immediate stale ext3 causes mount failure, settle advances udev to ext4 and mount succeeds;
- `STALE_PERSISTS_UNTIL_EXPLICIT_CHANGE`: settle alone leaves ext3, while an explicit change refreshes it;
- `UDEV_REFRESHED_BEFORE_IMMEDIATE_MOUNT`: this runner cannot hit the race because udev has already advanced to ext4.

## Candidate design

See `retry-guessed-fstype.patch`.

### State

Add a private context bit indicating that the current single filesystem type came from `mnt_context_guess_fstype()` rather than an explicit type. Explicit `mnt_context_set_fstype()` clears this provenance bit.

### Failure path

After `do_mount(cxt, NULL)` returns `EINVAL` for a guessed single type:

1. obtain the prepared source path;
2. call `mnt_get_fstype(src, ..., NULL)` so the cache/udev optimization is bypassed;
3. if direct probing returns the same type, preserve the original failure;
4. if direct probing returns a different type, retry with existing `do_mount(cxt, direct_type)` machinery.

This is deliberately failure-only: a correct udev guess does not pay for a direct probe.

## Why this candidate is preferable to the obvious alternatives

### Always ignore udev TYPE

Correct but gives up the new no-probe fast path on every auto-type mount.

### Always probe TYPE even when udev has it

Also correct, but similarly makes the optimization ineffective for the common success path.

### Require callers to settle udev

Useful operationally if the runtime confirms it closes the race, but `mount` historically did not require callers to synchronize an external metadata database after rewriting a filesystem. The library can recover cheaply after its guessed type is rejected.

### Retry every available filesystem after failure

Broader than needed. A direct probe gives a specific new type and avoids trial mounting unrelated filesystems.

## Permanent regression home

`tests/ts/libmount/context` is already the right upstream test surface. It provisions a real SCSI-debug block device, formats filesystems, interacts with udev, and mounts through the libmount context helper.

A deterministic regression should arrange for udev's ext4 refresh to be delayed while the ext3 database entry remains visible, then verify:

- auto-guessed stale ext3 recovers to direct-probed ext4;
- explicit `-t ext3` still fails;
- after udev refresh, the normal fast path succeeds.

Avoid a permanently timing-dependent test if a controlled udev queue or equivalent fixture can hold the stale state safely.

## Cross-context controls

- explicit `mount -t ext3` against ext4 must still fail as requested; do not override user intent;
- correct udev guess must mount without direct reprobe;
- guessed type with genuine corruption and matching direct probe must preserve the first failure;
- no detectable filesystem type must keep the existing `/etc/filesystems`/`/proc/filesystems` fallback;
- stale ext3 -> ext4 should retry ext4 only after the ext3 failure;
- stale ext3 -> ext2 should behave analogously if direct blkid reports ext2;
- udev-disabled builds must remain behaviorally compatible; their direct guess should normally compare equal on a failure;
- an explicit type set after earlier preparation must clear guessed-type provenance so later failure does not override caller intent.

## Evidence boundary

The libmount source mechanism, the global block-device watch rule, and the asynchronous udev update path are demonstrated. The loop-device current-head reproduction and candidate execution are separate gates and must not be claimed until their hosted receipts complete.

## Authority

No util-linux issue comment, pull request, review, email, or other canonical upstream interaction has been made.