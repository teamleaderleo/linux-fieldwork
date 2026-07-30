# Tarfilter transform target scopes

## In simple words

GNU tar transforms three kinds of text by default: archive member names, hard-link targets, and symlink targets. The merged Linux Fieldwork candidate from PR #48 rewrites hard-link targets but deliberately leaves symlink targets unchanged, and its regression records that divergence as success.

This follow-up retains one integrated local candidate that combines the reviewed replacement-count behavior from PR #56 with corrected transform target scopes and the hard-link/PAX metadata repairs from PR #48.

## Existing work and duplicate search

Searched open and closed issues, pull requests, investigations, notes, tests, and the imported source.

- PR #48 / issue #25: hard-link target and stale PAX path/linkpath repair.
- PR #56 / issues #36 and #51: replacement count, `g`/`i`, `&`, and escaped replacement characters.
- Issue #63: post-merge report for the wrong symlink-scope regression.
- PR #52: superseded stacked replacement-count candidate.

No separate candidate covered correct default target scopes plus the reviewed replacement and reference-metadata behaviors.

## Exact source boundary

- Imported file: `upstream/mmdebstrap/tarfilter`
- Imported blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Candidate branch: `fix/tarfilter-transform-target-scopes`
- Candidate patch: `tarfilter-transform-target-scopes.patch`
- Corrected regression: `tests/test_tarfilter_path_rewrite_metadata.py`
- Pull request: #68

The imported file remains unchanged. The test applies the retained integrated patch to an exact temporary copy.

## Source and test map

The candidate parses each transform into:

- compiled regex;
- sed-style replacement callable;
- replacement count;
- target scopes for member names (`r`), symlink targets (`s`), and hard-link targets (`h`).

Default scopes are `rsh`. Lowercase scope flags enable a target and uppercase `R`, `S`, or `H` disable it. The transform loop applies one parsed transform consistently to `member.name` and the applicable `member.linkname`, then removes stale PAX `path` or `linkpath` for regeneration.

The same patch retains component-strip hard-link rewriting and stale PAX cleanup from PR #48.

## Executable contract

The corrected regression creates:

- `prefix/target`, a regular file;
- `prefix/hard -> prefix/target`, a hard link;
- `prefix/sym -> prefix/target`, a symlink entry.

For `s,^prefix/,,`, candidate and GNU tar must both produce:

- member names `target`, `hard`, and `sym`;
- hard-link target `target`;
- symlink target `target`.

For `s,^prefix/,,S`, candidate and GNU tar must both keep the symlink target as `prefix/target` while still transforming member names and the hard-link target.

The default candidate archive must extract successfully, preserve hard-link inode identity, and leave `sym -> target`.

## Negative control

The exact retained PR #48 patch is applied separately. Its default transform produces `sym -> prefix/target`, proving the stale merged behavior before the integrated candidate is evaluated.

## Commands

```sh
python3 -m unittest tests.test_tarfilter_path_rewrite_metadata -v
```

Repository test discovery also runs the corrected regression and adjacent tarfilter candidates.

## Validation

Linux Fieldwork CI run `30536021112` passed on Ubuntu 24.04 against exact candidate head `155217c61c740ace30d3b56e947b792d48bad544`.

The run passed 15 tests. The corrected scope test applied both the stale PR #48 patch and the integrated candidate, required the stale default result as a negative control, matched candidate archives to GNU tar for default and `S`, extracted the default archive, verified hard-link inode identity, and required `sym -> target`. Adjacent no-option, path-filter, replacement-semantics, LF-07 safety, and LF-23 safety regressions also passed. Shell syntax and optional command-help checks passed.

## Evidence limits

- This follow-up establishes default `rsh` behavior and uppercase `S` using GNU tar as the differential reference.
- The candidate parses `r/R`, `s/S`, and `h/H`, but the executable differential matrix centers on default and `S` because those repair the merged defect.
- Numeric occurrence selectors, `x`, complete BRE differences, case-conversion escapes, and other GNU transform extensions remain in issue #36.
- Sparse-member encoding remains in PR #23/#45.
- The result is a retained local candidate; no imported or upstream source is modified.

## Cleanup and safety

All patch applications, fixture trees, reference archives, and extraction targets live under `TemporaryDirectory`. The test accepts no caller-selected deletion root.

## Self-review

- Read the current merged test and both retained candidate patches.
- Preserved the original wrong result as an asserted negative control.
- Compared archives against GNU tar instead of relying only on hard-coded expectations.
- Covered archive metadata and extracted filesystem effects.
- Kept the claim narrower than complete GNU tar transform compatibility.
- Separated this post-merge correction from the already completed replacement-count issue #51.
- Exact-head CI passed the complete current repository test set.

## Authority

No upstream contact is authorized or made.
