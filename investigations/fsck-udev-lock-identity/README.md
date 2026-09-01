# fsck and udev lock identity

## State

`ACTIVE`

## Question

Does current util-linux `fsck -l` exclude a udev-equivalent shared BSD lock on the whole block device, or do the two mechanisms operate on independent lock objects?

This is the first executable discriminator for Linux Fieldwork issue `#232`. It does not yet reproduce ext4 UUID loss or systemd device-unit cancellation.

## Current source map

Pinned source inspected during pickup:

```text
util-linux: fd82c4043fab942b889f478800118c66edfbc39f
systemd:    70a180a49088a28f9e0b4632f86ea3ac3e57a9e7
```

Current util-linux `disk-utils/fsck.c`:

- resolves the whole disk;
- skips locking for absent or non-rotating disks;
- opens `/run/fsck/<diskname>.lock`;
- takes `flock(LOCK_EX)` on that regular file;
- documents the descriptor as a flocked lockpath, not the device node.

Current systemd:

- documents a whole-device BSD-lock protocol for superblock writers, explicitly including fsck;
- udev workers open the whole-disk node and attempt `flock(LOCK_SH|LOCK_NB)`;
- a conflicting exclusive lock causes the event to be requeued;
- `systemd-fsck` still passes util-linux `fsck -l` and comments that pre-2.25 device locking conflicted with udevd;
- `systemd-fsck@.service` binds to the exact device unit and runs after it appears.

External util-linux issue `#4477` remains open. The maintainer states `fsck -l` coordinates parallel fsck instances and assigns simultaneous fsck/udev scheduling ownership to the init/device manager.

## Probe

```text
scripts/probe-fsck-udev-lock-identity.sh
```

The disposable probe:

1. attaches a temporary image to a loop device;
2. overlays only the container mount namespace's `queue/rotational` view with `1`, because current `fsck -l` intentionally skips non-rotating devices;
3. supplies a fake `fsck.ext4` first in `PATH` and blocks it after launch;
4. runs current `fsck -l` against the loop device;
5. requires `/run/fsck/<loop>.lock` to exist and be held exclusively;
6. attempts a nonblocking shared flock on the whole loop device while fsck is active;
7. releases fsck;
8. holds an exclusive flock on the whole loop device;
9. requires the same shared probe to fail;
10. records file identities, kernel locks, versions, statuses, mount override, checker identity, and cleanup.

Expected distinguishing result:

```text
private /run/fsck shared probe: nonzero
whole-device shared probe during fsck -l: zero
whole-device shared probe during whole-device LOCK_EX: nonzero
```

That result proves lock-domain independence and validates the documented device-node control. It does not prove the reported metadata race.

## Attempt 1 — checker-dispatch and rotational preflight

```text
PR: 413
head: 5045f2fba8b68f389d453fd26cd347eaf52b489a
workflow: 30705124327
job: 91382810762
artifact: 8820074565
artifact digest: sha256:7e4506082d11087eee2f6326c5dfb4bf9ad590870a8323d6da0446f02743c1ce
classification: carrier-preflight-failure
product claim: zero
```

The static carrier tests passed. The container reported:

```text
Loop sysfs rotational: 0
e2fsck: need terminal for interactive repairs
fsck front-end exited before holding the checker and lock file
```

Two preconditions were wrong:

- `FSCK_PATH` did not override util-linux's checker search; the real `e2fsck` ran;
- even with correct checker dispatch, `fsck -l` would skip a loop device whose queue reports `rotational=0`.

Repair:

- prepend the fake checker directory to `PATH`;
- bind a regular file containing `1` over the loop queue's rotational attribute inside the disposable container mount namespace;
- record original/effective values and the bind mount;
- unmount the override before detaching the loop device;
- require the fake checker executable and argv receipts.

## Next gate

Rerun the exact repaired carrier. After a positive identity result, add a synchronized real ext4 fixture:

- stable UUID on a loop-backed partition;
- controlled e2fsck final-superblock write window;
- udev add/change retrigger during that window;
- captured blkid output, udev database and by-uuid symlink state;
- systemd device and fsck service state;
- whole-device `LOCK_EX` negative control;
- deadlock control where udev holds `LOCK_SH` before the fsck owner requests exclusivity;
- cleanup and immediate rerun.

## Boundaries

Do not repurpose util-linux `fsck -l` without resolving its long-standing public semantics and the historical deadlock. A plausible future owner is the systemd fsck wrapper or device lifecycle, but no source correction is selected yet.

No external upstream contact is authorized or included.
