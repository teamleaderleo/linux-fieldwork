# Candidate — normalize directory mtimes before archive creation

## Status

`candidate for focused review; not selected for product landing`

## Mechanism

When `SOURCE_DATE_EPOCH` is defined and mmdebstrap is producing a tar-backed
format (`tar`, `squashfs`, `ext2`, or `ext4`), walk the completed temporary root
before starting GNU tar and set directory access/modification times to the
selected epoch.

The helper:

- uses the already imported `File::Find` module;
- does not follow symlinks;
- records the root filesystem device;
- prunes directories on a different device before calling `utime`;
- changes directories only;
- runs after `setup()` and before archive output;
- does not run for `directory`, `null`, dry-run, or absent
  `SOURCE_DATE_EPOCH` paths.

The existing GNU tar `--clamp-mtime` policy remains in place for non-directory
members, preserving package file mtimes older than the epoch.

## Why this candidate

The evidence matrix in PR #383 found:

- current clamp behavior reproduces run 999's directory-only divergence;
- full normalization converges bytes but destroys an intentionally old regular
  file mtime;
- directory-only normalization converges bytes and preserves that file mtime;
- comparison-only normalization leaves the product outputs different.

## Executable controls

`tests/test_mmdebstrap_chrootless_directory_mtime_candidate.py` requires:

1. exact zero-fuzz patch application to the imported source;
2. successful Perl compilation of the transformed source;
3. directory-only timestamp changes;
4. regular-file bytes and mtime preservation;
5. hard-link inode/link-count preservation;
6. ordinary `user.*` xattr preservation when supported;
7. no symlink following or outside-target timestamp change;
8. repeatable second execution;
9. explicit different-device pruning before `utime`;
10. invocation only inside the archive-backed format branch and only when
    `SOURCE_DATE_EPOCH` exists.

## Remaining product questions

The candidate deliberately stops before a full sid rerun. It still needs review
or execution for:

- a real different-device mount under the target rather than source-shape proof;
- concurrent replacement of a checked directory with a symlink between `lstat`
  and `utime`;
- ACL and privileged xattr preservation;
- package-created directory semantics that may intentionally retain an old
  mtime;
- all tar-backed converters, not only direct tar output;
- the real root/chrootless archive comparison and a second clean package run;
- whether changing the temporary tree before archiving is preferable to a
  streaming header-only implementation.

A Python tar-stream rewrite is not assumed safe: LF-14 already demonstrated that
rewriting GNU PAX sparse members through the current filter can create an
unextractable archive.

## Decision rule

Promote this candidate to a real package rerun only if complete review accepts
that directory mtimes are construction variance rather than package state, and
if no safer header-only implementation preserves sparse/PAX contracts.

## Authority

Internal candidate patch and synthetic controls only. No imported source is
modified on this branch. No merge, upstream publication, package change, or
external contact is authorized.
