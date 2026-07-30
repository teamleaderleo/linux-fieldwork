# Keep tarfilter path, hard-link, and PAX metadata consistent

## In simple words

`--strip-components` and `--transform` currently rename archive members but do not rename hard-link targets. They also leave old PAX `path` and `linkpath` metadata attached.

The output can list the new member name while still pointing a hard link at the old path, or a stale PAX header can override the requested rename entirely.

This candidate rewrites hard-link targets with the same operation, removes stale PAX path metadata so Python regenerates it from the new values, and deliberately leaves symlink targets unchanged.

## Existing work and duplicate search

- Canonical issue: #25.
- Issue #28 owns filter matching and parent retention, not member rewriting.
- Issue #29 owns no-option passthrough.
- PR #23 separately handles GNU sparse payload metadata.

## Source

- Project: imported `mmdebstrap`
- File: `upstream/mmdebstrap/tarfilter`
- Source blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Candidate patch: `tarfilter-path-rewrite-metadata.patch`

## Source and test map

The archive loop changes only `member.name` for component stripping and transforms. `member.linkname`, PAX `path`, and PAX `linkpath` remain unchanged.

The candidate:

- strips the same component count from hard-link targets;
- applies every transform to hard-link targets;
- removes stale `path` after a member rename;
- removes stale `linkpath` after a hard-link target rename;
- leaves symlink `linkname` untouched.

Python's PAX writer then regenerates long path/link headers from the corrected `TarInfo` values.

## Assertions and negative controls

`tests/test_tarfilter_path_rewrite_metadata.py`:

- reproduces the current short hard-link strip output and requires GNU tar extraction to fail;
- requires the candidate to rewrite the target and extract one shared inode;
- requires transforms to rewrite hard links while preserving symlink targets;
- creates long PAX `path` and `linkpath` values;
- proves the unmodified strip retains the stale prefixed long path;
- requires the candidate to regenerate both long headers and extract correctly.

## Evidence boundary

The candidate covers hard links whose target path can receive the same component stripping. A hard-link target with fewer components than the requested strip is omitted rather than emitted broken; broader GNU tar compatibility for unusual relative hard-link targets needs separate fixtures. GNU sparse `GNU.sparse.name` is owned by the sparse rewrite candidate, not this patch.

## Self-review

- Only hard-link targets receive member-path transforms.
- Symlink targets remain semantic link text.
- PAX metadata is regenerated rather than hand-encoded.
- Short and long names are tested under strip and transform paths.
- Extraction checks content and inode identity.

## Reusable note

See `notes/filesystems/archive-renames-must-update-reference-metadata.md`.

## Next step

Retain as a bounded local fix for issue #25. No upstream contact is authorized.
