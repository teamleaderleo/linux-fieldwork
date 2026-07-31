# Archive-only root/chrootless directory mtime normalization candidate

Tracking: issue #380 and PR #395.

## TL;DR

The real Debian sid `chrootless` case produced root and chrootless tarballs
whose paths, types, modes, ownership, sizes, regular-file bytes, and file mtimes
matched. The only differences were 123 directory mtimes.

This candidate normalizes **real directories on the archive root device** to an
explicit `SOURCE_DATE_EPOCH`, immediately after `setup()` and before tar output,
for root/chrootless `--format=tar` only.

The product helper uses the already-imported Perl `File::Find` API, `lstat`
object identity, explicit `st_dev` comparison, `File::Find::prune`, and built-in
`utime`. It does not shell out to `find` or `touch`.

No product source is modified in place. The retained patch applies to disposable
source copies only.

## Explain like I'm five

The two builders put the same files into the box, but one keeps old dates on
folders. The test compares the complete tarballs, so those folder dates make the
boxes different.

The repair changes only real folder dates inside the temporary tar tree. It
checks each object itself, skips shortcuts, and prunes another mounted device
before changing anything there.

## Why care

The current `tests/chrootless` case explicitly compares root and chrootless
tarballs byte-for-byte for four include variants. Treating directory timestamps
as comparison noise would weaken implemented behavior rather than repair it.

Broader alternatives are worse:

- full timestamp normalization destroys package-owned file mtimes;
- tar-header rewriting reopens PAX, link, and sparse metadata risks;
- `find -xdev -type d -exec touch` prunes descent but still evaluates the
  foreign mountpoint itself, so it can mutate the mounted filesystem root.

The selected mechanism matches the reviewed object/device boundary exactly.

## Exact source boundary

Imported source:

