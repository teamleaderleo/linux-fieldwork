# Tarfilter transform expression lists and persistent scopes

## In simple words

GNU tar accepts several transform statements in one `--transform` value. Substitutions run in order, and `flags=` statements select which path-bearing fields later substitutions can change.

The retained Linux Fieldwork candidate from PR #68 supports repeated `--transform` options, but it parses each option as one substitution. It rejects semicolon expression lists and every `flags=` statement.

This branch records the missing grammar and the already-working repeated-option path as executable characterization. It contains no source correction patch.

## Coordination and ownership

- Parent transform record: #36.
- Bounded expression-list issue: #117.
- Regex-dialect issue: #108 / PR #113.
- Numeric occurrence issue: #98 / PR #102.
- Characterization branch: `investigation/tarfilter-transform-expression-lists`.
- Imported source remains unchanged.
- No upstream contact is authorized or made.

A repository issue, PR, branch, investigation, note, and test search found no existing semicolon-list or persistent-scope candidate.

## Exact source and test boundary

- Imported source: `upstream/mmdebstrap/tarfilter`.
- Imported blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`.
- Characterized predecessor: `investigations/tarfilter-transform-target-scopes/tarfilter-transform-target-scopes.patch` from PR #68.
- Differential reference: GNU tar 1.35 under `LC_ALL=C`.
- Regression: `tests/test_tarfilter_transform_expression_lists.py`.

The fixture contains:

- regular member `prefix/target`;
- hard link `prefix/hard -> prefix/target`;
- symlink `sym -> prefix/target`.

The regression copies the imported source into `TemporaryDirectory`, applies the PR #68 patch, and compares archive metadata or parser rejection directly with GNU tar.

## Ordered substitutions

GNU tar applies semicolon-separated substitutions in order:

```text
s,^prefix/,,;s,^target$,final,
```

The fixture becomes:

```text
final                 regular file
hard -> final         hard link
sym -> final          symlink
```

The PR #68 predecessor rejects that one expression-list value. Two repeated command-line options already work and produce the same archive:

```text
--transform 's,^prefix/,,'
--transform 's,^target$,final,'
```

This positive control keeps the candidate boundary narrow: transform ordering already exists; statement tokenization is missing.

## Persistent `flags=` scope sets

`flags=<letters>` replaces the persistent target set. Lowercase letters enable:

- `r`: archive member names;
- `s`: symlink targets;
- `h`: hard-link targets.

Unspecified targets are off. `flags=` with an empty value disables every target. Uppercase letters disable their named target inside a supplied set.

The executable matrix covers these exact persistent sets:

| Statement | Selected fields |
| --- | --- |
| `flags=r` | member names |
| `flags=s` | symlink targets |
| `flags=h` | hard-link targets |
| `flags=rh` | member names and hard-link targets |
| `flags=rs` | member names and symlink targets |
| `flags=sh` | both link targets |
| `flags=rsh` | all three |
| `flags=` | none |

The predecessor rejects every statement before processing the archive.

## Persistent resets and local amendments

The setting remains active until another `flags=` statement or the end of the expression list. A later statement replaces the persistent set.

Local scope letters on one substitution amend the persistent set for that substitution only. The regression retains examples where:

- `flags=S` leaves every target off, then a later `flags=s` enables only symlink targets;
- `flags=r` transforms member names, then `flags=h` transforms hard-link targets in the next substitution;
- local `H` keeps hard-link targets disabled on a persistent `r` substitution;
- local `r` adds member names to a persistent `s` substitution;
- a later persistent `s` limits a second substitution to the already-transformed symlink target.

`flags=x` and `flags=g` are rejected by GNU tar because persistent statements accept target-scope letters, not regex or replacement modifiers.

## Statement-boundary grammar

A parser needs active delimiter and field state:

- `s;^prefix/;;` is one valid substitution using semicolon as its delimiter;
- `s,^prefix/,pre;fix/,` contains a semicolon inside replacement text and remains one substitution;
- `s|^prefix/||;s|^target$|final|` contains a top-level statement separator after the first complete substitution;
- a trailing separator is accepted;
- a leading empty statement and doubled interior separator are rejected.

A blind `expression.split(';')` cannot preserve those cases.

## Parser requirements for a later candidate

The eventual parser needs to:

1. scan statements left to right;
2. recognize `flags=` only at statement start;
3. track the active substitution delimiter, pattern field, replacement field, and final flags field;
4. treat semicolons as separators only after a complete statement;
5. allow one trailing separator while rejecting leading and doubled empty statements;
6. retain persistent target scope across substitutions;
7. clone and locally amend that scope for each substitution;
8. append statement lists in command-line option order so repeated `--transform` options remain equivalent;
9. preserve the existing replacement, occurrence, regex-dialect, and PAX metadata contracts;
10. reject unsupported persistent letters before archive output.

## Executable contract

```sh
python3 -m unittest tests.test_tarfilter_transform_expression_lists -v
python3 -m unittest discover -s tests -v
```

The characterization requires:

- one rejected semicolon list paired with successful repeated-option and GNU equivalents;
- eight persistent scope-set cases;
- five persistent reset or local-amendment cases;
- semicolon delimiter and replacement-data controls;
- trailing-separator acceptance and empty-statement rejection;
- non-scope `flags=` rejection;
- exact PR #68 patch application.

## Cleanup and evidence limits

All copied sources, files, hard links, symlinks, and archives live under `TemporaryDirectory`. The test accepts no caller-selected cleanup root and performs no privileged operation.

This record establishes expression-list parsing and target-scope state. It does not implement the correction. Regex dialect translation stays in #108, replacement case conversion stays under #36, and broader locale/POSIX regex behavior remains separate.

## Handoff

Start here, then read `observations.md`, the reusable parser-state note, and the regression. The source candidate should begin after this characterization and its transform predecessors have independent exact-head verdicts.
