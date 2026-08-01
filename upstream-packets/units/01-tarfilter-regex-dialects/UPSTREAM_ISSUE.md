# Draft upstream issue

Status: `INTERNAL DRAFT — DO NOT SEND WITHOUT EXPLICIT AUTHORIZATION`

## Title

tarfilter --transform interprets default GNU basic expressions as Python regex

## Description

`tarfilter --transform` documents sed expressions compatible with GNU tar, but the current parser passes the pattern directly to Python `re`. GNU tar uses basic regular expressions by default and extended regular expressions when the `x` flag is present, so ordinary expressions can silently rename different archive members.

Under `LC_ALL=C`, for a member named `aaa`:

```sh
# GNU tar default basic mode: + is literal, so the name remains aaa
tar --transform='s/a+/b/' -cf gnu.tar aaa

# tarfilter currently gives + Python repetition meaning, producing b
python3 tarfilter --transform='s/a+/b/' < input.tar > filtered.tar
```

The inverse spelling `s/a\+/b/` also diverges: it is active repetition in GNU basic mode and literal in extended mode.

A bounded candidate translates the characterized GNU basic or extended spelling before Python compilation, accepts `x`, preserves captures and contextual anchors, and rejects unresolved or Python-only syntax before archive output. Direct GNU tar 1.35 tests cover member names, hard-link targets, symlink targets, numeric occurrence selectors, malformed intervals, unmatched extended closing parentheses, and repeated quantifiers.

The intended compatibility claim is deliberately limited to the executed `LC_ALL=C` subset. POSIX bracket classes and locale behavior, GNU alphabetic escapes, expression lists, persistent flags, replacement case conversion, complete diagnostics, and regex resource policy remain outside this change.

## Minimal reproducer

```sh
mkdir repro && cd repro
printf 'payload\n' > aaa
LC_ALL=C tar --transform='s/a+/b/' -cf gnu.tar aaa
LC_ALL=C tar -tf gnu.tar

LC_ALL=C tar -cf input.tar aaa
LC_ALL=C python3 /path/to/tarfilter --transform='s/a+/b/' < input.tar > filtered.tar
LC_ALL=C tar -tf filtered.tar
```

Expected GNU-compatible default-basic listing:

```text
aaa
```

Observed direct-Python listing:

```text
b
```

## Proposed direction

Introduce an explicit transform-regex dialect boundary:

- GNU basic spelling by default;
- GNU extended spelling with `x`;
- stateful translation around escapes, brackets, groups, alternation, anchors, intervals, and backreferences;
- early rejection for unsupported or ambiguous syntax;
- retained direct GNU differential tests.

## Internal preparation state

The Linux Fieldwork candidate and repairs have exact-head internal test receipts. A current canonical-source rebase, upstream-native test run, fresh complete-diff review, and overlap search remain before any submission.

## Authority

This draft is retained internally. No public issue, merge request, email, comment, or review is authorized or created.
