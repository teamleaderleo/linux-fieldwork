# Archive transform regex dialects need an explicit parser

## TL;DR

GNU tar uses basic regular expressions by default and extended expressions
with the `x` flag. A wrapper that feeds both forms directly to Python `re`
silently changes operators, anchors, groups, intervals, and error behavior.
Translate a characterized subset with an explicit scanner and reject every
unresolved construct before processing archive data.

## Explain like I'm five

A regex engine choice is part of a transform's public behavior. Passing a sed-style pattern directly to another language's regex compiler can silently change which characters are operators.

GNU tar uses basic regular expressions by default and extended expressions with the `x` flag. Python's `re` syntax resembles the extended form. Direct compilation therefore behaves as though `x` were always active while still rejecting the flag itself.

Think of the two regex dialects as two sets of road signs that reuse the same
punctuation. Reading one set with the other set's rulebook can produce a valid
route to the wrong filename.

## Why care

An archive filter can exit successfully while renaming members or link targets
differently from GNU tar. That produces plausible archives whose paths no
longer follow the command the user supplied. Early rejection is safer than a
successful wrong rewrite.

## Operator mapping

A translator should model the selected dialect before compiling:

| Concept | GNU basic | GNU extended / Python-like |
| --- | --- | --- |
| one-or-more | `\+` | `+` |
| zero-or-one | `\?` | `?` |
| alternation | `\|` | `|` |
| capture group | `\(` and `\)` | `(` and `)` |
| interval | `\{m,n\}` | `{m,n}` |
| backreference | `\1` | `\1` after a valid group |

Unescaped operator characters in basic mode need literal treatment. Escaped operator characters need conversion to the target engine's active form. Extended mode generally keeps the Python-compatible spelling and treats escaped operators as literals.

## Scanner state

A safe translator needs state, at minimum:

- current dialect;
- inside or outside a bracket expression;
- escaped or unescaped character;
- group depth after translation;
- anchor position at expression or group boundaries;
- interval candidate and closing delimiter;
- existing transform delimiter escaping, handled before regex translation.

A global series of string replacements will corrupt bracket expressions, double escapes, and nested groups.

## Anchors

Regex dialects can disagree about context-sensitive anchors. In GNU basic syntax, `^` and `$` act as anchors only in permitted positions and can be literal elsewhere. Python treats them as anchors wherever parsed.

The translator should decide anchor status from scanner position, then escape a literal anchor before handing the pattern to Python.

## Captures and backreferences

Backreference syntax can look identical while group syntax differs. Validate references after translating groups:

1. translate group open/close tokens for the selected dialect;
2. count translated capture groups;
3. retain `\1` through `\9` only when the referenced group can exist;
4. let malformed references fail deterministically before archive output.

A test should include both directions: a basic expression that becomes valid after escaped-parenthesis translation, and an unescaped-parenthesis expression that GNU basic rejects while Python would accept.

## Bracket expressions and locales

Ordinary bracket expressions overlap well enough for focused controls. POSIX classes, equivalence classes, collating elements, range ordering, and multibyte locale behavior do not map cleanly to Python `re`.

Choose one explicit policy for each unsupported form:

- translate with a separately tested implementation;
- restrict the candidate to a named locale and subset;
- reject before processing archive members.

Silent partial interpretation produces convincing but wrong member names.

## Differential validation pattern

For each operator family, retain four cases:

1. default basic active spelling;
2. default basic literal spelling;
3. extended active spelling with `x`;
4. extended literal spelling with `x`.

Add:

- capture/backreference validity in both dialects;
- contextual `^` and `$` cases;
- bracket-expression controls;
- malformed-pattern parity;
- a predecessor negative control that demonstrates direct Python compilation;
- archive member and link-target cases once the translator is integrated with transform scopes.
- Python-only group extensions such as `(?=...)`, `(?:...)`, inline flags, and
  named groups, which GNU tar rejects;
- malformed active intervals and unmatched closing groups, whose GNU/Python
  error behavior needs an explicit policy.

Compare actual archive metadata with GNU tar under a recorded locale. Exit status alone cannot detect a successful wrong rename.

## Provenance and boundary

- Parent issue: #36.
- Regex-dialect issue: #108.
- Investigation: `investigations/tarfilter-transform-regex-candidate/`.
- Imported source: `upstream/mmdebstrap/tarfilter`, blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`.

The retained candidate passed 21 focused GNU tar 1.35 differential tests twice
on a synthetic merge with current `main` at reviewed head
`4555c5c250c1afedb3947fd1a7b5a0323bd9d262`. A follow-up malformed-grammar
probe found two success-versus-error mismatches: GNU rejects active
`{` sequences such as `a{}` and `a{2`, while Python treats them as literals;
GNU extended regex treats an unmatched closing `)` as a literal, while Python
rejects it. The follow-up candidate now rejects unparsed active intervals and
escapes unmatched closing parentheses only in extended mode. Six interval
controls and three unmatched-close controls compare directly with GNU tar.

This note covers the basic/extended dialect switch and translator design.
Persistent `flags=` statements, multiple substitutions, replacement case
conversion, malformed-grammar parity, and complete locale-aware POSIX regex
compatibility remain separate work.
