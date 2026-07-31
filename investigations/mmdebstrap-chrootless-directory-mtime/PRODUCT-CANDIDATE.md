# Archive-only root/chrootless directory mtime normalization candidate

Tracking: issue #380 and evidence PRs #383, #386, #388, #390, and #391.

## TL;DR

The real Debian sid `chrootless` failure is a reproducibility mismatch: root and
chrootless tarballs have the same paths, types, modes, ownership, sizes, regular
file bytes, and file mtimes, but 123 directory mtimes differ.

This candidate normalizes **real same-filesystem directories only** to the
explicit `SOURCE_DATE_EPOCH`, immediately after `setup()` and before tar output,
for `--format=tar` in root and chrootless modes.

It does not change:

- directory or null output;
- unshare or fakechroot behavior;
- squashfs/ext2/ext4 image paths;
- runs without `SOURCE_DATE_EPOCH`;
- dry runs;
- regular files, symlinks, hard links, xattrs, ACLs, capabilities, sparse source
  allocation, or mounted foreign-device descendants.

The retained patch is a local candidate. It is not offered upstream and is not
yet promoted until exact repository and focused sid execution pass.

## Explain like I'm five

The two builders make the same box, but one keeps old dates on folders while the
other writes the selected reproducible date. The test compares the whole boxes,
so they differ.

The repair changes only real folder dates in the temporary archive tree. It does
not change file dates, shortcuts, mounted folders, or directory-format output.

## Why care

The package test explicitly requires root and chrootless tarballs to be
byte-identical for four include variants. Treating directory timestamps as
comparison noise would weaken current behavior rather than fix it.

A broad timestamp rewrite would also destroy package-owned regular-file mtimes.
A tar-header rewrite would reopen archive metadata and sparse-layout risks. The
selected candidate is the smallest mechanism that matches the demonstrated
owner.

## Exact source boundary

Imported source:

