# LF-14 old GNU sparse type normalization

## In simple words

The existing LF-14 repair converts parsed sparse tar members into GNU PAX sparse 1.0 or dense output. Old GNU sparse input carries archive type `S`, and Python keeps that type after parsing. The conversion must change the type to an ordinary regular-file member or the output combines two incompatible representations.

The bounded repair and regression passed twice on the same exact head.

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
- Candidate head: `5476c2db54a639a29aa89e72ae4766c4251dce29`
- Pull request merge test commit: `d13c5244a084c2f1eb875d8bea9a147326e6d2a7`
- Candidate branch: `fix/lf-14-old-gnu-sparse-typeflag`
- Stacked pull request: #45
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

- GitHub Actions workflow: `Linux Fieldwork CI`
- Run: `30533527764`
- Initial job: `90841200004`
- Same-head rerun job: `90841605019`
- Runner OS: Ubuntu `24.04.4 LTS`
- Runner image: `ubuntu-24.04`, version `20260720.247.2`
- Runner version: `2.336.0`
- Git: `2.54.0`
- Privileges: ordinary GitHub-hosted workflow user

The exact Python and GNU tar version strings were not separately printed by this job. The exact runner image and source head are retained; adding explicit tool-version output is a provenance improvement rather than a result blocker.

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

The unmodified rewriter was executed before applying the candidate patch. The regression required that its output did not satisfy the normalized `REGTYPE` plus parsed-sparse invariant. That negative control passed.

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

Both exact-head jobs succeeded:

- initial `lab-tools` job `90841200004`: success;
- same-head rerun `lab-tools` job `90841605019`: success.

The successful unit-test step establishes, for the generated old GNU fixture:

- the source member is parsed as type `S` with a sparse map;
- the unmodified negative control does not satisfy the repaired invariant;
- repaired sparse output lists and extracts successfully;
- repaired sparse output is a regular-file member with parsed sparse state;
- repaired sparse contents equal the original sparse file;
- repaired sparse extraction remains sparse and the archive remains compact;
- repaired dense output is a regular-file member with no parsed sparse state or `GNU.sparse.*` headers;
- repaired dense contents equal the original sparse file;
- the inherited PAX sparse and nine-fixture LF-14 matrix remains green.

## Cleanup and rerun

All generated archives, extracted roots, and patched source copies are inside `TemporaryDirectory`. The test leaves no package state, mount, process, lock, or retained temporary path.

The same exact workflow head was rerun immediately and passed again in job `90841605019`, providing repeat and cleanup evidence.

## Interpretation

For the old GNU sparse dialect emitted by current GNU tar in the runner image, normalizing the output type to `REGTYPE` completes the representation conversion. The same one-line normalization is required for both PAX sparse 1.0 output and dense fallback.

The repair is deliberately stacked on PR #23. It changes no imported source directly; it updates the retained candidate patch and regression.

## Evidence boundary

- One old GNU dialect produced by current GNU tar `--format=gnu --sparse` is covered.
- Other historical GNU sparse dialects, malformed maps, overlapping or unsorted extents, and non-GNU readers remain outside this probe.
- The retained patch is applied to a temporary copy; imported upstream source remains unchanged.
- Exact Python and GNU tar version strings were not emitted separately from the pinned runner image.

## Self-review

- Exact reviewed head: `5476c2db54a639a29aa89e72ae4766c4251dce29`.
- Complete five-file stacked diff inspected against `dd0566ed5e7fa13252dc856cbb5c1c205980135b`.
- Semantic source change is one type normalization before both output branches.
- The test asserts the source dialect, negative control, sparse branch, dense branch, content, type, metadata, allocation, archive size, listing, and extraction.
- Failure and cleanup paths use nonzero subprocess assertions and `TemporaryDirectory`.
- No caller-controlled recursive deletion, privilege expansion, mount, package mutation, or persistent path was added.
- Same-head repeated execution passed.
- Documentation claims were compared with the exact executed head and remain bounded to the tested dialect.

## Peer review

PR #23 exact-head review at `dd0566ed5e7fa13252dc856cbb5c1c205980135b` identified this gap. PR #45 is ready for exact-head re-review after the successful initial and repeat jobs.

## Reusable notes

Updated `notes/filesystems/rewriting-gnu-pax-sparse-members.md` with the archive type-flag rule and old GNU control.

## Next step

Re-review PR #45, then fold the validated type normalization and regression into PR #23 before the sparse candidate advances.

## Authority

No upstream issue, email, merge request, patch submission, comment, review, or other interaction is authorized or performed.
