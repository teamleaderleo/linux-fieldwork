# Restore tarfilter no-option passthrough

## In simple words

`tarfilter` promises a byte-copy fast path when no filtering or rewrite option is active. The current condition can never be true because `argparse` always creates `strip_components` with value `None`.

As a result, a no-option call parses and reserializes the archive. Compressed inputs become uncompressed, and format-specific metadata can be changed or damaged.

This candidate makes the condition value-aware, includes every modifying option, and treats explicit zero strip/id-shift values as no-ops.

## Existing work and duplicate search

- Canonical issue: #29.
- Duplicate #27 was closed and linked to #29.
- LF-14 / PR #23 covers sparse-member rewriting when filtering is active; this investigation owns the no-operation contract.
- The imported source and current visible upstream source were checked in the issue record.

## Source

- Project: `mmdebstrap`
- Imported file: `upstream/mmdebstrap/tarfilter`
- Imported blob before the candidate: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Candidate patch: `tarfilter-no-option-passthrough.patch`

## Source and test map

After `argparse.parse_args()`, `main()` intends to call `shutil.copyfileobj()` when no operation is active. The current guard tests attribute existence for `strip_components`, but that normal argparse attribute always exists.

The existing expression also omits transforms and ID shifting, so changing only the `strip_components` term could incorrectly bypass real modifications.

## Probe and assertions

`tests/test_tarfilter_no_option_passthrough.py`:

- proves the unmodified source changes a gzip archive and removes its compression signature;
- applies the candidate patch to a temporary exact source copy;
- requires byte identity for plain, gzip, bzip2, xz, and GNU PAX sparse archives;
- requires explicit `--strip-components=0` and `--idshift=0` to remain byte-preserving;
- proves a real transform still renames the member;
- proves a real ID shift still changes numeric ownership.

The unmodified gzip case is the negative control.

## Interpretation

The fix restores the stated no-operation boundary without bypassing active transformations. It also avoids routing sparse archives into the separate Python tarfile sparse-rewrite defect when no operation was requested.

## Evidence limits

The regression covers common compression modes available through Python and one GNU PAX sparse archive. It does not cover every tar compressor, encryption wrapper, concatenated archive, malformed stream, or non-seekable transport behavior.

## Self-review

- Every modifying option is represented in the fast-path predicate.
- Explicit numeric zero is treated as a no-op consistently with the existing truthiness checks.
- Transform and nonzero ID-shift controls prove the fast path does not overmatch.
- The candidate changes only the intended source condition.

## Reusable note

See `notes/filesystems/no-op-archive-filters-must-preserve-bytes.md`.

## Next step

Retain as a bounded local fix candidate for issue #29. No upstream contact is authorized.
