# GNU `install` 9.7 backup-rollback receipt

## Boundary

- Binary: `/usr/bin/install`
- Version: `install (GNU coreutils) 9.7`
- Date: 2026-08-03
- Locale: `LC_ALL=C`
- Environment: disposable local Linux temporary directories
- Error fixture: source symlink to `/proc/self/mem`

No GNU source was read for these conclusions.

## Data-copy failure matrix

| Backup mode | Initial state | Exit | Final destination | Remaining backup state |
|---|---|---:|---|---|
| none | `dest/file=original` | 1 | zero-length partial destination | none |
| simple | `dest/file=original` | 1 | `original` restored | no `file~` |
| existing | `dest/file=original` | 1 | `original` restored | no backup |
| numbered | `dest/file=original` | 1 | `original` restored | no new numbered backup |
| existing, seeded | `dest/file=original`, `file.~1~=older` | 1 | `original` restored | `file.~1~` remains `older`; no `file.~2~` |
| simple, old backup present | `dest/file=current`, `file~=olderbackup` | 1 | `current` restored | old `file~` removed |

All cases reported:

```text
install: error reading 'source/file': Input/output error
```

## Multi-source interaction

Setup:

```sh
source1/file -> /proc/self/mem
source2/file = second
dest/file = original
install --backup=simple -t dest source1/file source2/file
```

Observed:

```text
status=1
dest/file=second
dest/file~=original
stderr=install: error reading 'source1/file': Input/output error
```

The failed first data copy does not reserve the destination. The destination is first restored, then the later source installs and backs up the restored original.

## Finalization negative control

Setup uses a strip helper that logs its argument and exits 1, with `dest/file=original` and two regular sources.

Observed under `--backup=simple --strip`:

```text
status=1
dest/file absent
dest/file~=original
strip helper calls=2
stderr lines=2
```

GNU does not roll the original destination back after strip failure. It keeps the original at the backup path, removes each failed installed destination, and attempts the later source.

## Interpretation

Rollback belongs strictly between successful backup rename and failed data-copy completion. It does not apply when no backup path exists, and it does not apply after the data copy has completed and finalization has begun.

## Limits

The fixture demonstrates a source read error. It does not independently demonstrate destination write errors such as ENOSPC, restore failure, dangling-symlink destinations, non-Linux behavior, SELinux, or an empty backup suffix.
