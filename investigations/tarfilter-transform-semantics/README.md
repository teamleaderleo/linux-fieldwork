# Tarfilter GNU transform semantics

## In simple words

`tarfilter --transform` says it behaves like GNU tar's sed-style rename option. The imported implementation currently replaces every match, rejects the `g` flag, and treats `&` as a literal character. A local candidate keeps the existing Python regular-expression boundary while matching GNU tar for substitution count, `g` and `i` flags, whole-match `&`, and escaped replacement characters.

## Existing work and duplicate search

Searched open and closed issues, pull requests, LF-14 records, investigations, notes, and the imported source.

- Canonical issue: #36 — broader GNU tar/sed transform mismatch.
- Focused duplicate: #51 — first-only default and `g`/`i` flag handling.
- Related path-reference work: #25 and PR #48.
- Related path-filter work: #28 and PR #47.
- Related no-option work: #29 and PR #46.
- Related sparse work: PR #23 and PR #45.

Those candidates own separate boundaries. No active branch covered transform replacement semantics when this work began.

## Exact source boundary

- Repository: `teamleaderleo/linux-fieldwork`
- Imported file: `upstream/mmdebstrap/tarfilter`
- Imported blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Source owner: `TransformAction` and the transform loop in `main()`
- Candidate branch: `fix/tarfilter-gnu-transform-semantics`
- Candidate patch: `tarfilter-gnu-transform-semantics.patch`
- Candidate pull request: #56

The patch is retained and applied to an exact temporary source copy by the regression. The imported file remains unchanged.

## Source and test map

`TransformAction` currently parses only an optional trailing `i`, stores `(compiled_regex, replacement)`, and later calls `regex.sub(replacement, member.name)`. Python replaces all matches when `count` is omitted and does not give sed's unescaped `&` its whole-match meaning.

`tests/test_tarfilter_transform_semantics.py`:

1. creates one PAX archive member named `a/a`;
2. proves the unmodified filter changes `s/a/b/` to `b/b` and rejects `s/a/b/g`;
3. applies the candidate patch to an exact temporary copy;
4. runs the same expressions through the candidate and GNU tar;
5. compares the resulting member names;
6. requires duplicate and unsupported flags to fail.

## Candidate behavior

The candidate:

- parses the pattern, replacement, and flags without a regex-based token split;
- defaults to one replacement;
- uses unlimited replacements only with `g`;
- accepts `i`, `g`, `gi`, and `ig`;
- rejects unsupported or duplicate flags;
- expands unescaped `&` to the complete match;
- preserves literal `&`, backslash, and delimiter characters when escaped;
- retains the existing Python regular-expression pattern dialect.

## Differential matrix

The executable regression requires these names to match GNU tar:

| Expression | Input | Expected |
|---|---|---|
| `s/a/b/` | `a/a` | `b/a` |
| `s/a/b/g` | `a/a` | `b/b` |
| `s/A/b/i` | `a/a` | `b/a` |
| `s/A/b/gi` | `a/a` | `b/b` |
| `s/A/b/ig` | `a/a` | `b/b` |
| `s/a/[&]/` | `a/a` | `[a]/a` |
| `s/a/\&/` | `a/a` | `&/a` |
| `s#a#x\#y#` | `a/a` | `x#y/a` |
| `s#a#\\#` | `a/a` | `\/a` |

Invalid `gg`, `ii`, `x`, and `gix` flag strings must exit nonzero.

## Commands

```sh
python3 -m unittest tests.test_tarfilter_transform_semantics -v
```

The repository CI discovery command also runs the test.

## Validation

Linux Fieldwork CI run `30535166174` passed on Ubuntu 24.04 against candidate code head `640f414cb18cf47b3e803856392c720414bea333`.

The run compiled the test suite, applied the retained patch to an exact temporary source copy, and passed all nine discovered tests. The transform differential test passed alongside the active no-option passthrough and path-reference regressions. The shell syntax and optional command-help checks also passed.

The first candidate run, `30535026893`, failed before semantic execution because the retained unified diff had an incorrect hunk count. Commit `640f414cb18cf47b3e803856392c720414bea333` corrected that packaging defect; no source-logic change was required.

## Negative control

The exact unmodified source must produce `b/b` for `s/a/b/` and reject `s/a/b/g`. The candidate matrix can pass only after the patch applies.

## Evidence limits

- The candidate corrects substitution count, `g`/`i` flags, matched-text `&`, and the listed replacement escapes.
- The pattern remains Python regular-expression syntax. GNU tar's complete sed/BRE grammar, address selection, transform scope flags, case-conversion escapes, and every sed replacement extension remain outside this candidate.
- The regression compares archive member names. Hard-link and PAX reference metadata are owned by issue #25 and PR #48.
- GNU tar is the differential reference; other tar implementations remain outside the test.
- No upstream source or tracker is modified.

## Cleanup and safety

The test uses `TemporaryDirectory`, copies one source file into a disposable candidate tree, and applies the retained patch there. It does not accept or recursively delete a caller-provided path.

## Self-review

- Exact imported blob and source owner recorded.
- Baseline behavior is an asserted negative control.
- Candidate behavior is compared against GNU tar, not a hand-written expectation alone.
- Invalid flags are asserted.
- Work is separated from the active sparse, path-filter, path-reference, and no-option branches.
- Claims remain narrower than full sed compatibility.
- The initial malformed retained patch was caught by CI and corrected before the semantic result was claimed.

## Disposition

Keep a local candidate fix and regression. Merge authority remains inside Linux Fieldwork. No upstream contact is authorized.
