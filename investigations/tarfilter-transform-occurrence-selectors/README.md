# Tarfilter transform occurrence selectors

## In simple words

GNU tar lets the transform flag field select a numbered regex match. The retained Linux Fieldwork candidate from PR #68 rejects every digit as an unsupported flag.

This follow-up keeps the imported source untouched and retains a small incremental patch over the PR #68 candidate. The patch models a numeric selector as a match start point and keeps `g` as the decision to continue replacing after that point.

## Coordination and ownership

- Parent compatibility record: #36.
- Bounded defect: #98.
- Candidate pull request: #102.
- Replacement-language predecessor: PR #56.
- Target-scope and reference-metadata predecessor: PR #68.
- Branch: `fix/tarfilter-transform-occurrence-selectors`.
- Investigation owner: `teamleaderleo`; formal peer review remains pending.
- No upstream contact is authorized or made.

A repository issue/PR/file/branch search found no existing numeric-occurrence candidate. Existing LF-14 transform work mentions the missing feature only as a future boundary.

## Exact source boundary

- Imported file: `upstream/mmdebstrap/tarfilter`.
- Imported blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`.
- Base retained patch: `investigations/tarfilter-transform-target-scopes/tarfilter-transform-target-scopes.patch`.
- Base patch blob at branch creation: `1703984aa0c030e5131618a3541ee85bfd68ec65`.
- Incremental patch: `tarfilter-transform-occurrence-selectors.patch`.
- Regression: `tests/test_tarfilter_transform_occurrences.py`.
- Differential reference: GNU tar 1.35.

The test copies the exact imported file into a temporary repository, applies the PR #68 patch, and then applies this occurrence-selector patch. The imported tree remains unchanged. Keeping the patch incremental preserves the predecessor failure and avoids a second competing copy of the already-reviewed transform implementation.

## Reference contract

GNU tar documents a decimal transform flag as selecting only that numbered match. When `g` and a number are combined, matches before the selected number remain unchanged and every match from the selected one onward is replaced.

The local GNU tar 1.35 differential probe also established these parser details:

| Expression | Input `a/a/a/a` | Result |
| --- | --- | --- |
| `s/a/b/2` | second only | `a/b/a/a` |
| `s/a/b/2g` | second onward | `a/b/b/b` |
| `s/a/b/g2` | second onward | `a/b/b/b` |
| `s/a/b/0` | ordinary first-match default | `b/a/a/a` |
| `s/a/b/0g` | ordinary global default | `b/b/b/b` |
| `s/a/b/22` | no twenty-second match | `a/a/a/a` |
| `s/a/b/2g3` | last decimal run selects third | `a/a/b/b` |
| `s/A/b/2gi3` | case-insensitive, third onward | `a/a/b/b` |

A contiguous decimal string is one selector. When several decimal runs occur, the last completed run controls the start point. The wider exploratory output is retained in `observations.md`.

## Candidate mechanism

The predecessor stores regex, replacement callable, first/global count, and target scopes. Python's `re.sub(..., count=N)` cannot express “replace only the Nth match”: it replaces the first N matches.

The incremental candidate instead stores:

- compiled regex;
- sed-style replacement callable;
- numeric occurrence selector;
- whether `g` continues replacement after the selector;
- member/symlink/hard-link target scopes.

`_sed_substitute()` counts matches for one input string:

1. selectors greater than zero start at that match;
2. zero and an absent selector start at the first match;
3. matches before the start point are returned unchanged;
4. the selected match is replaced;
5. later matches are replaced only when `g` is active.

The counter resets independently for every member name, hard-link target, and symlink target. This matches GNU tar's per-field behavior and prevents a member-name match count from leaking into its link target.

## Executable contract

`tests/test_tarfilter_transform_occurrences.py` requires:

- the PR #68 predecessor to reject `s/a/b/2`, proving the new patch is necessary;
- ordinary first/global behavior to remain unchanged;
- numeric-only, numeric-plus-global, zero, flag-order, large selector, case-insensitive, and repeated-decimal-run cases to equal GNU tar;
- `s/a/b/2g` to apply independently to a regular member name, hard-link target, and symlink target;
- the candidate archive metadata to equal a GNU tar archive created from the same file/link fixture.

Focused and complete commands:

```sh
python3 -m unittest tests.test_tarfilter_transform_occurrences -v
python3 -m unittest discover -s tests -v
```

Repository discovery runs this alongside the existing substitution, scope, path, sparse, Debian/security, and safety regressions.

## Validation result

Candidate code head `8c3ba696310fe0a631c74749df08055677fd109e` passed Linux Fieldwork CI run `30542362599`, job `90869929455`.

- 41 repository tests passed in 4.853 seconds.
- all three focused occurrence-selector tests passed;
- patch composition passed;
- the predecessor rejection passed;
- the GNU tar name and link-target matrix passed;
- adjacent LF-14 and repository safety tests passed.

`RESULTS.md` retains the exact run and merge-ref receipt. Documentation-only consolidation commits follow the validated code head, so the final complete head needs one more CI receipt before merge.

## Evidence limits

- This candidate covers numeric occurrence selectors and their interaction with `g`, `i`, and the already-retained target scopes.
- Existing explicit rejection of duplicate letter flags remains unchanged, even where GNU tar may tolerate repeated flags.
- `x`, `flags=` statements, semicolon-separated expressions, complete BRE translation, case-conversion escapes, and the wider GNU sed replacement language remain in #36.
- The result is a retained local patch and differential regression, not a proposal against the imported source.

## Cleanup and rerun

Every copied source tree, patched candidate, input fixture, GNU reference archive, and output archive lives below `TemporaryDirectory`. The regression accepts no caller-selected cleanup root and performs no privileged operation.

## Self-review and handoff

- searched existing issues, PRs, branches, investigations, notes, and tests;
- read the imported parser, PR #68 integrated patch, and adjacent differential tests;
- retained the predecessor failure as an executable negative control;
- compared supported results directly with GNU tar;
- checked member and link-target state, not only command exit codes;
- consolidated the durable record to avoid a directory of tiny overlapping files;
- recorded unsupported grammar separately instead of presenting full GNU transform compatibility;
- retained a reusable note for later transform parsers.

To resume: read this file, `observations.md`, and `RESULTS.md`; then inspect the incremental patch and regression. Apply the PR #68 patch first, then the occurrence patch.

After #98, the next bounded slices under #36 are:

1. extended-regex `x` and the Python/GNU regex-dialect boundary;
2. persistent `flags=` scope statements and semicolon-separated expression parsing;
3. GNU sed case-conversion replacement escapes;
4. remaining BRE and backreference compatibility.

Each should receive its own issue, predecessor negative control, differential matrix, investigation, and reusable note.