- project: mmdebstrap;
- requested revision: `debian/1.5.7-3`;
- resolved commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`;
- path: `upstream/mmdebstrap/mmdebstrap`.

Candidate patch:

`0001-normalize-root-chrootless-directory-mtimes.patch`

Construction branch:

`candidate/chrootless-directory-mtime-normalization`.

The patch applies to a temporary source copy. The imported source remains
unchanged.

## Demonstrated baseline

Run 999, workflow `30640356619`, completed 154 Debian sid package tests and
stopped at `(242/284) chrootless`.

Artifact `8798679560`, SHA-256
`50d8ab7a20cb241ff9821b35329508ecdb0c58cbd3dec348c18d68d1dfe7a244`,
showed 123 directory-only mtime differences.

The focused synthetic matrix established:

- current `--mtime` plus `--clamp-mtime` diverges on older chrootless directory
  mtimes;
- full timestamp normalization converges but destroys package file mtime;
- real-directory normalization converges and preserves package file mtime;
- comparison-only normalization explains but does not repair output.

## Selected mechanism

The candidate adds:

```perl
sub normalize_archive_directory_mtimes {
    my $root  = shift;
    my $mtime = shift;

    0 == system(
        'find', $root, '-xdev', '-type', 'd', '-exec',
        'touch', '--no-dereference', "--date=\@$mtime", '--', '{}', '+'
      )
      or error "cannot normalize archive directory mtimes: $?";
}
```

The worker invokes it only when all are true:

- not dry-run;
- `SOURCE_DATE_EPOCH` exists;
- format is exactly `tar`;
- mode is exactly root or chrootless.

`touch` availability is checked inside that exact gate. Unrelated modes and
formats do not gain a new dependency.

## Why this approach

### Why GNU `find -xdev -type d`?

Current product tar already uses `--one-file-system` and does not follow
symlinks. The selected walk mirrors those two material traversal boundaries:

- `-xdev` prunes foreign-device mounted descendants;
- `-type d` selects real directories under ordinary find semantics;
- `touch --no-dereference` makes object identity explicit.

### Why before tar output?

The call runs:

```text
setup completes
→ directory normalization
→ worker sends success boundary
→ tar output pipe is selected
→ tar starts
```

A normalization failure therefore produces no partial tar stream. The existing
caller may already have created an empty target file before worker execution;
this candidate does not change that established failure behavior.

### Why only explicit `SOURCE_DATE_EPOCH`?

Without the variable, mmdebstrap chooses current wall-clock time for `$mtime`.
Rewriting every directory to an implicit current timestamp would create a new
behavior unrelated to the demonstrated reproducibility contract.

### Why only tar format?

The real failure is a tarball byte comparison. Squashfs/ext2/ext4 consume the
same intermediate tar path but have additional timestamp, xattr, and filesystem
compatibility surfaces. Directory output exposes the target tree directly and
must not be mutated merely to satisfy an archive test.

## Rejected alternatives

### Full `--mtime` without clamp

Converges archives but overwrites package-owned regular-file mtimes.

### Comparison-only manifest normalization

Leaves product bytes different and weakens the explicit `cmp` test.

### Tar header rewrite

Adds a second archive transformation layer and repeats the class of PAX, hard
link, and sparse metadata hazards seen in LF-14.

### General recursive Python/Perl walk

Can diverge from tar's one-filesystem and symlink behavior unless it reimplements
those boundaries. The existing GNU tools already define the target platform
contract.

### Global `touch` dependency

Would make unrelated modes and formats require a tool they never execute. The
candidate checks it only inside the selected normalization path.

## Evidence inherited from the stacked matrix

The composed evidence stack proves:

- symlink-to-directory objects and outside targets are not mutated;
- hard-link inode identity and package file mtime remain unchanged;
- injected foreign-device subtrees are pruned before descent;
- selected user xattrs survive source normalization and PAX archive creation;
- sparse source size, allocation, mtime, and logical bytes remain unchanged;
- a real tmpfs subtree remains unchanged;
- real POSIX ACLs and file capabilities remain unchanged;
- cleanup unmounts before recursive deletion;
- a second clean real-boundary run succeeds.

Real-boundary workflow `30656548394` passed at head
`679f8b1ecae13c05013f82dc5750a424f816bd27`.
Artifact `8803444764`, SHA-256
`60ae20d7b19d0e690bac39233f273517b16e70c52c10d8428771e3e946bdc548`.

## Candidate regression

`tests/test_mmdebstrap_chrootless_directory_mtime_candidate.py` requires:

- exact zero-fuzz, zero-offset patch application;
- complete Perl syntax;
- current sid perltidy agreement when available;
- exact helper command and failure diagnostic;
- `touch` dependency scoped to the selected gate;
- explicit dry-run, epoch, format, and mode predicates;
- source order before the tar output boundary;
- real directory normalization with regular file, symlink, hard-link, and outside
  target preservation;
- immediate second helper run;
- fail-closed fake-find and fake-touch controls.

The dedicated real-boundary workflow installs perltidy and executes this test on
the same exact candidate head.

## Failure precedence

A missing `touch`, failing `find`, or failing `touch` is an archive-preparation
failure and remains authoritative. The helper stops before tar output begins.

The candidate does not attempt rollback of directory mtimes after a partial
normalization failure. The tree is already a disposable archive/image temporary
root and existing outer cleanup owns its removal. A product promotion still
requires the focused real sid case and a second complete run.

## Compatibility boundary

Still open after the reduced candidate gate:

- same-device bind mounts, which GNU tar `--one-file-system` also traverses;
- mount replacement races after traversal starts;
- SELinux/AppArmor labels;
- unreadable or ownership-hostile directories;
- squashfs/ext2/ext4 normalization policy;
- sparse archive layout (source sparse allocation is preserved, but tar is not
  invoked with `--sparse` here);
- every package set and architecture;
- current upstream intent or acceptance.

## Promotion gate

Before product recommendation:

1. exact repository CI and dedicated metadata/candidate workflow pass;
2. complete candidate diff review passes;
3. compose the candidate into a disposable sid source generation;
4. run the focused real `chrootless` case and all four include variants;
5. require byte-identical archives and unchanged host-root receipt;
6. run a second clean focused execution;
7. only then continue the remaining package matrix from the next independent
   failure.

## Authority

Internal Linux Fieldwork candidate only. No Debian/mmdebstrap upstream issue,
email, patch, merge request, review, package publication, release, or deployment
is included or authorized.
