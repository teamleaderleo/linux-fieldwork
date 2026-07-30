# Archive renames must update reference metadata

## In simple words

An archive member name is not the only place where a path can appear. Hard-link targets and extended headers can also carry archive paths.

Renaming only the member can leave the archive internally inconsistent: a hard link points at a name that no longer exists, or a stale PAX `path` header overrides the new name.

## What I learned

When an archive rewriter strips components or transforms names, review every path-bearing field:

- member name;
- hard-link target;
- PAX `path`;
- PAX `linkpath`;
- format-specific metadata such as GNU sparse names.

Hard links refer to another archive member and generally need the same archive-name rewrite. Symlink targets are filesystem link text and must not automatically receive hard-link semantics.

For PAX output, removing stale `path` and `linkpath` fields is safer than manually copying old values. A capable writer can regenerate the extended headers from the corrected member name and link target when they exceed legacy header limits.

Validation must extract the archive. A listing that looks plausible can still contain a hard link to a missing target.

## Source and provenance

- Project: imported `mmdebstrap`
- File: `upstream/mmdebstrap/tarfilter`
- Canonical issue: #25
- Investigation: `investigations/tarfilter-path-rewrite-metadata/`

## Validation

The retained regression covers:

- short hard-link paths under component stripping;
- short hard-link paths under transforms;
- symlink target preservation;
- long PAX member paths;
- long PAX hard-link targets;
- GNU tar extraction and inode equality.

The unmodified short and long strip results are negative controls.

## Limits

This note does not define behavior for every unusual relative hard-link target or every archive format. GNU sparse metadata and filter matching are handled by separate investigations.

## Related work

- Issue #25
- Issue #28 for path-filter matching
- PR #23 for GNU sparse metadata
