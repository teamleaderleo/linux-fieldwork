# Reject Python-only transform group syntax

## In simple words

The tarfilter regex candidate translates GNU tar basic and extended transform patterns into Python regular expressions. Explicit extended mode previously passed every unescaped `(?...)` form through to Python, activating lookahead, noncapturing groups, inline flags, and named groups that GNU tar rejects.

This focused repair rejects the Python special-group namespace before compilation while preserving escaped literal parentheses and bracket-expression content.

## Canonical records

- parent issue: #108
- canonical candidate: PR #151
- independent blocking review: PR #151 review `4822922810`
- predecessor exact head: `7f1865e48b77b89d4989b7de0fe4b85bad4377ec`
- repair branch: `repair/tarfilter-reject-python-groups`
- repair patch: `../tarfilter-transform-regex-candidate/tarfilter-transform-regex-python-groups.patch`
- executable regression: `../../tests/test_tarfilter_transform_regex_python_groups.py`
- authority: internal Linux Fieldwork work only

## Reproduced mismatch

Under GNU tar 1.35 with `LC_ALL=C`, all four explicit-extended transforms fail with status 2:

```text
s/a(?=b)/X/x
s/(?:a)/X/x
s/(?i)a/X/x
s/(?P<n>a)/X/x
```

The predecessor candidate handed these patterns to Python `re.compile()`. Python then performed substitutions, including case-insensitive matching from `(?i)` without the GNU transform `i` flag.

## Repair

After bracket expressions and before escape/operator translation, the candidate checks for an active `(` immediately followed by `?` in explicit extended mode. That sequence raises a focused `ValueError` before archive output.

The rule deliberately leaves these controls available:

- `\(` remains an escaped literal parenthesis;
- `?` following that literal remains an ordinary ERE quantifier;
- `(` and `?` inside a bracket expression remain bracket members;
- internally generated `(?:...)` wrappers for repeated-quantifier normalization are created after source translation and remain implementation-only.

## Regression

The new test subclasses the complete regex edge-case matrix, applies the focused repair after the two canonical candidate patches, and therefore reruns every inherited dialect, anchor, capture, backreference, occurrence, member, hard-link, symlink, repeated-quantifier, and interval case.

It adds:

1. direct GNU differential rejection for lookahead, noncapturing, inline-flag, and named-group forms;
2. zero candidate archive bytes on rejection;
3. the focused candidate diagnostic without claiming GNU diagnostic-text parity;
4. positive controls for an escaped parenthesis with `?` and for bracket content containing `(` and `?`;
5. a source-contract assertion for the bounded guard.

Focused command:

```text
python3 -m unittest -v tests/test_tarfilter_transform_regex_python_groups.py
```

Complete discovery and exact-head Linux Fieldwork CI remain required before promotion.

## Evidence boundary

This repair closes the active Python `(?...)` namespace in the explicit-extended slice. POSIX bracket classes and collation, locale and encoding parity, GNU-specific alphabetic escapes, malformed-expression diagnostic parity, and unexecuted interval combinations remain separate gaps.

The branch starts from PR #151's reviewed predecessor head. Current-main restacking and its own exact-head rerun remain required before any final landing decision.

## External contact

No Debian, GNU, mmdebstrap, mailing-list, issue, email, patch, merge request, comment, or review outside controlled `teamleaderleo/*` repositories is authorized or included.
