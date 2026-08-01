# Draft upstream merge request

Status: `INTERNAL DRAFT — DO NOT SEND WITHOUT EXPLICIT AUTHORIZATION`

## Title

tarfilter: honor basic and extended transform regex dialects

## Summary

`tarfilter --transform` now interprets the characterized GNU basic-regex spelling by default and the characterized extended spelling when `x` is present. Patterns are translated or rejected before Python compilation, preventing silent Python-specific rename behavior.

## Changes

- select GNU basic syntax by default and extended syntax with `x`;
- translate the executed operator, group, alternation, interval, backreference, and contextual-anchor subset into Python spelling;
- preserve user capture numbering while normalizing the executed repeated-quantifier cases;
- reject Python-only active `(?...)` extensions before archive processing;
- preserve escaped-parenthesis and bracket-expression neighbors of the active-`(?` guard;
- reject malformed active intervals and proven-invalid consecutive basic intervals;
- treat an unmatched extended closing parenthesis as a literal when no group is open;
- retain composition with numeric occurrence selectors and member, hard-link, and symlink target scopes;
- add direct GNU tar differential regressions under `LC_ALL=C`.

## Why

The previous implementation passed transform patterns directly to Python `re`. GNU tar uses basic regular expressions by default, so punctuation such as `+`, `?`, `|`, parentheses, and interval braces can have the opposite meaning. The command could succeed while emitting different archive paths.

For example, default expression `s/a+/b/` on member `aaa` produced `b` through Python, while GNU tar leaves `aaa` unchanged because `+` is literal in basic mode.

## Compatibility boundary

This merge request covers the executed GNU tar 1.35 subset under `LC_ALL=C`. Unsupported POSIX bracket constructs, unresolved alphabetic escapes, expression lists, persistent flags, replacement case conversion, locale-sensitive matching, complete diagnostic parity, and regex resource policy remain outside the claim and fail early where relevant.

## Tests

The focused matrix compares candidate archive snapshots directly with GNU tar and covers:

- basic/extended operator reversal;
- captures, backreferences, and contextual anchors;
- ordinary bracket expressions and early rejection of unresolved POSIX bracket forms;
- numeric occurrence selection;
- member, hard-link, and symlink target scopes;
- branch-leading basic `*` and literal `\0`;
- nested simple and interval quantifiers;
- Python-only special groups;
- accepted guard neighbors `s/\(?/X/x`, `s/[(?]/X/x`, and `s/\(/X/x`;
- malformed active intervals;
- unmatched extended closing parentheses;
- cleanup and immediate rerun.

Historical internal receipts:

- repaired grammar head `55d20a4cc08c93b34961c679bdb73458fea4c408` passed Linux Fieldwork hosted run `30581672669` / job `625`;
- proof head `bb0a79dec47958c6b865d4b382a44baff17ab736` passed run `30582215292` / 634, direct inherited tests twice, focused current-main tests 15/15, and full regex discovery 38/38.

The final merge request must replace these historical receipts with the exact current-Salsa base/head and fresh current-source results.

## Upstream-native execution plan

The current published project runner stages local `./tarfilter` into `shared/tarfilter`. After rebasing, run the exact transform-related names selected from current `coverage.txt` and `tests/` through:

```sh
CMD=./mmdebstrap ./coverage.py --dist unstable TEST-NAME
```

Then run the appropriate broader project suite, with `./make_mirror.sh` preparation when the current test instructions require it. Record exact commands, environment, exit statuses, cleanup, and immediate rerun.

## Current preparation gates

- [ ] resolve exact current canonical Salsa `master` and `tarfilter` blob;
- [ ] rebase or regenerate without fuzz or offsets;
- [ ] record exact candidate head and complete diff;
- [ ] run focused GNU differential matrix on that head;
- [ ] run current upstream-native focused and broader entry points;
- [ ] clean generated state and rerun;
- [ ] search exact live Salsa issues and merge requests for equivalent work;
- [ ] obtain explicit authorization before creating or sending this merge request.

## Authority

Internal draft only. No Salsa fork, branch, merge request, issue, comment, review, or email has been created by this unit.
