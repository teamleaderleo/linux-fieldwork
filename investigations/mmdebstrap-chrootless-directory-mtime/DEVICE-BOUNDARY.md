# Directory mtime normalization must preserve the archive device boundary

Tracking: issue #380, PR #383, symlink repair PR #386.

## TL;DR

The current mmdebstrap archive command already uses GNU tar's
`--one-file-system` option. A pre-tar directory timestamp walk must preserve the
same device boundary or it can mutate mounted descendants that the archive
itself intentionally skips.

This stacked evidence repair replaces recursive `rglob` collection with a
top-down walk that:

- classifies each candidate with `lstat`;
- rejects symlink objects;
- compares each real directory's `st_dev` with the root device;
- prunes a foreign-device directory before descent;
- normalizes only real directories on the root device.

The focused reversing control injects a different device identity for one
subtree and proves the mount point analogue, nested directory, and sentinel file
remain unchanged.

No product patch is selected by this record.

## Explain like I'm five

Tar says, “pack this disk, but do not walk into another disk mounted inside it.”

A separate timestamp helper must follow the same rule. Otherwise it can walk
into the other disk and change folder dates even though tar was going to leave
that disk alone.

## Why care

Directory mtime normalization is a metadata mutation. Crossing a mount boundary
can change live or caller-owned state outside the archive contract.

The headline archive may still look correct because tar omits the foreign
device. That makes this a classic donut: correct output around the outside, with
an invisible side effect in the middle.

## Exact source boundary

Imported mmdebstrap source:

- requested revision: `debian/1.5.7-3`;
- resolved commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`;
- local path: `upstream/mmdebstrap/mmdebstrap`.

The archive worker runs `setup()` and then invokes GNU tar with:

```text
--sort=name
--mtime=@$SOURCE_DATE_EPOCH
--clamp-mtime
--numeric-owner
--one-file-system
--format=pax
--xattrs
```

Root and chrootless modes share that tar path. The current `tests/chrootless`
case explicitly compares the resulting tarballs byte-for-byte for four include
sets.

## Why `rglob` is not enough

The earlier synthetic helper enumerated every descendant before changing
timestamps. Even after symlink classification was repaired, a recursive walk
could still cross a mounted real directory.

Tar's later `--one-file-system` option does not undo those earlier timestamp
mutations.

## Candidate evidence contract

The focused helper now:

1. obtains the root object's `lstat` identity;
2. requires the root itself to be a real directory;
3. walks top-down with `followlinks=False`;
4. obtains `lstat` identity for each candidate directory;
5. discards non-directories and symlinks;
6. discards and prunes any directory whose `st_dev` differs from the root;
7. normalizes only the retained same-device directories.

Pruning occurs by replacing `os.walk`'s mutable `dirnames` list, so the walk does
not visit the foreign subtree later.

## Reversing control

Ordinary repository CI does not require root or mount privileges. The test
therefore uses a real directory subtree and an injected `lstat` result that gives
its top directory a different `st_dev`.

For both root-mode and chrootless analogues, the control creates:

```text
usr/share/foreign-device/
└── nested/
    └── sentinel
```

It records mtimes, reports a foreign device only for the top directory, and
requires:

- the top directory mtime is unchanged;
- the nested directory mtime is unchanged;
- the sentinel mtime and bytes are unchanged;
- neither nested path reaches the injected `lstat` function;
- an ordinary same-device directory is normalized;
- the final root/chrootless archive bytes still converge.

The injected device result tests traversal policy without claiming a real mount
operation occurred.

## Why not use a privileged mount in the ordinary suite?

A real bind or tmpfs mount would prove kernel integration but would add sudo,
mount lifecycle, namespace, cleanup, and hosted-runner dependencies to every
repository test.

The injected-device matrix is the smallest source-independent discriminator for
the walk algorithm. A product candidate still needs one disposable privileged
integration control with a real mount before promotion.

## Evidence boundary

Established:

- the focused algorithm is same-device by explicit `st_dev` comparison;
- a foreign-device directory is pruned before descent;
- same-device directory normalization and archive convergence remain intact.

Not established:

- real bind, tmpfs, overlay, FUSE, autofs, or namespace behavior;
- mount replacement races after classification;
- unreadable directories or permission changes during traversal;
- xattrs, ACLs, capabilities, sparse files, directory-format output, or failure
  cleanup;
- the final mmdebstrap product insertion point.

## Next discriminator

Before a product patch:

1. compose the symlink and device repairs into PR #383;
2. add one disposable real-mount integration probe that proves zero mutation and
   complete cleanup;
3. add xattr/ACL/capability and sparse-file reversing controls;
4. select an archive-only insertion point after setup and immediately before tar;
5. run an immediate second archive creation from a clean disposable tree.

## Authority

Internal synthetic filesystem and archive evidence only. No external contact,
package publication, release, deployment, or upstream modification is included
or authorized.
