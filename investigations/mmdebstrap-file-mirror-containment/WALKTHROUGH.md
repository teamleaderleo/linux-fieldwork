# file-mirror-automount code walkthrough

## TL;DR

This investigation changes two POSIX shell scripts:

- `setup00.sh` places selected host repositories and package files inside an mmdebstrap-generated root;
- `customize00.sh` later removes or unmounts exactly the destinations that setup recorded.

The central rule is simple:

> Resolve the real paths first, prove the destination is a strict child of the generated root, then act.

The final candidate also separates two names that can legitimately differ:

- the **canonical host source** used by `mount` or the copy helper;
- the **configured URI destination** that APT expects to find inside the generated root.

Cleanup reads NUL-delimited marker entries in two passes. The first pass validates the complete list without deleting or unmounting anything. The second pass validates each entry again immediately before the action.

## What language is this?

The hook files are POSIX shell scripts. They run commands and join those commands with shell control flow.

A few pieces of syntax appear repeatedly:

- `name=value` assigns a variable.
- `"$name"` expands a variable while preserving spaces and wildcard characters as ordinary data.
- `$(command)` runs a command and captures its output.
- `case value in pattern) ... ;; esac` selects behavior by pattern.
- `command || return 1` reports failure from a helper function when the command fails.
- `if ! command; then ... fi` runs the body when the command fails.
- `a | b | c` sends the output of one command into the next.
- `set -e` stops after an unhandled command failure.
- `set -u` stops when an unset variable is used.
- `\0` is a NUL byte. It lets the marker safely separate pathnames containing spaces or newlines.

The scripts depend on GNU utilities such as `realpath` and `xargs` in addition to ordinary shell behavior.

## The lifecycle

```text
APT repository configuration / included package paths
                    |
                    v
              setup00.sh
       validate -> mount/copy/upload
                    |
                    v
       NUL-delimited cleanup marker
                    |
                    v
            customize00.sh
       preflight all -> recheck -> act
```

`setup00.sh` owns destination creation and marker writing. `customize00.sh` owns later unmount or removal. The patches treat them as one contract because a safe setup can still become unsafe when cleanup trusts stale or altered path text.

## How the three patches build the final candidate

The imported upstream scripts remain unchanged in `upstream/`. The candidate is represented as three patches applied in order.

### Patch 1: containment and cleanup discipline

`0001-contain-file-mirror-targets.patch` adds:

- canonical generated-root handling;
- refusal to use `/` as the generated root;
- source and destination resolution;
- strict descendant checks;
- root-relative NUL marker entries;
- complete cleanup preflight;
- per-action cleanup revalidation.

### Patch 2: preserve APT's configured destination spelling

`0002-preserve-file-uri-target-path.patch` separates the host source from the destination spelling.

Example:

```text
configured URI:  file:///tmp/repository-link
host link target: /srv/repository
mount source:     /srv/repository
root destination: $root/tmp/repository-link
```

The host operation uses the real source. APT still sees the path it was configured to use.

### Patch 3: reject every parent component

`0003-reject-parent-uri-components.patch` rejects any configured `..` component.

A path such as `/sources/spelling/../repository` can normalize to `/sources/repository`, yet the original pathname still tries to enter `sources/spelling` before processing `..`. When that intermediate directory is absent, APT cannot reach the normalized destination. Rejection gives setup one clear compatibility rule.

## Setup walkthrough

### Stage 1: start in strict shell mode

```sh
set -eu
```

- `-e` makes an unexpected command failure stop the hook.
- `-u` makes an unset variable an error.

When verbosity is high, `set -x` prints executed commands for diagnosis.

### Stage 2: canonicalize the generated root

```sh
rootdir="$(realpath -e -- "$1")"
case "$rootdir" in
    /) ... exit 1 ;;
esac
```

`$1` is the generated-root argument passed to the hook.

`realpath -e` requires the root to exist and resolves symlinks. A caller may pass a harmless-looking symlink that resolves to `/`; canonicalization makes that visible. Refusing `/` prevents the containment rule from treating every host path as a child of the generated root.

**Decision:** the root must exist, resolve successfully, and represent a private generated tree rather than the host filesystem root.

### Stage 3: parse a repository path

APT supplies repository URIs through:

```sh
apt-get indextargets --format '$(REPO_URI)'
```

The pipeline then:

1. keeps only `file:` URIs and removes their URI prefix;
2. sorts and deduplicates them;
3. reads one path spelling at a time.

The helper `safe_repo_path` removes trailing slashes and rejects:

- an empty result;
- a remaining absolute spelling;
- a leading `..`;
- any embedded `..` component.

Harmless dot components and repeated separators can be normalized later.

**Decision:** configured parent traversal is rejected as an input contract, even when lexical normalization appears to remain inside the host filesystem.

### Stage 4: resolve source and destination separately

The final `resolve_contained_target` helper receives:

1. a source path that must already exist;
2. optionally, a separate path spelling to use for the generated destination.

It calculates three values:

- `canonical_source`: the real existing host object from `realpath -e`;
- `target_relative`: the normalized configured destination without its leading slash;
- `canonical_target`: the destination after resolving existing components and symlinks below the generated root.

The key check is equivalent to:

```sh
case "$canonical_target" in
    "$rootdir"/*) allowed ;;
    *) rejected ;;
esac
```

This requires a **strict child**. The generated root itself is never a valid mirror target.

**Decision:** source identity and destination identity can differ, but the destination must resolve below the canonical generated root.

### Stage 5: choose mount or copy behavior

The mode decides which operation runs:

```text
root / unshare mode -> bind mount
other modes         -> mmdebstrap hook-helper copy or upload
```

For a repository directory:

- root-style modes create the checked destination and use a read-only bind mount;
- other modes invoke `sync-in` with the canonical source and the checked configured destination.

