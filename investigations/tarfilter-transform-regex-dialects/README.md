# Tarfilter transform regex dialects

## In simple words

GNU tar transforms use basic regular-expression syntax by default. The `x` flag switches one substitution to extended syntax.

The retained Linux Fieldwork transform candidate from PR #68 compiles every pattern directly with Python `re`, whose operator syntax resembles extended regular expressions, and rejects `x`. It therefore activates extended operators in default expressions while rejecting the explicit extended form.

This branch records that mismatch as executable characterization. It contains no correction patch.

## Coordination and ownership

- Parent transform record: #36.
- Bounded regex-dialect issue: #108.
- Characterization pull request: #113.
- Numeric occurrence predecessor: #98 / PR #102; its patch changes match selection and leaves regex compilation unchanged.
- Characterization branch: `investigation/tarfilter-transform-regex-dialects`.
- Imported source remains unchanged.
- No upstream contact is authorized or made.

A repository issue, PR, branch, investigation, note, and test search found no existing `x`/basic-regex candidate.

## Exact source and test boundary

- Imported source: `upstream/mmdebstrap/tarfilter`.
- Imported blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`.
- Characterized predecessor: `investigations/tarfilter-transform-target-scopes/tarfilter-transform-target-scopes.patch` from PR #68.
- Differential reference: GNU tar 1.35 under `LC_ALL=C`.
- Regression: `tests/test_tarfilter_transform_regex_dialects.py`.

The regression copies the imported source into `TemporaryDirectory`, applies the retained PR #68 patch, and compares its archive result or parser rejection directly with GNU tar.

## Confirmed operator reversal

For default basic syntax, GNU tar treats unescaped `+`, `?`, `|`, grouping parentheses, and interval braces as literals. Their escaped forms are operators. With `x`, those meanings reverse to extended syntax.

Representative results:

| Input | Expression | PR #68 predecessor | GNU tar |
| --- | --- | --- | --- |
| `aaa` | `s/a+/b/` | `b` | `aaa` |
| `aaa` | `s/a\+/b/` | `aaa` | `b` |
| `aa` | `s/a?/b/` | `ba` | `aa` |
| `aa` | `s/a\?/b/` | `aa` | `ba` |
| `ab` | `s/a|b/c/` | `cb` | `ab` |
| `ab` | `s/a\|b/c/` | `ab` | `cb` |
| `aaa` | `s/(aa)/[&]/` | `[aa]a` | `aaa` |
| `aaa` | `s/\(aa\)/[&]/` | `aaa` | `[aa]a` |
| `aaa` | `s/a{2}/b/` | `ba` | `aaa` |
| `aaa` | `s/a\{2\}/b/` | `aaa` | `ba` |
| `a^b` | `s/a^b/x/` | `a^b` | `x` |
| `a$b` | `s/a$b/x/` | `a$b` | `x` |

The predecessor rejects every tested explicit `x` expression. GNU tar executes active and escaped forms for `+`, `?`, `|`, grouping, and intervals according to extended syntax.

## Captures and backreferences

The selected dialect determines whether parentheses create capture groups. `\1` can only refer to a group created by that dialect.

- basic `s/\(a\)\1/b/` transforms `aa` to `b` in GNU tar; the Python predecessor rejects it because escaped parentheses are literals to Python and no capture group exists;
- basic `s/(a)\1/b/` is invalid in GNU tar because unescaped parentheses do not create a group; the Python predecessor transforms it to `b`;
- extended `s/(a)\1/b/x` transforms to `b` in GNU tar and is rejected by the predecessor because `x` is unsupported;
- extended `s/\(a\)\1/b/x` is invalid in GNU tar because escaped parentheses are literals.

## Shared control subset

The regression also preserves expressions whose operator meaning agrees across GNU basic syntax and Python:

- `*` repetition;
- `^` at the beginning;
- `$` at the end;
- ordinary bracket expressions such as `[a+]`.

These controls prevent the characterization from treating every regex as divergent.

## Translator requirements for a later candidate

A correction needs a pattern scanner rather than a blind replacement table:

1. recognize `x` as a transform flag;
2. leave Python-compatible extended syntax active when `x` is selected;
3. translate default GNU basic syntax into Python syntax;
4. invert escaped/unescaped operator meaning for `+`, `?`, `|`, grouping parentheses, and interval braces;
5. preserve backreferences after translated capture groups;
6. track bracket-expression state so operator translation does not run inside `[...]`;
7. treat `^` and `$` as anchors only in GNU basic anchor positions;
8. preserve escaped delimiters handled by the existing transform parser;
9. reject or separately test POSIX bracket classes, collating elements, locale ranges, GNU word-boundary escapes, and other features that Python cannot represent faithfully.

## Executable contract

```sh
python3 -m unittest tests.test_tarfilter_transform_regex_dialects -v
python3 -m unittest discover -s tests -v
```

The characterization requires:

- 12 default-dialect divergences covering active and literal `+`, `?`, `|`, grouping, intervals, and contextual anchors;
- 7 explicit-`x` predecessor rejections paired with successful GNU results;
- 4 basic/extended capture and backreference cases, including inverse validity;
- 4 shared-subset controls;
- exact patch application against the imported source.

## Validation

Initial characterization head `faf135a5b6525c63f36f6e649e2ec33b10824717` passed Linux Fieldwork CI run `30543947343`, job `90875235407`. Repository discovery ran 42 tests in 5.464 seconds; all four dialect test methods passed.

Complete-diff review found that `?` and default alternation were present in the raw observation file and PR prose but absent from the executable default-dialect matrix. Head `0e929b67d15e936af229afe0f9246a1cd8b9b956` adds active/literal `?` and `|` cases in both default and explicit-`x` matrices. Linux Fieldwork CI run `30544085794`, job `90875709615`, passed.

This validation-record commit requires one final exact-head CI receipt before independent review.

## Cleanup and evidence limits

All copied sources, files, and archives live under `TemporaryDirectory`. The test accepts no caller-selected cleanup root and performs no privileged operation.

This record establishes the dialect mismatch and a bounded translator design. It does not claim complete GNU regex compatibility. POSIX bracket classes, locale/collation behavior, GNU-specific escapes, malformed-expression parity, and performance limits remain explicit later work.

## Handoff

Start here, then read `observations.md`, the reusable note, and the regression. The source candidate should begin only after this characterization is green and PR #102 has an independent exact-head verdict, so one integrated predecessor remains canonical.
