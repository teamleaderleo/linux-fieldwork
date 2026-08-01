# Deep dive

## Question and observed failure

Can `file-mirror-automount` guarantee that every mount, copy, upload, unmount, and recursive removal target stays below the generated mmdebstrap root while preserving valid `file:` repository behavior?

The baseline derives targets by joining `rootdir` with path text from APT or the cleanup marker. It performs no canonical containment decision. A repository such as `file:///../../etc` can therefore resolve outside the generated root. An existing symlink below the generated root can redirect an apparently contained target. Passing `/` as the generated root makes ordinary host paths satisfy any descendant-prefix check. Cleanup processes marker entries sequentially, so it can act on valid early entries before discovering a later escape.

This belongs to the hook source owner. The failing commands are constructed directly by `setup00.sh` and `customize00.sh`; package-test scheduling, mirror-server readiness, and Debian packaging only determine when the hook runs.

## Source mechanism

### Setup baseline

`setup00.sh` obtains repository URIs from `apt-get indextargets`, strips the `file:` prefix, and uses the resulting path for both the host source and the in-root target. Included package files follow the same concatenation model after `realpath` on the source. Successful actions append leading-slash entries to a NUL-delimited marker.

### Cleanup baseline

`customize00.sh` reads the marker with GNU `xargs`, prints every textual target, then invokes `umount` or `rm -r` on `"$rootdir/{}"`. It trusts the marker and acts entry by entry.

### Final candidate

The selected candidate separates three identities:

1. canonical existing host source;
2. normalized configured in-root destination spelling;
3. canonical root-relative cleanup entry.

Setup canonicalizes the generated root and refuses `/`. Repository input rejects every `..` component. The source uses `realpath -e`; the configured target uses `realpath -m -s` so a terminal source symlink can keep the URI path APT requested; the destination below the generated root uses ordinary `realpath -m` so existing destination symlinks become visible. Only a strict child passes.

Cleanup rejects empty, absolute, trailing-slash, doubled-separator, dot-component, and parent-component entries. It resolves each current target and requires a strict child. One complete validation-only pass runs before the first destructive action, followed by a second pass that repeats validation immediately before each action.

## Reproduction narrative

The smallest baseline distinguisher is a generated root nested several directories deep plus the repository URI `file:///../../etc`. A fake `mount` records a source of `/../../etc` and a target of `$root/../../etc`, demonstrating selection outside the generated root without a real mount.

Candidate controls include:

- an ordinary repository and local package file;
- a destination parent symlink pointing outside;
- literal `/` and a symlink resolving to `/` as generated roots;
- a terminal source symlink whose configured URI must remain reachable inside the candidate root;
- harmless `.` path spelling;
- any leading or embedded `..` component;
- a marker with one valid entry followed by an invalid or symlink-escaping entry;
- correction of the marker followed by immediate successful rerun.

## Approach history

### Approach A — canonical host source as both source and destination

- Mechanism: use `realpath -e` source output to derive the in-root target.
- Evidence: PR #179 review showed `file:///tmp/repository-link -> /srv/repository` would mount at `$root/srv/repository` while APT still requests `$root/tmp/repository-link`.
- Result: rejected.
- Compatibility cost: valid terminal source-symlink configurations become unreachable.

### Approach B — separate canonical source from configured destination

- Mechanism: use the canonical path for the host operation and a symlink-preserving normalized URI path for the in-root destination.
- Evidence: source-symlink setup, cleanup, and rerun regression.
- Result: accepted.
- Compatibility cost: requires GNU `realpath -m -s`.

### Approach C — normalize embedded parent components

- Mechanism: allow `spelling/../repository` after lexical normalization.
- Evidence: predecessor differential proved the normalized destination can exist while the original configured pathname remains unreachable because the intermediate `spelling` component is absent in the generated root.
- Result: rejected.
- Compatibility cost: setup can claim success while APT cannot traverse the configured URI.

### Approach D — reject every configured parent component

- Mechanism: reject leading or embedded `..` before source or destination action.
- Evidence: parent-component reachability and source-normalization regressions.
- Result: accepted.
- Compatibility cost: some textually normalizable paths are refused; the rule stays deterministic and preserves APT reachability.

