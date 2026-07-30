# file-mirror-automount target containment

## Explain it like I am five

Imagine building a tiny model house inside a cardboard box. A helper receives a label such as `kitchen/packages` and copies or mounts the matching real folder into that place inside the box.

The old helper joined the box name and the label as plain text. A label containing `..` could say, in effect, “walk out of the box and use the real house.” A symlink inside the box could redirect the destination the same way. Cleanup later trusted a saved list of those labels and could unmount or delete the redirected location.

This candidate checks the real source, the real box, and the resolved destination. It allows the action only when the destination stays inside the box. Cleanup reads and validates the entire saved list before it removes anything.

## Why should anyone care?

This hook constructs commands for `mount`, copy/upload helpers, `umount`, and `rm -r`. A destination error therefore reaches beyond a wrong filename: it can operate on a host path outside the generated mmdebstrap root.

The executable tests use disposable directories and fake destructive commands, so they demonstrate command selection without touching real mounts. The underlying defect still concerns host-path authority. A malformed repository URI, a redirected target parent, a generated root resolving to `/`, or a corrupted cleanup marker can select the wrong host location.

## What happens if we leave it alone?

Several bad outcomes remain possible:

1. `file:///../../etc` can derive a target outside the generated root;
2. an existing symlink below the generated root can redirect a mount or copy destination outside it;
3. a generated-root argument of `/` makes ordinary host paths appear “inside” the root;
4. cleanup can act on an early valid entry before discovering a later malicious entry;
5. a source symlink can be mounted correctly on the host while becoming unreachable at the configured `file:` URI inside the generated root;
6. a path containing `..` can normalize to one destination while APT still resolves the original spelling through a missing parent component.

The result can be an out-of-root mount/copy/delete, partial cleanup, or a setup that reports success while APT still cannot reach the configured repository.

## Was the old behavior intentional?

The original hook appears to assume that APT emits ordinary canonical `file:` paths and that its own cleanup marker remains trustworthy. Direct string concatenation is compact and preserves the configured path in the common case.

That assumption breaks once path text can contain traversal components, once destination parents can be symlinks, or once persisted marker contents are stale or altered. The unsafe behavior does not look like a desired feature.

Some choices in the final candidate are deliberate:

- harmless `.` and repeated separators can be normalized while preserving a reachable configured URI;
- every `..` component is rejected because normalization alone can create a destination that the original URI cannot traverse to;
- a terminal source symlink keeps its configured destination spelling inside the generated root while the host action uses the canonical source;
- cleanup rejects the older leading-slash marker format during an active run instead of guessing whether historical text is safe.

## The proposed fix in plain terms

Setup performs this checklist:

1. resolve the generated root and refuse `/`;
2. parse the configured repository path and reject parent components;
3. resolve the actual host source;
4. preserve the safe configured URI spelling for the destination when APT needs that spelling;
5. resolve the destination, including existing symlinks;
6. require the destination to be a strict child of the generated root;
7. mount, copy, or upload using the checked source and destination;
8. record one canonical root-relative cleanup entry.

Cleanup performs two passes:

1. validate every saved entry and current resolved target with zero destructive actions;
2. after the full list passes, revalidate each target immediately before `umount` or `rm -r`.

The first pass prevents “remove three safe things, then discover the fourth entry escapes the root.” The second pass reduces the gap between checking and acting.

## Historical and technical precedent

- CWE-22 describes the recurring pathname-traversal weakness and recommends canonicalization followed by validation against the permitted directory: https://cwe.mitre.org/data/definitions/22.html
- GNU `realpath` produces absolute canonical names without `.` or `..`, resolves symbolic links, and provides separate modes for existing and missing components: https://www.gnu.org/software/coreutils/manual/html_node/realpath-invocation.html
- The broader Unix lesson predates this hook: a pathname is a request to traverse filesystem components, and symlinks plus parent components can change the object reached. A textual prefix alone does not grant containment.

The candidate follows that precedent while documenting its remaining pathname race. A process with enough access can still replace a component after validation and before the mount, copy, unmount, or removal call. Descriptor-relative hardening would be a separate, larger design.

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
- reusable note: `notes/filesystems/cleanup-markers-must-carry-contained-relative-paths.md`

## Concrete examples

### Escape spelling

```text
configured URI: file:///../../etc
old derived target: $root/../../etc
resolved target: outside $root
candidate result: reject before mkdir, mount, copy, or marker write
```

### Terminal source symlink

```text
configured URI: file:///tmp/repository-link
host symlink target: /srv/repository
host bind source: /srv/repository
generated destination: $root/tmp/repository-link
marker entry: tmp/repository-link
```

The source uses the real host directory. The destination preserves the path APT requests inside the generated root.

### Parent-component reachability

```text
configured URI: file:///sources/spelling/../repository
```

Creating only `$root/sources/repository` is insufficient because pathname traversal still attempts to enter `$root/sources/spelling` before processing `..`. The final candidate rejects the spelling before action.

## Executable regression

The disposable matrix uses fake `apt-get`, `mount`, `umount`, and destructive `rm -r` commands. It covers baseline traversal, root refusal, destination-symlink escape, complete cleanup preflight, corrected rerun, ordinary repositories and package files, source-symlink reachability, harmless dot normalization, parent-component rejection, exact patch application, and POSIX shell syntax.

No real mount, unmount, package mutation, external network access, privilege expansion, or upstream contact occurs.

## Evidence boundary

The candidate closes the demonstrated lexical traversal, generated-root `/`, pre-existing destination-symlink, static mixed-marker partial-cleanup, terminal source-symlink reachability, and parent-component reachability cases under GNU `realpath` and GNU `xargs` on Linux.

The remaining boundaries are pathname or marker replacement between validation and action, real mount-namespace behavior, and a real non-root hook-socket transfer.

## Disposition

The three-patch setup/cleanup candidate is one contract. Exact-head CI, a current-main comparison, complete-diff review, and cleanup/rerun confirmation remain the acceptance gates. No Debian or external upstream issue, patch, email, merge request, comment, or review is authorized or created by this record.