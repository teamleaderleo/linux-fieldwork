# LF-14 old GNU sparse type normalization

## In simple words

The existing LF-14 repair converts parsed sparse tar members into GNU PAX sparse 1.0 or dense output. Old GNU sparse input carries archive type `S`, and Python keeps that type after parsing. The conversion must change the type to an ordinary regular-file member or the output combines two incompatible representations.

## Question

When `tarfilter` rewrites an old GNU sparse member, does normalizing `TarInfo.type` to `REGTYPE` produce valid PAX sparse 1.0 and dense output without changing logical contents or sparse allocation?

## Existing work and duplicate search

- Searched open and closed repository issues and pull requests for `GNUTYPE_SPARSE`, old GNU sparse type flags, and sparse normalization.
- Reuses LF-14 PR #17, sparse candidate PR #23, and issue #44.
- No separate existing candidate covers the archive type flag.

## Source

- Project: imported Debian `mmdebstrap`
- Requested revision: `debian/1.5.7-3`
- Resolved upstream commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Imported source blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Candidate base head: `dd0566ed5e7fa13252dc856cbb5c1c205980135b`
- Candidate branch: `fix/lf-14-old-gnu-sparse-typeflag`
- Local source path: `upstream/mmdebstrap/tarfilter`
- Retained source patch: `programmes/filesystems-images/lanes/LF-14-archive-extraction-metadata-contracts/scouts/LF-SCOUT-FS-01/artifacts/mmdebstrap-tarfilter-preserve-gnu-sparse.patch`

## Source and test map

- `TarInfo._proc_sparse()` in Python's `tarfile` parser records old GNU extents but retains type `GNUTYPE_SPARSE`.
- `TarInfo._proc_pax()` and `_apply_pax_info()` parse GNU PAX sparse 1.0 metadata on a regular-file member.
- The LF-14 candidate enters its rewrite branch for every `member.sparse is not None`.
- `TarFile.addfile()` serializes the retained `member.type`; clearing `member.sparse` alone does not change the archive type.
- Existing test `tests/test_lf14_sparse_repair.py` only generated `tar --format=pax --sparse` input.
- The missing assertion was an old GNU input whose repaired output must have `member.type == tarfile.REGTYPE` in both sparse and dense cases.

## Environment

Target execution is the repository's Ubuntu 24.04 GitHub Actions job with GNU tar and Python recorded by the existing LF-14 runner. Exact workflow run and tool versions will be added after the stacked pull request executes.

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

The pre-repair candidate clears or replaces sparse metadata but does not change `member.type`, so it cannot satisfy the normalized regular-file representation invariant.

## Hypothesis or candidate

Set:

```python
member.type = tarfile.REGTYPE
```

once after confirming `member.sparse is not None` and before choosing sparse or dense output.

Expected distinguishing outcomes:

- unmodified rewriter does not meet the regular-file sparse invariant;
- repaired old GNU sparse output lists and extracts successfully;
- repaired sparse output parses as regular-file plus a non-empty sparse map;
- repaired dense output parses as regular-file with no sparse map or `GNU.sparse.*` headers;
- both outputs preserve complete logical contents;
- sparse output remains compact and extracts sparsely;
- the existing PAX sparse matrix remains green.

## Reproduction

```sh
python3 -m unittest tests.test_lf14_sparse_repair
```

The test generates the old GNU fixture, executes the unmodified negative control, applies the retained source patch to a temporary copy, runs the complete LF-14 matrix, and executes old GNU sparse and dense controls.

## Assertions and negative control

The regression asserts source type `GNUTYPE_SPARSE`, then runs the unmodified rewriter and requires that its output does not satisfy `REGTYPE` plus parsed sparse state. This is the deliberate negative control.

The repaired assertions cover exit status, GNU tar listing and extraction, Python member type, sparse metadata state, SHA-256 equality, sparse allocation, and archive size.

## Results

Pending exact-head GitHub Actions execution.

## Cleanup and rerun

All generated archives, extracted roots, and patched source copies are inside `TemporaryDirectory`. The test leaves no package state, mount, process, lock, or retained temporary path. Immediate rerun evidence will be recorded from CI.

## Interpretation

Pending execution. Source review establishes that type normalization is necessary whenever the repair converts an old GNU sparse member into PAX sparse 1.0 or dense representation.

## Evidence boundary

- One old GNU dialect produced by current GNU tar `--format=gnu --sparse` is covered.
- Other historical GNU sparse dialects, malformed maps, overlapping or unsorted extents, and non-GNU readers remain outside this probe.
- The retained patch is applied to a temporary copy; imported upstream source remains unchanged.

## Self-review

- Complete stacked diff: pending after final CI adjustments.
- Failure and cleanup paths: temporary directories and nonzero subprocess assertions inspected.
- Destructive path safety: no caller-controlled recursive deletion added.
- Repeated execution: designed for isolated repeat runs.
- Claims versus evidence: result language remains pending until exact-head execution.

## Peer review

PR #23 exact-head review at `dd0566ed5e7fa13252dc856cbb5c1c205980135b` identified this gap. The stacked repair requires re-review after execution.

## Reusable notes

Updated `notes/filesystems/rewriting-gnu-pax-sparse-members.md` with the archive type-flag rule and old GNU control.

## Next step

Open a stacked pull request against PR #23's branch, run exact-head CI, update this record with results, and request re-review.

## Authority

No upstream issue, email, merge request, patch submission, comment, review, or other interaction is authorized or performed.
