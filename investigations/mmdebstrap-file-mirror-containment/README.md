# file-mirror-automount target containment

## In simple words

The `file-mirror-automount` hook turns local APT repository and package-file paths into destinations below a generated root. The imported setup hook concatenates those paths directly, and the cleanup hook later trusts the same marker text. Parent traversal or an existing symlink below the generated root can therefore redirect setup or cleanup outside that root.

This candidate canonicalizes sources, keeps safe configured repository spellings reachable inside the generated root, resolves every generated destination, requires the destination to remain below the canonical root, and records only canonical root-relative marker entries. Cleanup validates the complete marker stream before any action, then repeats validation while acting on each entry.

## Canonical records

- issue: #164
- pull request: #179
- setup source: `upstream/mmdebstrap/hooks/file-mirror-automount/setup00.sh`
- setup imported blob: `6ccbdaf2ba97c77c4e5223ac5280acd51a998424`
- cleanup source: `upstream/mmdebstrap/hooks/file-mirror-automount/customize00.sh`
- cleanup imported blob: `b6b9b46afdd9dad01df3abcb514475326162e42c`
- containment patch: `0001-contain-file-mirror-targets.patch`
- URI-path compatibility patch: `0002-preserve-file-uri-target-path.patch`
- parent-component reachability patch: `0003-reject-parent-uri-components.patch`
- containment regression: `tests/test_file_mirror_automount_containment.py`
- generated-root regression: `tests/test_file_mirror_automount_root_guard.py`
- cleanup preflight regression: `tests/test_file_mirror_automount_cleanup_preflight.py`
- source-normalization regression: `tests/test_file_mirror_automount_source_normalization.py`
- parent-component differential: `tests/test_file_mirror_automount_parent_component_reachability.py`
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

1. canonicalizes the generated root with `realpath -e` and refuses `/`;
2. rejects empty, absolute-after-prefix, leading-parent, and embedded-parent repository spellings;
3. canonicalizes each existing host source;
4. normalizes accepted configured repository URI paths with GNU `realpath -m -s`, preserving terminal source-symlink spelling while removing harmless lexical `.` and repeated-separator components;
5. derives repository destinations from that normalized URI path, while local package destinations retain the existing canonical-source mapping;
6. resolves the generated destination with `realpath -m` so existing target symlinks are visible;
7. requires the destination to be a strict descendant of the generated root;
8. uses the canonical host source and contained generated destination for bind/copy operations;
9. records only the contained relative destination without a leading slash or parent component.

Separating source and destination identities preserves a terminal symlink configured in APT. For `file:///tmp/repository-link` where the host link resolves to `/srv/repository`, the bind source is `/srv/repository`, while the generated destination and marker remain `tmp/repository-link`. APT inside the generated root can still open the configured URI path.

A parent component cannot be handled by lexical normalization alone. For `file:///sources/spelling/../repository`, the two-patch predecessor created only `/sources/repository` below the generated root. The configured path still had to resolve `/sources/spelling` before `..`, so it remained unreachable. The final candidate rejects every `..` component before mount, copy, or marker creation. A harmless `.` component remains accepted because its retained parent is created and the configured path stays reachable.

The cleanup hook canonicalizes the root, refuses `/`, and treats the marker as untrusted persisted input. Its first NUL-delimited pass validates every entry and current target without invoking `umount` or `rm -r`. Only after that complete preflight succeeds does a second pass repeat lexical and canonical containment checks immediately before each cleanup action. Any rejected entry leaves the marker present for diagnosis.

The complete preflight prevents a valid early entry from being removed or unmounted when a later entry is invalid. Action failures can still leave partial cleanup; the retained marker and command diagnostics expose that ordinary operational boundary.

## Executable regression

The disposable regressions use fake `apt-get`, `mount`, `umount`, and destructive `rm -r` commands. They perform no real mount or package operation. They require:

- the imported baseline to derive an out-of-root target from `file:///../../etc`;
- the candidate to reject leading and embedded parent components before target creation, mount, copy, or marker write;
- the two-patch predecessor to demonstrate the embedded-parent reachability failure;
- a harmless dot component to normalize to a reachable configured path, contained target, and canonical marker;
- a valid local repository to map below the root and create one canonical relative marker entry;
- a symlinked repository URI to use the canonical host source while preserving the configured URI path as target and marker;
- cleanup of that symlinked URI target followed by an immediate successful rerun;
- an existing target-parent symlink that resolves outside the root to be rejected before mount;
- a local package file to use the same contained target contract;
- valid cleanup to pass one canonical contained target to the selected action and remove the marker;
- literal `/` and a symlink resolving to `/` to fail before repository or marker processing;
- a valid marker followed by traversal, absolute, doubled-separator, dot, trailing-separator, or symlink-escaping entries to cause zero cleanup actions;
- the rejected marker and target to remain available for diagnosis;
- immediate rerun with a corrected marker to succeed in root and non-root modes;
- all retained patches to apply exactly to temporary source copies;
- both candidate scripts to pass POSIX shell syntax validation.

## Evidence boundary

The candidate closes the demonstrated lexical traversal, pre-existing target-symlink, generated-root `/`, static mixed-marker partial-cleanup, terminal source-symlink reachability, and parent-component reachability paths under GNU `realpath` and GNU `xargs` on Linux. It uses pathname validation followed by pathname operations; a process able to replace components or marker contents between validation and action remains outside this candidate. Descriptor-relative or mount-namespace-specific hardening would be a separate investigation.

The executable matrix exercises root-mode bind and unmount command construction with fake commands. The non-root helper calls share the same resolved destination helper and receive source/destination arguments checked by source assertions; a real hook-socket transfer is outside this focused regression.

The setup and cleanup candidates are intended to run as one set. The cleanup candidate rejects the older leading-slash marker format instead of accepting ambiguous historical state during an active run.

## Cleanup and authority

All files and symlinks live below `TemporaryDirectory`. The only real filesystem operations are disposable directory, file, and symlink creation. No real mount, unmount, package mutation, external network, privilege expansion, or upstream contact occurs.

## Disposition

The three-patch candidate carries setup containment, complete cleanup preflight, generated-root refusal, safe URI-path preservation, parent-component rejection, and terminal-symlink reachability as one contract. Exact-head CI and complete-diff review are the acceptance gates. No Debian or external upstream issue, patch, email, merge request, comment, or review is authorized or created by this record.
