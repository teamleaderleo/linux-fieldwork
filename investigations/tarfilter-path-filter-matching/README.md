# Correct tarfilter path matching and parent retention

## In simple words

The current path filter removes every leading `.` and `/` character before matching. That changes dotfile names and can turn traversal-looking names into unrelated absolute paths.

The re-include logic also tries to recover a literal prefix from Python's translated regular expression instead of the original glob, and checks the parent/child relationship in the wrong direction. A requested descendant can therefore lose its parent directory or symlink member.

This candidate keeps the original glob, normalizes only structural archive prefixes, and retains a parent when an included literal prefix is equal to or below that parent.

## Existing work and duplicate search

- Canonical issue: #28.
- Issue #25 is separate and owns rewriting member paths, hard-link targets, and stale PAX path metadata.
- Issue #29 is separate and owns the no-option fast path.

## Source

- Project: imported `mmdebstrap`
- File: `upstream/mmdebstrap/tarfilter`
- Source blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Candidate patch: `tarfilter-path-filter-matching.patch`

## Source and test map

`PathFilterAction` currently stores only the compiled `fnmatch.translate()` regex. `path_filter_should_skip()` then:

- uses `member.name.lstrip("./")`, which strips filename dots rather than one archive prefix;
- derives an include prefix from the translated regex;
- asks whether the parent path starts with the descendant prefix.

The candidate stores the original glob alongside the matcher, normalizes repeated leading `./` and leading `/` without touching filename dots, derives the literal prefix from the original glob, and checks whether that prefix lies at or below the excluded parent.

## Assertions and negative controls

`tests/test_tarfilter_path_filter_matching.py`:

- reproduces the unmodified `./.secret` mismatch;
- requires `/.secret` to match and `/secret` not to match;
- requires `../etc/passwd` not to be collapsed into `/etc/passwd`;
- reproduces the missing parent directory under exclude-all plus exact re-include;
- requires the repaired archive to retain the parent directory and child;
- requires the same relationship for a symlink parent without rewriting its link target.

## Evidence boundary

The literal-prefix logic covers exact and literal-leading include patterns. Patterns whose first component begins with a wildcard have no useful literal prefix and remain outside this candidate's parent-retention proof. Extraction safety for archive-created symlink parents is a separate consumer concern; this patch matches the requested archive-filter contract and does not claim safe extraction by every tool.

## Self-review

- Dotfile dots remain part of the filename.
- `../` is not silently normalized away.
- Filter ordering remains unchanged.
- Original globs are retained only for parent-prefix reasoning.
- Symlink targets are untouched; issue #25 owns link rewrite semantics.

## Reusable note

See `notes/filesystems/archive-path-normalization-must-not-change-names.md`.

## Next step

Retain as a bounded local fix for issue #28. No upstream contact is authorized.