For a local package file:

- root-style modes create the target file and bind mount the canonical package source;
- other modes invoke `upload` with the same contained-target contract.

Because the script uses `set -e`, a failed mount, copy, or upload stops execution before the marker entry is written.

### Stage 6: record cleanup authority

After a successful setup action:

```sh
printf '%s\0' "$target_relative" >> "$rootdir/run/mmdebstrap/file-mirror-automount"
```

The marker stores only a canonical path relative to the generated root.

It has:

- no leading slash;
- no `.` or `..` component;
- no ambiguous line delimiter;
- no authority to name the generated root itself.

**Decision:** cleanup receives a constrained identifier, then treats that identifier as untrusted again when it is consumed.

## Cleanup walkthrough

### Stage 1: canonicalize the root again

Cleanup repeats root canonicalization and the `/` refusal. It does not assume the root argument still resolves the same way setup saw it.

It then defines the marker path. When the marker does not exist, cleanup exits successfully because there is nothing from this hook to remove.

### Stage 2: define one entry processor

`cleanup_entry` is a small shell program stored in a string and run by `xargs` for each NUL-delimited marker entry.

For every entry it:

1. rejects empty, absolute, trailing-slash, doubled-separator, `.` and `..` spellings;
2. resolves the current destination with `realpath -m`;
3. requires the resolved destination to remain a strict child of the root;
4. either validates only, unmounts, or recursively removes according to the supplied mode.

The inner program exists because `xargs --null` already handles the safe iteration over NUL-delimited entries.

### Stage 3: preflight the complete marker

The first `xargs` pass supplies the special mode `validate`:

```text
entry 1 -> validate only
entry 2 -> validate only
entry 3 -> validate only
...
```

Any invalid entry stops the script before an unmount or recursive removal occurs.

This closes the partial-cleanup case:

```text
valid entry -> valid entry -> escaping entry
```

Earlier code could act on the first two and fail on the third. The candidate acts on none.

### Stage 4: act with immediate revalidation

After the complete list passes, a second `xargs` pass processes every entry again.

- `root` and `unshare` modes call `umount`.
- other modes call `rm -r`.

The repeated resolution narrows the interval between validation and action. It cannot eliminate a hostile same-time pathname replacement race; that remains an explicit boundary.

### Stage 5: retire the marker only after success

The marker file is removed only after the complete action pass succeeds. The containing runtime directory is removed only when empty.

When validation or an action fails, the marker stays in place. A person can inspect it, repair the cause, and rerun cleanup.

## Four concrete traces

### Ordinary repository

```text
input URI          file:///srv/debian
canonical source   /srv/debian
configured target  /srv/debian
resolved target    $root/srv/debian
result             mount/copy, then marker "srv/debian\0"
```

### Repository whose final source component is a symlink

```text
input URI          file:///tmp/repository-link
canonical source   /srv/repository
configured target  /tmp/repository-link
resolved target    $root/tmp/repository-link
result             use real host source at APT-visible destination
```

### Traversal attempt

```text
input URI          file:///../../etc
parsed path        ../../etc
result             reject before mkdir, mount, copy, or marker write
```

### Mixed cleanup marker

```text
marker entry 1     var/cache/local
marker entry 2     ../../outside
first pass         entry 1 valid, entry 2 rejected
result             zero umount/rm-r calls; marker retained
corrected rerun    entry 1 removed or unmounted; marker retired
```

## Where each behavior is tested

- `tests/test_file_mirror_automount_containment.py`
  - baseline escape;
  - ordinary repository and package behavior;
  - destination-parent symlink escape;
  - canonical marker format;
  - valid and invalid cleanup.
- `tests/test_file_mirror_automount_root_guard.py`
  - literal `/` and a symlink resolving to `/`;
  - refusal before marker or repository processing.
- `tests/test_file_mirror_automount_cleanup_preflight.py`
  - a later invalid marker causes zero earlier destructive actions;
  - marker retention and immediate corrected rerun;
  - root-style and copy-style cleanup modes.
- `tests/test_file_mirror_automount_source_normalization.py`
  - configured-path normalization and leading traversal controls.
- `tests/test_file_mirror_automount_parent_component_reachability.py`
  - terminal source-symlink compatibility;
  - harmless dot normalization;
  - rejection of every `..` component;
  - the original configured pathname remains the compatibility reference.

Every regression applies the retained patch stack to temporary copies of the imported scripts. The tests use fake destructive commands and temporary directories.

## The decisions a reviewer is actually making

A reviewer is choosing whether these contracts belong together:

1. `/` can never be a generated root for this hook.
2. Configured repository paths containing `..` are invalid.
3. Existing host sources are canonicalized before use.
4. A terminal source symlink may preserve a different APT-visible destination spelling.
5. Existing destination symlinks are resolved before containment is accepted.
6. The destination must be a strict child of the generated root.
7. The marker stores canonical root-relative NUL-delimited entries.
8. Cleanup validates the complete marker before any destructive action.
9. Cleanup revalidates each entry immediately before acting.
10. Invalid or failed cleanup keeps enough state for diagnosis and rerun.

The supporting evidence is the five focused regression files, exact patch application, shell syntax checks, and the merged exact-head CI receipts recorded in issue #164 and pull request #179.

## What remains open

This candidate still uses check-then-act pathnames. Another process with sufficient access may replace a pathname or marker component after validation and before the actual operation.

The disposable tests also stop short of:

- real mount-namespace execution;
- real unmount behavior;
- a real non-root hook-socket transfer;
- portability beyond the documented GNU `realpath` and GNU `xargs` environment.

Those limits narrow the claim. They do not erase the demonstrated setup, cleanup, compatibility, and command-selection results.