### Approach E — validate and act one cleanup entry at a time

- Mechanism: resolve and remove each entry sequentially.
- Evidence: a valid entry followed by an invalid entry would still cause partial cleanup.
- Result: rejected.
- Compatibility cost: poor rerun and diagnostic behavior.

### Approach F — complete marker preflight, then action-time revalidation

- Mechanism: validation-only pass over the complete NUL stream, followed by a second validating action pass.
- Evidence: root and fakechroot mixed-marker controls produce zero fake actions, preserve the marker, and succeed after correction.
- Result: accepted.
- Compatibility cost: two marker scans and repeated path resolution.

### Approach G — descriptor-relative or namespace isolation

- Mechanism: `openat2`-style beneath-root operations or a private mount namespace.
- Evidence: conceptual hardening route; absent from the focused carrier.
- Result: deferred.
- Compatibility cost: substantially larger implementation, portability, privilege, and review surface.

## Selected correction

The upstream packet contains one composed patch modifying both hook scripts. It preserves the proven three-increment behavior from PR #179 while presenting a reviewer with the final current-source diff. The patch has no investigation paths, Linux Fieldwork test paths, or package-test scheduling changes.

## Why the changes belong together

Setup writes the marker and cleanup consumes it. The safety claim spans the complete authority chain:

```text
configured input -> checked action target -> constrained marker -> checked cleanup target
```

A setup-only patch leaves destructive cleanup trusting an unsafe marker model. A cleanup-only patch leaves initial mount/copy/upload selection exposed. URI compatibility and parent-component policy alter the same setup helper and belong in the same final behavior.

## Compatibility analysis

- Ordinary absolute repository directories preserve their configured in-root location.
- Local `.deb` paths remain available at the path passed to dpkg.
- Terminal source symlinks use the canonical host object at the configured URI path.
- Harmless `.` components and repeated separators normalize.
- Every `..` component is refused before action.
- Existing destination symlinks are resolved before containment acceptance.
- The generated root itself is never a valid target, and `/` is refused as the generated root.
- Markers become canonical root-relative NUL entries; historical leading-slash entries fail closed during an active cleanup.
- Action failure retains the marker for diagnosis and rerun.
- GNU `realpath` and GNU `xargs` are explicit runtime dependencies already consistent with the Linux/GNU operating environment of this hook.

## Current-upstream reconciliation

On 2026-08-01 the canonical Forgejo repository reported `main@77ec9be5417ee44c96343d2347145585da1b1f94`. Its hooks directory still identified the file-mirror setup warning-prefix commit from 2024-03-23 as the latest change in that directory. Debian sid/forky remained on `1.5.7-3`. The current packaged hook blobs are exactly:

- setup: `6ccbdaf2ba97c77c4e5223ac5280acd51a998424`;
- cleanup: `b6b9b46afdd9dad01df3abcb514475326162e42c`.

Those match the Linux Fieldwork imported blobs recorded before PR #179. The retained three-patch stack applied without a rejected hunk. Patch 0003 applied with one line of context fuzz after patch 0002 shifted the helper body; the resulting source matches the intended final candidate and passes shell syntax. The packet patch was generated from the baseline and final source as a fresh unified diff, eliminating incremental-patch context history from the proposed upstream artifact.

## Remaining limits

A sufficiently capable concurrent actor can replace a pathname component or marker after validation and before the corresponding action. The second cleanup pass narrows the interval while retaining pathname APIs. The claim therefore covers static input, current path resolution, and command selection; it excludes a full filesystem transaction against hostile same-time replacement.

Real mount propagation, real unmount behavior, a privileged integration fixture, and real non-root hook-socket transfer remain outside the disposable matrix. These are useful later gates, with larger environmental cost than the current source correction.

## Open questions

- Does the upstream maintainer prefer one composed commit or a small ordered series that preserves review history?
- Should historical leading-slash markers receive an explicit migration diagnostic beyond the current unsafe-entry error?
- Does upstream want the fake destructive-command matrix adapted into its own test harness, or a smaller direct hook regression?
- Would upstream accept the explicit GNU `realpath -m -s` dependency in this hook, or prefer equivalent shell/perl logic?
