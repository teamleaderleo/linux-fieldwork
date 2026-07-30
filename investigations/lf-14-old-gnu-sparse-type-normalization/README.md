# LF-14 old GNU sparse type normalization

## In simple words

The LF-14 repair converts parsed sparse tar members into GNU PAX sparse 1.0 or dense output. Old GNU sparse input carries archive type `S`, and Python keeps that type after parsing. The conversion must change the output member to an ordinary regular-file type or it combines incompatible representations.

## Question

When `tarfilter` rewrites an old GNU sparse member, does normalizing `TarInfo.type` to `REGTYPE` produce valid PAX sparse 1.0 and dense output without changing logical contents or sparse allocation?

## Existing work and duplicate search

- Reuses merged LF-14 corpus PR #17 and sparse repair PR #85.
- Tracks issue #44.
- Supersedes the old stacked candidate PR #45 with a clean current-main branch.
- No separate candidate covered the archive type flag.

## Source boundary

- Project: imported Debian `mmdebstrap`
- Requested revision: `debian/1.5.7-3`
- Resolved upstream commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Imported source blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Local source path: `upstream/mmdebstrap/tarfilter`
- Retained source patch: `programmes/filesystems-images/lanes/LF-14-archive-extraction-metadata-contracts/scouts/LF-SCOUT-FS-01/artifacts/mmdebstrap-tarfilter-preserve-gnu-sparse.patch`

The imported source remains unchanged. The regression applies the retained patch to an exact temporary copy.

## Source and test map

- `TarInfo._proc_sparse()` records old GNU extents but retains type `GNUTYPE_SPARSE`.
- GNU PAX sparse 1.0 is represented on a regular-file member.
- `TarFile.addfile()` serializes the retained `member.type`; clearing `member.sparse` alone does not change that type.
- The missing assertion was an old GNU input whose repaired sparse and dense outputs must both have `member.type == tarfile.REGTYPE`.

## Baseline behavior

A fixture generated with:

```sh
tar --format=gnu --sparse -cf old-gnu-sparse.tar old-gnu-source
```

parses as:

```python
member.type == tarfile.GNUTYPE_SPARSE
member.sparse is not None
```

The regression executes the unmodified rewriter before applying the candidate and requires that its output does not satisfy the normalized `REGTYPE` plus parsed-sparse invariant.

## Candidate

Set:

```python
member.type = tarfile.REGTYPE
```

once after confirming `member.sparse is not None` and before choosing sparse or dense output.

Expected distinguishing outcomes:

- unmodified rewriter does not meet the regular-file sparse invariant;
- repaired old GNU sparse output lists and extracts successfully;
- repaired sparse output parses as a regular-file member plus a non-empty sparse map;
- repaired dense output parses as a regular-file member with no sparse map or `GNU.sparse.*` headers;
- both outputs preserve complete logical contents;
- sparse output remains compact and extracts sparsely;
- the existing PAX sparse matrix remains green.

## Reproduction

```sh
python3 -m unittest tests.test_lf14_sparse_repair -v
```

The test generates the old GNU fixture, executes the unmodified negative control, applies the retained source patch to a temporary copy, runs the complete LF-14 matrix, and exercises old GNU sparse and dense output paths.

## Assertions

The repaired controls cover exit status, GNU tar listing and extraction, Python member type, sparse metadata state, SHA-256 equality, sparse allocation, archive size, and dense fallback cleanup.

## Cleanup and safety

All generated archives, extracted roots, and patched source copies are inside `TemporaryDirectory`. The test leaves no package state, mount, process, lock, or retained temporary path.

## Evidence boundary

- One old GNU dialect produced by current GNU tar `--format=gnu --sparse` is covered.
- Other historical GNU sparse dialects, malformed maps, overlapping or unsorted extents, and non-GNU readers remain outside this probe.
- The retained patch is applied only to a temporary copy.

## Authority

Internal Linux Fieldwork work only. No upstream issue, email, merge request, patch submission, comment, review, or other interaction is authorized or performed.
