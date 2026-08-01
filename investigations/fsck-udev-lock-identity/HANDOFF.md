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
```

## Completed

- confirmed current util-linux `fsck -l` flocks `/run/fsck/<disk>.lock`;
- confirmed current systemd-udevd flocks the whole-disk device node with `LOCK_SH|LOCK_NB`;
- confirmed systemd documentation recommends whole-device `LOCK_EX` for fsck and other superblock writers;
- confirmed `systemd-fsck` still invokes `fsck -l` because older device-node locking historically conflicted with udevd;
- created an exact disposable loop-device lock-domain probe;
- added static assertions and a same-repository privileged CI workflow;
- preserved cleanup for loop attachment, background processes, lock file, and temporary source.

## First incomplete step

Run the branch through CI and classify:

```text
private /run/fsck shared probe must fail
whole-device shared probe while fsck -l is active must succeed
whole-device shared probe while whole-device LOCK_EX is held must fail
```

If all three hold, record exact kernel/util-linux/systemd versions, loop identity, statuses, artifact ID/digest, and cleanup. Then build the synchronized real-ext4/udev fixture described in `README.md`.

If `fsck -l` skips locking because the loop device is non-rotating, adapt the disposable carrier to a virtual SCSI disk or a controlled rotational sysfs fixture; do not weaken the positive control.

## Claim boundary

A positive run proves only that the two lock schemes are independent. It does not prove UUID corruption, symlink removal, systemd unit cancellation, or final source ownership.

## Authority

Internal Linux Fieldwork work only. No util-linux, systemd, kernel, distribution, or reporter contact is authorized or included.
