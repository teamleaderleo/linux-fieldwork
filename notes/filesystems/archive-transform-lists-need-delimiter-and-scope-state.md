# Archive transform lists need delimiter and scope state

## In simple words

A semicolon in a transform string can mean three different things:

- the delimiter of one substitution;
- ordinary pattern or replacement data;
- the separator between complete statements.

A parser can decide among them only by tracking where it is inside the current statement.

GNU tar also carries target-scope state across statements through `flags=`. Parsing each substitution independently loses that state.

## Statement scanner

A reusable scanner should produce an ordered statement stream:

```text
ScopeStatement(scope_set)
Substitution(pattern, replacement, local_flags)
```

Track:

- statement start;
- active substitution delimiter;
- pattern, replacement, and flag fields;
- backslash/escape state;
- whether one complete statement has ended;
- persistent target scope.

Treat `;` as a separator only after a complete statement and outside every delimited field.

## Persistent target scope

Model scope as three booleans:

```text
member names
symlink targets
hard-link targets
```

A `flags=` statement replaces the persistent set. Start the statement from an empty set, process lowercase enables and uppercase disables, and reject non-scope letters.

For each substitution:

1. copy the persistent set;
2. apply local lowercase/uppercase scope letters to the copy;
3. store that effective set with the substitution;
4. leave the persistent set unchanged for the next statement.

This keeps local amendments from leaking forward.

## Ordered application

Preserve statement and command-line order. These forms should compose equivalently:

```text
--transform 's,A,B,;s,B,C,'
```

and

```text
--transform 's,A,B,' --transform 's,B,C,'
```

Each substitution consumes the member name or link target produced by the previous substitution. PAX `path` and `linkpath` cleanup should follow the final changed values, with tests proving sequential renames and extraction.

## Empty statements

Grammar rules need explicit tests:

- one trailing separator may be accepted;
- a leading separator creates an invalid empty statement;
- doubled interior separators create an invalid empty statement;
- a semicolon delimiter can close a substitution without becoming a statement separator;
- semicolons inside another delimiter's pattern or replacement remain data.

## Integration with other transform features

The statement scanner should stay separate from:

- regex basic/extended translation;
- replacement-language expansion;
- numeric occurrence selection;
- case-insensitive matching;
- target-scope application;
- archive metadata regeneration.

Parse the list first, then parse each substitution using the dedicated regex, replacement, and flag components. This keeps one grammar correction from rewriting every transform feature.

## Differential validation

A practical matrix includes:

- semicolon list versus repeated command-line options;
- every persistent target subset;
- empty persistent scope;
- uppercase disables;
- persistent reset between substitutions;
- local enable and disable amendments;
- delimiter-semicolon and replacement-semicolon controls;
- trailing separator and invalid empty statements;
- unsupported persistent letters;
- regular member, hard-link target, and symlink target metadata;
- a predecessor negative control.

Compare archive metadata directly with GNU tar under a recorded locale.

## Provenance and boundary

- Parent issue: #36.
- Expression-list issue: #117.
- Investigation: `investigations/tarfilter-transform-expression-lists/`.
- Imported source: `upstream/mmdebstrap/tarfilter`, blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`.

This note covers statement tokenization and persistent target scope. Regex dialect translation, replacement case conversion, and full locale-aware POSIX regex compatibility remain separate contracts.
