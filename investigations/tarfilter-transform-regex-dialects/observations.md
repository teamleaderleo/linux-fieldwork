# GNU tar 1.35 regex dialect observations

Observed on 2026-07-30 with `LC_ALL=C`. Each command archived one file whose basename is shown in the first column.

```text
input  expression                 result
aaa    s/a+/b/                    aaa
aaa    s/a+/b/x                  b
aaa    s/a\+/b/                  b
aaa    s/a\+/b/x                aaa
aa     s/a?/b/                    aa
aa     s/a?/b/x                  ba
aa     s/a\?/b/                  ba
aa     s/a\?/b/x                aa
ab     s/a|b/c/                   ab
ab     s/a|b/c/x                 cb
ab     s/a\|b/c/                 cb
ab     s/a\|b/c/x               ab
aaa    s/(aa)/[&]/                aaa
aaa    s/(aa)/[&]/x              [aa]a
aaa    s/\(aa\)/[&]/             [aa]a
aaa    s/\(aa\)/[&]/x           aaa
aab    s/a\{1,2\}/x/             xb
aab    s/a{1,2}/x/x             xb
aa     s/\(a\)\1/b/              b
aa     s/(a)\1/b/x               b
aa     s/(a)\1/b/                rejected: invalid back reference
aa     s/\(a\)\1/b/x             rejected: invalid back reference
a^b    s/a^b/x/                  x
a^b    s/a^b/x/x                a^b
a$b    s/a$b/x/                  x
a$b    s/a$b/x/x                a$b
aa     s/[a+]/x/                 xa
aa     s/[a+]+/x/x               x
```

## Immediate deductions

- GNU tar's default expression uses basic regular-expression operator spelling.
- `x` selects extended operator spelling for that substitution.
- Escaping reverses the operator status of `+`, `?`, `|`, parentheses, and interval braces between the two dialects.
- Backreference validity follows the groups created in the selected dialect.
- In basic mode, `^` and `$` are literal outside their anchor positions; direct Python compilation treats them as anchors everywhere.
- Translation must suspend operator rewriting inside bracket expressions.
- Ordinary classes and the shared `.`, `*`, leading `^`, and trailing `$` subset provide useful positive controls.

## Unresolved reference matrix

A later candidate should extend differential coverage before claiming compatibility for:

- POSIX classes such as `[[:digit:]]`;
- equivalence classes and collating elements;
- escaped GNU word-boundary operators;
- empty alternatives and empty groups;
- nested and malformed intervals;
- anchor behavior immediately inside translated groups;
- bytes and multibyte characters under non-C locales;
- catastrophic-backtracking and expression-size limits.
