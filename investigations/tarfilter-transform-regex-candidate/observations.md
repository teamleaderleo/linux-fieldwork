# Regex candidate observations

## Proven reference matrix

The source candidate starts from the GNU tar 1.35 matrix retained by PR #113. The decisive rules under `LC_ALL=C` are:

- basic syntax is the default;
- `x` selects extended syntax for one substitution;
- escaping reverses operator status for `+`, `?`, `|`, parentheses, and interval braces;
- backreference validity follows capture groups created by the selected dialect;
- `^` and `$` are context-sensitive anchors in GNU basic syntax;
- ordinary bracket expressions suspend punctuation translation.

## Candidate parser decisions

### Operator translation

A stateful scanner translates the characterized GNU basic tokens into Python spelling. A sequence of global string replacements was rejected because it would corrupt bracket expressions, escaped literals, and nested group/alternation boundaries.

### Extended mode

With `x`, unescaped operator punctuation remains active. Escaped punctuation remains escaped and therefore literal in Python. Existing delimiter unescaping runs before regex-dialect translation.

### Anchors

The scanner records whether the next token begins an expression or alternation branch. In basic mode it keeps `^` active at branch starts and `$` active at branch ends, escaping other positions as literals. In extended mode GNU tar keeps both anchors active at every position, including the middle-position `a^b` and `a$b` controls.

Representative composition probes retained in the regression:

```text
input  expression       result
aa     s/\(a\)\1/b/     b
ab     s/\(^a\)/x/      xb
b      s/a\|^b/x/       x
a      s/a$\|b/x/       x
ab     s/(^a)/x/x       xb
b      s/a|^b/x/x       x
a      s/a$|b/x/x       x
```

### Numeric occurrence and target scopes

Regex translation happens once during transform parsing. Match-position counting remains in the PR #102 `_sed_substitute()` helper and resets for every transformed field.

The candidate matrix uses a two-match path and both dialects:

```text
input     expression     result
aaa/aaa  s/a\+/b/2      aaa/b
aaa/aaa  s/a+/b/x2      aaa/b
```

The same selected match is required independently for the member name, hard-link target, and symlink target.

### Repeated quantifiers

GNU tar 1.35 accepts the executed nested repetition forms that Python rejects or interprets as lazy or possessive syntax. The edge patch wraps the preceding atom in a noncapturing group before applying each later quantifier, preserving user capture numbering.

The same GNU tar rejects consecutive basic intervals such as `a\{2\}\{2,3\}`.
It also rejects active malformed interval openings such as `a{}`, `a{2`, and
`a{x}` in extended mode and their escaped basic equivalents. Python treats
several of those spellings as literal text, so the candidate rejects every
active `{` that is not a parsed interval before archive output.

GNU extended regex treats an unmatched closing `)` as a literal. Python
rejects it as an unbalanced group. The normalizer escapes a closing parenthesis
only when extended mode has no open group; balanced groups and active basic
`\)` keep their original behavior.

## Explicit unsupported policy

GNU tar accepts POSIX bracket classes, collating elements, and equivalence classes in the tested C-locale forms. Python `re` does not provide a faithful direct mapping. The candidate rejects these strings before archive output:

```text
s/[[:digit:]]/x/
s/[[.a.]]/x/
s/[[=a=]]/x/
```

Alphabetic escapes such as GNU word-boundary extensions and Python-specific shorthand classes also remain rejected until a separate differential matrix defines their contract.

## Questions reserved for later slices

- exact GNU behavior for interval forms beyond the executed valid and malformed matrix;
- POSIX classes and collation outside the C locale;
- GNU word-boundary and buffer-boundary escapes;
- byte-oriented versus Unicode-oriented matching;
- expression-size and catastrophic-backtracking limits;
- interaction with persistent `flags=` state and expression lists;
- replacement-language case conversion.

These are recorded as boundaries, not inferred compatibility.
