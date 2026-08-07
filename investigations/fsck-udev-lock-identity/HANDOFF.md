# Handoff

## State

`ACTIVE`

## Branch

```text
investigation/fsck-udev-lock-identity
```

## Source identities

```text
util-linux source inspected: fd82c4043fab942b889f478800118c66edfbc39f
systemd source inspected: 70a180a49088a28f9e0b4632f86ea3ac3e57a9e7
external report: util-linux issue 4477
Linux Fieldwork owner: issue 232
internal execution PR: 413
```

## Completed

- confirmed current util-linux `fsck -l` flocks `/run/fsck/<disk>.lock`;
- confirmed current systemd-udevd flocks the whole-disk device node with `LOCK_SH|LOCK_NB`;
- confirmed systemd documentation recommends whole-device `LOCK_EX` for fsck and other superblock writers;
- confirmed `systemd-fsck` still invokes `fsck -l` because older device-node locking historically conflicted with udevd;
- created an exact disposable loop-device lock-domain probe;
- added static assertions and a same-repository privileged CI workflow;
- preserved cleanup for loop attachment, background processes, lock file, rotational bind override, and temporary source.

## Attempt 1

```text
head: 5045f2fba8b68f389d453fd26cd347eaf52b489a
workflow: 30705124327
job: 91382810762
artifact: 8820074565
digest: sha256:7e4506082d11087eee2f6326c5dfb4bf9ad590870a8323d6da0446f02743c1ce
classification: carrier-preflight-failure
```

Static tests passed. Dynamic evidence showed:

```text
kernel: 6.17.0-1020-azure
util-linux: 2.42.2
loop device: /dev/loop0
rotational: 0
stderr: e2fsck: need terminal for interactive repairs
```

`FSCK_PATH` did not override checker lookup, so the real checker ran. The loop's non-rotating queue would also make current `fsck -l` skip locking. No lock-domain or product claim is attached to this run.

## Repair committed

- fake `fsck.ext4` is selected by prepending its directory to `PATH`;
- a file containing `1` is bind-mounted over the loop queue's rotational attribute only in the container mount namespace;
- original/effective rotational values and mount identity are retained;
- fake checker executable and argv are retained;
- the override is unmounted before loop detach;
- regressions require these exact preconditions.

## First incomplete step

Run the repaired branch head through PR `#413` and classify:

```text
private /run/fsck shared probe must fail
whole-device shared probe while fsck -l is active must succeed
whole-device shared probe while whole-device LOCK_EX is held must fail
```

If all three hold, record exact head, run, artifact ID/digest, lock inode/device identities, statuses, and cleanup. Then build the synchronized real-ext4/udev fixture described in `README.md`.

If the private sysfs bind mount is unavailable, return neutral status and move to a disposable virtual SCSI device; do not weaken the positive control or manually substitute a private lock for current `fsck -l` execution.

## Kernel note

Current mainline `fs/locks.c` stores BSD lock state in the inode's file-lock context. A regular file under `/run/fsck` and a block-device inode are expected to be distinct lock objects. The executable probe is still required to tie that VFS semantic to current util-linux and systemd contracts. This is not presently a kernel-fix claim.

## Claim boundary

A positive run proves only that the two lock schemes are independent. It does not prove UUID corruption, symlink removal, systemd unit cancellation, or final source ownership.

## Authority

Internal Linux Fieldwork work only. No util-linux, systemd, kernel, distribution, or reporter contact is authorized or included.
