# GNU `install` 9.7 ownership receipt

## Boundary

- Reference binary: `/usr/bin/install`
- Reported version: `install (GNU coreutils) 9.7`
- Execution date: 2026-08-03
- Environment: disposable local temporary directories on Linux
- Locale: `LC_ALL=C`
- Cleanup: temporary root removed on shell exit

No GNU source was read for these conclusions. This receipt records behavior only.

## Matrix

| Case | Exit | Final destination | Backup/result | Diagnostic summary | Ownership conclusion |
|---|---:|---|---|---|---|
| ordinary repeated basename | 1 | first source | none | refuses second overwrite | first completed copy owns name |
| simple backup with original destination | 1 | first source | `file~` remains original | refuses second overwrite | refusal preserves pre-command backup |
| numbered backup | 0 | second source | `.~1~` original; `.~2~` first | none | numbered mode permits reuse |
| `--compare` true no-op first | 0 | second source | none | none | no-op does not own name |
| missing first source | 1 | second source | none | cannot stat missing source | pre-copy failure does not own name |
| first source read error after destination creation | 1 | second source | none | input/output error | incomplete `copy_file` does not own name |
| first copy completes, chown fails | 1 | first source | none | ownership error, then just-created refusal | post-copy failure leaving file keeps ownership |
| strip fails and removes destination | 1 | absent | strip helper invoked twice | two strip failures | removed destination releases name |

## Compact observed output

```text
install (GNU coreutils) 9.7
default status=1 dest=first stderr=install: will not overwrite just-created 'dest/file' with 's2/file'
simple status=1 dest=first backup=original stderr=install: will not overwrite just-created 'dest/file' with 's2/file'
numbered status=0 dest=second b1=original b2=first stderr=''
compare status=0 dest=second stderr=''
missing status=1 dest=second stderr=install: cannot stat 'missing/file': No such file or directory
read-error status=1 dest=second stderr=install: error reading 's1/mem': Input/output error
chown status=1 dest=first stderr=<ownership error, then just-created refusal>
strip status=1 dest_exists=no calls=2 stderr_lines=2
```

## Fixtures

The read-error case used `source1/mem -> /proc/self/mem` and a regular `source2/mem`. GNU created or opened the first destination, encountered `EIO` while reading, then allowed the second source to install. This distinguishes file creation from completed data-copy ownership.

The chown case ran GNU `install` as `nobody` with `--owner=root`. The first data copy completed, ownership change failed, and GNU then refused the second same-name source. This distinguishes completed copy from successful post-copy finalization.

The strip helper appended each argument to `strip.log`, returned 1, and caused GNU to remove the destination. Two log entries prove the later same-name source was attempted after the first destination was removed.

## Interpretation

The distinguishing transition is successful completion of the data-copy operation. Ownership does not begin on a compare no-op, stat failure, or copy/read failure. It begins before post-copy ownership and metadata work, and remains while the created directory entry remains. Numbered backups override the refusal policy.

## Limits

This receipt does not establish behavior on non-Linux systems, SELinux-enabled finalization, write-side ENOSPC failures, or GNU versions other than 9.7. It does not claim implementation intent beyond the observed behavior.
