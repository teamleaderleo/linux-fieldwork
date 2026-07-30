# Archive renames must update reference metadata

## In simple words

An archive member name is not the only place where a path can appear. Hard-link targets, symlink target text, and extended headers can also carry path-like values.

Renaming only the member can leave the archive internally inconsistent: a hard link points at a name that no longer exists, a transformed symlink keeps stale text, or an old PAX `path` header overrides the new name.

## What I learned

When an archive rewriter strips components or transforms names, review every path-bearing field:

- member name;
- hard-link target;
- symlink target text when the operation's scope includes it;
- PAX `path`;
- PAX `linkpath`;
- format-specific metadata such as GNU sparse names.

Hard links refer to another archive member and generally need the same archive-name rewrite. Symlink targets are filesystem link text, so their treatment depends on the operation:

- component stripping changes archive member paths and hard-link references, while symlink text stays literal;
- GNU tar transforms default to `rsh`, which includes member names, symlink targets, and hard-link targets;
- uppercase `S` disables symlink-target transformation.

For PAX output, removing stale `path` and `linkpath` fields is safer than manually copying old values. A capable writer can regenerate the extended headers from corrected member and link values when they exceed legacy header limits.

Validation must extract the archive. A listing that looks plausible can still contain a hard link to a missing target or a symlink aimed at a stale transformed path.

## Source and provenance

- Project: imported `mmdebstrap`
- File: `upstream/mmdebstrap/tarfilter`
- Hard-link/PAX issue: #25
- Transform-scope correction: #63
- Original investigation: `investigations/tarfilter-path-rewrite-metadata/`
- Corrected investigation: `investigations/tarfilter-transform-target-scopes/`

## Validation

The retained regressions cover:

- short hard-link paths under component stripping;
- default transforms across member, hard-link, and symlink targets;
- the uppercase `S` symlink opt-out;
- the merged PR #48 result as a negative control;
- long PAX member paths;
- long PAX hard-link targets;
- GNU tar differential archive metadata;
- GNU tar extraction and inode equality.

## Correction history

PR #48 originally recorded unchanged symlink text under a default transform as success. Post-merge review showed that GNU tar defaults to `rsh`; issue #63 and PR #68 correct the candidate and regression. This distinction is easy to miss because symlink target text should not receive hard-link semantics automatically, yet a transform command can explicitly include it by default.

## Limits

This note does not define every unusual relative hard-link target, transform occurrence selector, transform scope combination, or archive format. GNU sparse metadata and filter matching are handled by separate investigations. Complete GNU/sed transform grammar remains in issue #36.

## Related work

- Issue #25 for hard-link/PAX consistency
- Issue #63 for target scopes
- Issue #36 for remaining transform grammar
- Issue #28 for path-filter matching
- PR #23/#45 for GNU sparse metadata