- project: mmdebstrap;
- requested revision: `debian/1.5.7-3`;
- resolved commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`;
- path: `upstream/mmdebstrap/mmdebstrap`.

Candidate patch:

`0001-normalize-root-chrootless-directory-mtimes.patch`

Live carrier:

PR #395, branch `candidate/chrootless-directory-mtime-normalization-v3`.

## Demonstrated baseline

Workflow `30640356619` / run 999 completed 154 Debian sid package tests and
stopped at `(242/284) chrootless`.

Artifact `8798679560`, SHA-256
`50d8ab7a20cb241ff9821b35329508ecdb0c58cbd3dec348c18d68d1dfe7a244`,
showed 123 directory-only mtime differences.

The focused policy matrix established:

- current `--mtime` plus `--clamp-mtime` diverges on older chrootless directory
  mtimes;
- full timestamp normalization converges but destroys package file mtime;
- real-directory normalization converges and preserves package file mtime;
- comparison-only normalization explains but does not repair output.

## Selected product helper

The patch adds a helper with this contract:

1. `lstat` the archive root;
2. require the root itself to be a real directory, not a symlink;
3. retain the root `st_dev`;
4. walk top-down with `File::Find` and `no_chdir`;
5. `lstat` each object;
6. ignore non-directories and symlinks;
7. set `File::Find::prune` and return before mutation when `st_dev` differs;
8. call built-in `utime` only for retained real same-device directories;
9. fail explicitly on root stat, descendant stat, or timestamp failure.

The helper does not add a new external command dependency.

## Invocation gate

The worker calls the helper only when all are true:

- dry-run is false;
- `SOURCE_DATE_EPOCH` exists;
- format is exactly `tar`;
- mode is exactly root or chrootless.

The call runs immediately after `setup()` and before the worker success boundary
and tar output selection.

Consequences:

- runs without an explicit reproducibility epoch remain unchanged;
- directory/null output remains unchanged;
- unshare/fakechroot remains unchanged;
- squashfs/ext2/ext4 remains unchanged;
- helper failure occurs before tar bytes are written.

The caller may already have created an empty target file before the worker
starts. This candidate does not change that existing failure behavior.

## Evidence inherited from the stacked matrix

The evidence stack established:

- symlink-to-directory and outside-target preservation;
- hard-link inode and package file mtime preservation;
- injected foreign-device pruning before descent;
- selected user xattrs preserved in source and PAX headers;
- sparse source size, allocation, mtime, and logical bytes preserved;
- real tmpfs root/nested/sentinel unchanged;
- real POSIX ACL and file capability unchanged;
- stale runtime symlink rejected before cleanup;
- stale mount refused before runtime reset;
- unmount rechecked before recursive deletion;
- immediate clean rerun.

Initial real-boundary workflow `30656548394` passed with artifact `8803444764`,
SHA-256
`60ae20d7b19d0e690bac39233f273517b16e70c52c10d8428771e3e946bdc548`.

## Exact product execution in the real probe

The candidate branch contains
`prepare_product_normalizer.py`. It:

- copies exact imported source;
- applies the retained patch with zero fuzz and zero offset;
- validates complete Perl syntax;
- extracts only `normalize_archive_directory_mtimes`;
- writes an executable Perl harness.

When the candidate patch exists, `real_metadata_probe.sh` executes that extracted
Perl helper against the real tmpfs/ACL/capability fixture. The receipt must say:

```text
normalizer=extracted-product-perl-helper
```

The dedicated candidate workflow rejects a fallback to the Python evidence
model.

## Candidate tests

The exact candidate matrix requires:

- source-independent patch grammar validation;
- declared old-side source slices match exact imported lines;
- `git apply --check` succeeds;
- GNU patch zero-fuzz/zero-offset dry run succeeds;
- exact patch application and complete Perl syntax;
- exact `File::Find`/`lstat`/`st_dev`/`prune`/`utime` mechanism;
- explicit dry-run, epoch, format, and mode gate;
- source order before tar output;
- regular-file, symlink, hard-link, outside-target, and second-run preservation;
- missing-root, symlink-root, and injected-`utime` failure controls;
- exact product-helper preparation and real-probe handoff;
- current Debian sid perltidy agreement in a sid container.

## Gate history and failure ownership

The candidate intentionally preserves classified red runs:

1. malformed hunk counts stopped before candidate execution;
2. exact-looking hunks still missed until source ranges were regenerated;
3. source-slice, `git apply`, and GNU patch checks then passed;
4. Ubuntu runner perltidy 20230309 reformatted unchanged imported source, so the
   whole-source host formatting test was invalid;
5. formatting authority moved to a Debian sid container.

These were carrier/harness failures, not product behavior results.

## Failure precedence

A root/descendant `lstat` failure or `utime` failure is an archive-preparation
failure and remains authoritative before tar output begins.

The helper does not roll back directory mtimes after a partial failure. The tree
is already a disposable archive/image temporary root and existing outer cleanup
owns its removal. Product promotion still requires the real focused sid case and
a clean rerun.

## Remaining promotion gate

After exact repository and dedicated candidate workflows pass:

1. compose the patch into the disposable sid source generation;
2. execute only the real `chrootless` case first, including all four include
   variants;
3. require byte-identical root/chrootless tarballs and unchanged host-root
   receipt;
4. rerun the focused case cleanly;
5. continue the remaining package matrix from the next independent failure.

## Evidence boundary

Still open:

- same-device bind mounts, which product tar also traverses;
- mount replacement races after traversal starts;
- SELinux/AppArmor labels;
- ownership-hostile or concurrently replaced directories;
- non-tar image format policy;
- sparse archive layout (source sparse allocation is preserved; tar is not
  invoked with `--sparse` here);
- every package set and architecture;
- upstream intent or acceptance.

## Authority

Internal Linux Fieldwork candidate only. No Debian/mmdebstrap upstream issue,
email, patch, review, package publication, release, deployment, or merge to
`main` is included or authorized.
