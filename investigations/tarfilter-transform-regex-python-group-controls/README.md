# Python-group guard positive controls

## In simple words

PR #151 now rejects active `(?...)` syntax in explicit extended-regex mode because GNU tar rejects that Python-only group namespace. A parser guard can also reject ordinary patterns accidentally when it ignores escaping or bracket-expression state.

This cross-review adds direct GNU differential controls for the accepted neighbors of the new rejection boundary.

## Source and routing

- parent issue: #108
- canonical candidate: PR #151
- reviewed predecessor head: `7f1865e48b77b89d4989b7de0fe4b85bad4377ec`
- repaired canonical head at review start: `4555c5c250c1afedb3947fd1a7b5a0323bd9d262`
- executable control: `../../tests/test_tarfilter_transform_regex_python_group_controls.py`
- authority: internal Linux Fieldwork work only

## Controls

GNU tar 1.35 under `LC_ALL=C` accepts all three transforms for a member named `(` and produces member `X`:

```text
s/\(?/X/x
s/[(?]/X/x
s/\(/X/x
```

They distinguish:

1. an escaped literal parenthesis followed by an ordinary ERE `?` quantifier;
2. `(` and `?` as bracket-expression members;
3. an escaped literal parenthesis without the neighboring quantifier.

The canonical guard runs after bracket expressions are copied and before escape translation, so these forms should remain outside the active `(?` rejection.

## Regression design

The focused test subclasses the existing edge-case suite. It therefore reapplies the target-scope, occurrence-selector, dialect, and edge patches and reruns the inherited full matrix before executing the three positive controls against GNU tar.

Focused command:

```text
python3 -m unittest -v tests/test_tarfilter_transform_regex_python_group_controls.py
```

Complete discovery and exact-head Linux Fieldwork CI remain required before this review enhancement is accepted.

## Evidence boundary

This record proves only the escaping and bracket-state neighbors of the Python-group guard. It does not expand claims for POSIX bracket classes, collation, locale and encoding parity, GNU-specific alphabetic escapes, malformed-expression diagnostics, or other interval combinations.

## External contact

No Debian, GNU, mmdebstrap, mailing-list, issue, email, patch, merge request, comment, or review outside controlled `teamleaderleo/*` repositories is authorized or included.
