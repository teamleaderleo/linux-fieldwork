# file-mirror-automount target containment

## In simple words

The `file-mirror-automount` hook turns local APT repository and package-file paths into destinations below a generated root. The imported setup hook concatenates those paths directly, and the cleanup hook later trusts the same marker text. Parent traversal or an existing symlink below the generated root can therefore redirect setup or cleanup outside that root.

This candidate canonicalizes sources, resolves every generated destination, requires the destination to remain below the canonical root, and records only canonical root-relative marker entries. Cleanup repeats the validation before unmounting or removing anything.

## Canonical records

- issue: #164
- setup source: `upstream/mmdebstrap/hooks/file-mirror-automount/setup00.sh`
- setup imported blob: `6ccbdaf2ba97c77c4e5223ac5280acd51a998424`
- cleanup source: `upstream/mmdebstrap/hooks/file-mirror-automount/customize00.sh`
- cleanup imported blob: `b6b9b46afdd9dad01df3abcb514475326162e42c`
- candidate patch: `0001-contain-file-mirror-targets.patch`
- regression: `tests/test_file_mirror_automount_containment.py`
- reusable note: `notes/filesystems/cleanup-markers-must-carry-contained-relative-paths.md`

## Source boundary

The setup hook strips the `file:` prefix and leading slashes, then uses the remaining text in both source and target paths:

```sh
mkdir -p "$rootdir/$path"
mount -o ro,bind "/$path" "$rootdir/$path"
printf '/%s\0' "$path" >> "$rootdir/run/mmdebstrap/file-mirror-automount"
```

For `file:///../../etc`, the source resolves to `/etc` while the target resolves outside the generated root. The marker retains the traversing spelling. The cleanup hook later runs `umount "$rootdir/{}"` or `rm -r "$rootdir/{}"` from that marker.

Local package files use a canonical source path, but their target also relies on direct string concatenation and can follow an existing target-parent symlink outside the root.

## Candidate

The setup hook now:

1. canonicalizes the generated root with `realpath -e`;
2. rejects empty, absolute, doubled-separator, dot, and parent repository components before source access;
3. canonicalizes each existing source;
4. derives a root-relative destination from the canonical absolute source;
5. resolves the destination with `realpath -m` so existing target symlinks are visible;
6. requires the destination to be a strict descendant of the generated root;
7. uses the canonical source and destination for bind/copy operations;
8. records only the canonical relative destination without a leading slash or `..` component.

The same destination helper is used for local package files.

The cleanup hook canonicalizes the root, rejects absolute, trailing-separator, doubled-separator, dot, and parent marker entries, resolves each target, requires it to remain below the root, and only then calls `umount` or `rm -r`. A rejected marker leaves the marker file present for diagnosis.

## Executable regression

The disposable regression uses fake `apt-get`, `mount`, and `umount` commands. It performs no real mount or package operation. It requires:

- the imported baseline to derive an out-of-root target from `file:///../../etc`;
- the candidate to reject that input before target creation, mount, or marker write;
- a valid local repository to map below the root and create one canonical relative marker entry;
- an existing target-parent symlink that resolves outside the root to be rejected before mount;
- a local package file to use the same contained target contract;
- valid cleanup to pass one canonical contained target to `umount` and remove the marker;
- traversing and symlink-escaping marker entries to fail before cleanup action and retain the marker;
- the candidate scripts to retain the defining canonicalization and cleanup checks.

Both candidate scripts also pass POSIX shell syntax validation and ShellCheck in the local review environment.

## Evidence boundary

The candidate closes the demonstrated lexical traversal and pre-existing target-symlink paths under GNU `realpath` on Linux. It uses pathname validation followed by pathname operations; a process able to replace components between validation and mount/copy/cleanup remains outside this candidate. Descriptor-relative or mount-namespace-specific hardening would be a separate investigation.

The executable matrix exercises root-mode bind and unmount command construction with fake commands. The non-root helper calls share the same resolved destination helper and receive source/destination arguments checked by source assertions; a real hook-socket transfer is outside this focused regression.

The setup and cleanup candidates are intended to run as one pair. The cleanup candidate rejects the older leading-slash marker format instead of accepting ambiguous historical state during an active run.

## Cleanup and authority

All files and symlinks live below `TemporaryDirectory`. The only real filesystem operations are disposable directory, file, and symlink creation. No real mount, unmount, package mutation, external network, privilege expansion, or upstream contact occurs.

## Disposition

Retain the candidate and regression for internal review. No Debian or external upstream issue, patch, email, merge request, comment, or review is authorized or created by this record.
