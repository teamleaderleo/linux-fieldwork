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

The retained focused matrix compares candidate archive snapshots directly with GNU tar and covers:

- basic/extended operator reversal;
- captures, backreferences, and contextual anchors;
- ordinary bracket expressions and early rejection of unresolved POSIX bracket forms;
- numeric occurrence selection;
- member, hard-link, and symlink target scopes;
- branch-leading basic `*` and literal `\0`;
- nested simple and interval quantifiers;
- Python-only special groups;
- malformed active intervals;
- unmatched extended closing parentheses;
- cleanup and immediate rerun.

Historical internal receipt: repaired head `55d20a4cc08c93b34961c679bdb73458fea4c408` passed Linux Fieldwork hosted run `30581672669` / job `625`. The final merge request must replace this section with exact current-Salsa base/head, upstream-native commands, and fresh results.

## Current preparation gates

- [ ] rebase/regenerate against exact current canonical Salsa `master`;
- [ ] record exact candidate head and complete diff;
- [ ] run focused GNU differential matrix on that head;
- [ ] run current upstream-native test entry points;
- [ ] clean generated state and rerun;
- [ ] search current issues and merge requests for equivalent work;
- [ ] obtain explicit authorization before creating or sending this merge request.

## Authority

Internal draft only. No Salsa fork, branch, merge request, issue, comment, review, or email has been created by this unit.
