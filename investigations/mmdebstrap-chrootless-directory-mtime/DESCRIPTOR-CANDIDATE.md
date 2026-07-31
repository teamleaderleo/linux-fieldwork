# Descriptor-retained directory mtime candidate

Tracking: #380, evidence PR #383, evidence repair PR #386.
Supersedes the pathname-based product attempt in PR #384.

## In simple words

The rejected helper checked a folder by name and then changed the date using that
same name. Another process could swap the name between those two operations.

This candidate keeps the folder itself open. Child folders are opened relative
to an already-open parent, shortcuts are refused, and the timestamp operation is
performed on the open folder rather than resolving its old name again.

## Current bounded contract

On Linux, when `SOURCE_DATE_EPOCH` is defined and the output format is direct
`tar`:

1. reuse mmdebstrap's existing locked temporary-root filehandle;
2. enumerate each directory through `/dev/fd/<parent-fd>`;
3. open child entries with `O_DIRECTORY|O_NOFOLLOW` relative to that pinned
   parent;
4. skip entries that disappeared or became symlinks or non-directories;
5. prune a different device;
6. require readable Linux `/proc/self/fdinfo` mount identity and prune a
   different mount ID, including same-device bind mounts;
7. retain visited `(device,inode)` identities to avoid traversal cycles;
8. recurse through the opened child handle;
9. preserve each opened directory's existing atime and set only its mtime through
   Perl `utime` on the directory filehandle;
10. retain GNU tar's existing `--clamp-mtime` policy for every non-directory
    member.

The helper is not called for `squashfs`, `ext2`, `ext4`, `directory`, `null`,
dry-run, absent `SOURCE_DATE_EPOCH`, or non-Linux output. Those surfaces retain
their current behavior until they receive separate evidence and portability
review.

## Why this is different from PR #384

PR #384 performed:

```text
lstat(path)
utime(path)
```

That has a replacement window. A symlink can redirect the second operation
outside the temporary root, and a regular-file replacement can violate the
claimed directory-only mutation boundary.

This candidate performs child lookup through a pinned parent with
`O_NOFOLLOW`. Once a directory is opened, rename or replacement of its old path
does not change the object referenced by the handle. Timestamp mutation receives
the handle itself.

## Complete-review repairs before execution

The first descriptor head correctly closed the pathname mutation race but
expanded beyond its evidence and overstated one control:

- it ran for `tar`, `squashfs`, `ext2`, and `ext4` although executed evidence
  covered direct tar only;
- it could reach the helper on non-Linux even though `/dev/fd`, `O_NOFOLLOW`,
  handle `utime`, and mount-ID authority were unresolved;
- unreadable `/proc/self/fdinfo` silently disabled same-device mount pruning;
- the replacement test changed the child before helper invocation, so it proved
  no-follow/type rejection but not readdir-to-open replacement.

The current generation:

- limits invocation to Linux direct tar;
- fails closed when Linux mount identity cannot be read;
- enumerates the child through the pinned parent, replaces it, and only then
  calls `open_child_directory` in both symlink and regular-file controls;
- retains source assertions for the Linux/direct-tar scope and the absence of a
  name-based mount-ID fallback.

The attempted pull-request checkpoint for this review was blocked by the
interaction platform. The exact observation and repair are retained here instead
of being retried or disguised.

## Focused controls

`tests/test_mmdebstrap_chrootless_directory_mtime_descriptor.py` requires:

- zero-fuzz, zero-offset patch application and transformed Perl syntax;
- root/chrootless archive convergence under the retained GNU tar options;
- preservation of intentionally distinct directory atimes while directory mtimes
  converge to the epoch;
- preservation of an intentionally old regular-file mtime;
- preservation of regular-file bytes, hard-link inode identity, symlink mtime
  and target, outside directory/sentinel mtimes, and `user.*` xattrs when
  supported;
- a clean second normalization run;
- enumeration of a real child followed by replacement with an outside symlink,
  then descriptor-open rejection;
- enumeration followed by replacement with a regular file, then descriptor-open
  rejection;
- continued authority over an opened directory after it is renamed and its old
  path becomes an outside symlink;
- fail-closed behavior when Linux mount identity is unavailable;
- one call using the existing locked root handle only inside the Linux,
  direct-tar, SDE branch;
- source contracts for `O_NOFOLLOW`, `/dev/fd`, filehandle `utime`, device and
  mount pruning, visited-inode tracking, and mtime-only mutation.

## Historical contract

The imported source already states that package extraction is retained in
chrootless mode because directory creation timestamps must match non-chrootless
mode for bit-by-bit identical tar output. Public mmdebstrap documentation also
states that `SOURCE_DATE_EPOCH` makes output bit-by-bit reproducible.

The run-999 failure is therefore treated as a product reproducibility boundary,
not merely an overstrict internal comparison.

## Remaining limits

This is still a draft candidate, not an upstream-ready patch.

- Non-Linux behavior is deliberately unchanged. A Hurd or other-platform design
  needs separate evidence rather than inheriting Linux `/proc` and no-follow
  assumptions.
- A real different-mount control may require a privileged disposable namespace;
  the current test verifies fail-closed mount-ID authority and ordinary tree
  behavior but does not create a bind mount.
- ACLs, capabilities, privileged xattrs, converter outputs, and a full package
  rerun remain unexecuted.
- Directory ctime necessarily changes when mtime is changed; the existing PAX
  policy deletes ctime from the output archive.
- A hostile actor that moves an arbitrary directory into the pinned root before
  descriptor lookup can make that object part of the operation tree; the same
  object would also be visible to the later archive traversal.
- The existing final tar invocation remains pathname-based. This candidate
  closes timestamp-mutation authority, not every same-UID replacement race in
  the output pipeline.

## Promotion rule

Require fresh exact-head repository CI, complete review of the descriptor and
mount boundary, and a real different-mount control. Only then compose this patch
into a disposable current-sid carrier and rerun the real direct-tar
`chrootless` comparison.

## Authority

Internal patch carrier and focused disposable controls only. Imported source is
unchanged. No merge, package publication, deployment, credential use, spending,
or public-upstream interaction is authorized or performed.
