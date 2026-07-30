# Tarfilter regex dialect candidate

## In simple words

GNU tar reads transform patterns as basic regular expressions by default and as extended expressions when the `x` flag is present. Python `re` uses an extended-like spelling. Passing the GNU expression directly to Python changes which punctuation acts as an operator.

This candidate retains a small incremental translator after the reviewed transform target-scope and numeric-occurrence patches. It leaves the imported source unchanged.

## Coordination and ownership

- Parent transform compatibility record: #36.
- Bounded regex-dialect defect: #108.
- Characterization and negative control: PR #113.
- Candidate pull request: #151.
- Replacement and target-scope predecessor: PR #68.
- Numeric occurrence predecessor: PR #102.
- Branch: `fix/tarfilter-transform-regex-dialects`.
- No upstream contact is authorized or made.

A repository issue, pull request, branch, investigation, note, and test search found no competing source translator. PR #113 intentionally stopped at characterization so this implementation has one canonical predecessor.

## Exact source boundary

Patch order in the regression:

1. imported `upstream/mmdebstrap/tarfilter`, blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`;
2. `investigations/tarfilter-transform-target-scopes/tarfilter-transform-target-scopes.patch`;
3. `investigations/tarfilter-transform-occurrence-selectors/tarfilter-transform-occurrence-selectors.patch`;
4. `tarfilter-transform-regex-dialects.patch` from this directory.

Regression: `tests/test_tarfilter_transform_regex_candidate.py`.
Differential reference: GNU tar 1.35 with `LC_ALL=C`.

The imported file is copied into `TemporaryDirectory`; every patch is applied to that copy.

## Candidate mechanism

The parser now accepts `x` alongside the existing case, global, scope, and numeric flags.

`_translate_pattern()` scans one pattern before Python compilation. Its state covers:

- selected basic or extended dialect;
- beginning of an expression or alternation branch;
- bracket-expression boundaries;
- escaped versus unescaped operator spelling;
- context-sensitive `^` and `$` anchors.

For the characterized subset:

| Concept | GNU basic input | Python output | GNU extended input | Python output |
| --- | --- | --- | --- | --- |
| one or more | `\+` | `+` | `+` | `+` |
| zero or one | `\?` | `?` | `?` | `?` |
| alternation | `\|` | `|` | `|` | `|` |
| capture | `\(` / `\)` | `(` / `)` | `(` / `)` | unchanged |
| interval | `\{m,n\}` | `{m,n}` | `{m,n}` | unchanged |
| literal operator | unescaped punctuation | escaped for Python | escaped punctuation | escaped for Python |

Backreferences `\1` through `\9` remain in the translated pattern. Python compilation then rejects references whose selected dialect created no corresponding group.

## Anchors and branches

GNU basic `^` and `$` are anchors only in permitted positions. The scanner keeps leading `^`, trailing `$`, and anchors immediately after a translated group or alternation boundary. It escapes middle-position anchors before Python compilation.

The regression includes anchors at:

- expression start and end;
- translated group start;
- basic and extended alternation branch start;
- branch end before alternation.

## Bracket-expression policy

Ordinary bracket expressions are copied without operator translation. The candidate rejects these unresolved forms before reading archive input:

- POSIX classes such as `[[:digit:]]`;
- collating elements such as `[[.a.]]`;
- equivalence classes such as `[[=a=]]`.

GNU tar accepts the tested forms in the C locale. Early rejection is deliberate: Python's parser can partially interpret them and emit plausible wrong names.

Alphabetic escapes outside numeric backreferences also receive an explicit rejection until GNU/Python compatibility is characterized. This avoids silently treating GNU word-boundary or implementation-specific escapes as Python escapes.

## Executable contract

`tests/test_tarfilter_transform_regex_candidate.py` requires:

- the PR #68/#102 predecessor to keep the characterized default `a+` mismatch;
- the predecessor to reject `x`;
- the predecessor to reject a valid GNU basic escaped capture/backreference;
- candidate and GNU tar equality for active and literal `+`, `?`, `|`, grouping, and intervals in both dialects;
- contextual anchor equality at expression, group, and alternation boundaries;
- matching success and failure for dialect-dependent capture/backreference forms;
- shared controls for `*`, leading `^`, trailing `$`, and ordinary brackets;
- composition with numeric selector `2`;
- independent member-name, hard-link-target, and symlink-target counting;
- candidate early rejection and GNU acceptance for the named unsupported POSIX bracket forms.

Commands:

```sh
python3 -m unittest tests.test_tarfilter_transform_regex_candidate -v
python3 -m unittest discover -s tests -v
```

## Observations and results

See `observations.md` for parser and differential notes. `RESULTS.md` will retain every CI run, including failed runs that expose candidate or harness defects.

## Cleanup and rerun

All copied source trees, patch applications, fixture trees, candidate archives, and GNU reference archives live below `TemporaryDirectory`. The test accepts no caller-selected cleanup path and performs no privileged operation.

## Evidence limits

This candidate covers the operator and anchor subset proven by PR #113, `x`, numeric occurrence composition, and existing target scopes.

It excludes:

- POSIX classes, collating elements, equivalence classes, and locale-sensitive ranges;
- GNU word-boundary and other alphabetic escapes;
- malformed-pattern diagnostic parity;
- persistent `flags=` statements and semicolon-separated expression lists;
- replacement case-conversion escapes;
- complete POSIX regex compatibility and performance limits.

## Reusable note

The merged note `notes/filesystems/archive-transform-regex-dialects-need-an-explicit-parser.md` already owns the reusable lesson. A duplicate note is intentionally omitted.

## Resume point

Read this file, `observations.md`, the patch, and the regression. Apply the three patches in the recorded order. Then inspect `RESULTS.md` and PR #151 for the latest exact-head receipt and review state.
