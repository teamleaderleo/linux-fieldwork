# Keep tarfilter path, hard-link, and PAX metadata consistent

## In simple words

`--strip-components` and `--transform` currently rename archive members but do not rename hard-link targets. They also leave old PAX `path` and `linkpath` metadata attached.

The output can list the new member name while still pointing a hard link at the old path, or a stale PAX header can override the requested rename entirely.

PR #48 retained a candidate that rewrites hard-link targets and removes stale PAX metadata. Its transform regression deliberately left symlink targets unchanged. Post-merge review found that expectation diverges from GNU tar: default transforms apply to member names, hard-link targets, and symlink targets; uppercase `S` disables symlink-target transformation.

Issue #63 and PR #68 carry the integrated correction. The original PR #48 patch remains useful as a negative control and as the bounded component-strip/PAX repair record.

## Existing work and duplicate search

- Canonical hard-link/PAX issue: #25.
- Post-merge transform-scope correction: #63 and PR #68.
- Replacement count and replacement-language candidate: PR #56, issues #36 and #51.
- Issue #28 owns filter matching and parent retention.
- Issue #29 owns no-option passthrough.
- PR #23 separately handles GNU sparse payload metadata.

## Source

- Project: imported `mmdebstrap`
- File: `upstream/mmdebstrap/tarfilter`
- Source blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Original candidate patch: `tarfilter-path-rewrite-metadata.patch`
- Integrated scope candidate: `../tarfilter-transform-target-scopes/tarfilter-transform-target-scopes.patch`

## Source and test map

The archive loop changes only `member.name` for component stripping and transforms. `member.linkname`, PAX `path`, and PAX `linkpath` remain unchanged.

The original PR #48 candidate:

- strips the same component count from hard-link targets;
- applies every transform to hard-link targets;
- removes stale `path` after a member rename;
- removes stale `linkpath` after a hard-link target rename;
- leaves symlink `linkname` untouched.

The first four behaviors remain useful. The final transform behavior is superseded by issue #63 / PR #68. GNU tar defaults to `rsh`, so the integrated candidate transforms symlink targets unless `S` disables that scope.

Python's PAX writer regenerates long path/link headers from corrected `TarInfo` values after stale fields are removed.

## Assertions and negative controls

`tests/test_tarfilter_path_rewrite_metadata.py` now:

- reproduces the current short hard-link strip output and requires GNU tar extraction to fail;
- requires the integrated candidate to rewrite the target and extract one shared inode;
- applies the exact PR #48 patch and requires its stale `sym -> prefix/target` default result as a negative control;
- compares integrated default and `S` archives directly with GNU tar;
- requires default extraction with `sym -> target`;
- creates long PAX `path` and `linkpath` values;
- proves the unmodified strip retains the stale prefixed long path;
- requires regenerated long metadata and successful extraction.

## Evidence boundary

The component-strip candidate covers hard links whose target path can receive the same component stripping. A hard-link target with fewer components than the requested strip is omitted rather than emitted broken; broader GNU tar compatibility for unusual relative hard-link targets needs separate fixtures. Component stripping still does not rewrite symlink text.

Transform target scopes are handled by issue #63 / PR #68. Numeric occurrence selectors, `x`, complete BRE differences, and other transform extensions remain in issue #36. GNU sparse `GNU.sparse.name` remains with the sparse rewrite candidate.

## Self-review correction

The original record incorrectly treated symlink target preservation as universally correct. Symlink targets are filesystem link text, yet GNU tar's transform command explicitly includes them in its default scope. The corrected rule is operation-specific:

- component stripping rewrites member names and hard-link references, not symlink text;
- transforms follow their target scopes, defaulting to `rsh`;
- uppercase `S` preserves symlink target text.

## Reusable note

See `notes/filesystems/archive-renames-must-update-reference-metadata.md`.

## Next step

Use PR #68 as the integrated local candidate for transforms. Retain PR #48 as the hard-link/PAX subset and stale-scope negative control. No upstream contact is authorized.
