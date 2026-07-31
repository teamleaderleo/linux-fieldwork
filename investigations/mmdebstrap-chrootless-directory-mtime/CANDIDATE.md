# Candidate — normalize directory mtimes before direct tar creation

## Status

`candidate for focused review; not selected for product landing`

## Mechanism

When `SOURCE_DATE_EPOCH` is defined and mmdebstrap is producing direct `tar`
output, walk the completed temporary root before starting GNU tar and set only
directory modification times to the selected epoch.

The helper:

- uses the already imported `File::Find` module;
- does not follow ordinary symlinks;
- records the root filesystem device;
- prunes directories on a different device before calling `utime`;
- preserves each directory access time while changing its modification time;
- changes directories only;
- runs after `setup()` and before direct tar output;
- does not run for `squashfs`, `ext2`, `ext4`, `directory`, `null`, dry-run, or
  absent `SOURCE_DATE_EPOCH` paths.

The existing GNU tar `--clamp-mtime` policy remains in place for non-directory
members, preserving package file mtimes older than the epoch.

## Why this candidate

The evidence matrix in PR #383 found:

- current clamp behavior reproduces run 999's directory-only divergence;
- full normalization converges bytes but destroys an intentionally old regular
  file mtime;
- directory-only normalization converges bytes and preserves that file mtime;
- comparison-only normalization leaves the product outputs different.

Complete review of the first candidate head found two unnecessary expansions:

1. it changed directory atime even though the observed difference and archive
   contract concern mtime;
2. it ran for every tar-backed converter even though executed evidence covers
   direct tar only.

The current generation preserves atime and limits execution to direct tar.

## Executable controls

`tests/test_mmdebstrap_chrootless_directory_mtime_candidate.py` requires:

1. exact patch application with neither fuzz nor offset;
2. successful Perl compilation of the transformed source;
3. directory mtime change with directory atime preservation;
4. regular-file bytes and mtime preservation;
5. hard-link inode/link-count preservation;
6. ordinary `user.*` xattr preservation when supported;
7. no ordinary symlink following or outside-target timestamp change;
8. repeatable second execution;
9. explicit different-device pruning before `utime`;
10. invocation only for direct tar output and only when `SOURCE_DATE_EPOCH`
    exists.

## Remaining product questions

The candidate deliberately stops before a full sid rerun. It still needs review
or execution for:

- a real different-device mount under the target rather than source-shape proof;
- concurrent replacement of a checked directory with a symlink between `lstat`
  and path-based `utime`;
- ACL and privileged xattr preservation;
- package-created directory semantics that may intentionally retain an old
  mtime;
- separate evidence and decisions for `squashfs`, `ext2`, and `ext4`;
- the real root/chrootless direct-tar comparison and a second clean package run;
- whether changing the temporary tree before archiving is preferable to a
  streaming header-only implementation.

The lstat-to-utime replacement race is a blocker, not a closed limitation: a
same-UID actor that replaces a checked directory with a symlink before `utime`
can redirect the path-based mutation outside the validated tree.

A Python tar-stream rewrite is not assumed safe: LF-14 already demonstrated that
rewriting GNU PAX sparse members through the current filter can create an
unextractable archive.

## Decision rule

Promote this candidate to a real package rerun only if complete review accepts
that directory mtimes are construction variance rather than package state, and
if the path-replacement authority gap is repaired or explicitly eliminated by a
safer header-only design that preserves sparse/PAX contracts.

## Authority

Internal candidate patch and synthetic controls only. No imported source is
modified on this branch. No merge, upstream publication, package change, or
external contact is authorized.
