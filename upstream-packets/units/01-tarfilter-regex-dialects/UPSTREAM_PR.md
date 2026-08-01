# Draft upstream merge request

Status: `INTERNAL DRAFT — DO NOT SEND WITHOUT EXPLICIT AUTHORIZATION`

## Title

tarfilter: honor basic and extended transform regex dialects

## Summary

`tarfilter --transform` now uses the characterized GNU basic-regex spelling by default and extended spelling when `x` is present. The parser translates the supported subset before Python compilation and rejects unresolved forms before archive output.

## Changes

- add explicit basic/extended transform dialect selection;
- translate operators, groups, alternation, intervals, backreferences, and contextual anchors;
- preserve capture numbering while normalizing the executed nested-quantifier forms;
- reject active Python-only `(?...)` extensions;
- preserve escaped-parenthesis and bracket-expression neighbors of that guard;
- reject malformed active intervals and proven-invalid consecutive basic intervals;
- treat unmatched extended `)` as literal when no group is open;
- compose with replacement, target-scope, PAX, and numeric-occurrence behavior;
- add direct GNU tar differential coverage.

## Why

The previous source passed GNU-style transform patterns directly to Python `re`. For member `aaa`, default expression `s/a+/b/` therefore produced `b`; GNU tar basic mode leaves `aaa` unchanged because `+` is literal. Similar silent differences affect grouping, alternation, intervals, anchors, and link targets.

## Candidate series

1. transform metadata/occurrence prerequisite;
2. regenerated regex dialect patch.

The exact current internal candidate is built from source blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` and produces blob `ca8e656c036172230c796a8a12cb17f262108c39`.

The historical regex patch was regenerated because its old context applied two hunks with offsets and failed the final parser hunk after the clean prerequisite. The retained series applies with zero fuzz and no offsets.

## Validation completed

Environment:

```text
Python 3.13.5
GNU tar 1.35
LC_ALL=C
```

Results:

- exact base, prerequisite, and candidate blobs verified;
- both patches applied with `patch --fuzz=0`, zero offsets;
- Python compilation passed;
- baseline and prerequisite mismatch controls passed;
- 41 candidate/GNU successful comparisons passed;
- two numeric-occurrence/link-scope comparisons passed;
- 11 shared rejection comparisons passed;
- three explicit unsupported-POSIX boundary comparisons passed;
- a freshly materialized representative gate passed twice with an identical digest;
- temporary source and archive state was removed.

## Compatibility boundary

This change covers the executed GNU tar 1.35 subset under `LC_ALL=C`. POSIX classes, collating/equivalence forms, locale-sensitive matching, GNU alphabetic escapes, expression lists, persistent flags, replacement case conversion, full diagnostics, and regex resource policy remain outside the claim.

## Preparation gates remaining

- [ ] port or select upstream-native transform tests;
- [ ] run focused native tests through current `coverage.py`;
- [ ] run the appropriate broader native gate;
- [ ] compose selected independent tarfilter units and review the combined diff;
- [ ] resolve exact canonical Salsa head and live issue/MR overlap;
- [ ] create the candidate branch and compare URL;
- [ ] obtain explicit authorization before any upstream write.

## Authority

Internal draft only. No Salsa issue, merge request, branch, comment, review, email, or mailing-list post has been created by this unit.
