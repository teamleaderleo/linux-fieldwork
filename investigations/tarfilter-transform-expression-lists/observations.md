# GNU tar 1.35 expression-list observations

Observed on 2026-07-30 under `LC_ALL=C` with one regular member, one hard link, and one symlink.

## Ordered substitutions

```text
s,^prefix/,,;s,^target$,final,
```

Result:

```text
final                 regular file
hard -> final         hard link
sym -> final          symlink
```

Two repeated `--transform` options with the same substitutions produce the same archive.

## Persistent target sets

```text
flags=r     member names only
flags=s     symlink targets only
flags=h     hard-link targets only
flags=rh    member names and hard-link targets
flags=rs    member names and symlink targets
flags=sh    both link targets
flags=rsh   all three targets
flags=      no targets
```

Uppercase examples:

```text
flags=Rsh   both link targets
flags=rSH   member names only
```

The statement starts from an empty set, then processes its letters. Unspecified targets remain off.

## Reset and local amendment

```text
flags=S;s,^prefix/,,;flags=s;s,^prefix/,,
```

The first substitution changes nothing. The second changes only the symlink target.

```text
flags=r;s,^prefix/,,;flags=h;s,^prefix/,,
```

The first substitution changes member names. The second changes only the hard-link target.

```text
flags=s;s,^prefix/,,r
```

The local `r` adds member names to persistent symlink-target scope for that substitution.

```text
flags=r;s,^prefix/,,H
```

The local `H` leaves hard-link targets disabled while member-name scope remains active.

## Parser boundaries

```text
s;^prefix/;;                         valid; semicolon is the substitution delimiter
s,^prefix/,pre;fix/,                 valid; semicolon is replacement data
s|^prefix/||;s|^target$|final|      valid; semicolon separates complete statements
s,^prefix/,,;                        valid trailing separator
;s,^prefix/,,                        rejected leading empty statement
s,^prefix/,,;;s,^target$,final,      rejected interior empty statement
```

A backslash before a semicolon inside replacement text is retained as replacement data by GNU tar; it is not required to protect the field semicolon from statement splitting.

## Persistent flag rejection

```text
flags=x;s,^prefix/,,   rejected
flags=g;s,^prefix/,,   rejected
```

Persistent statements accept scope letters. Regex, occurrence, and replacement modifiers belong to individual substitutions.

## Unresolved reference details

A later candidate should expand coverage for:

- whitespace between statements;
- repeated or contradictory persistent letters;
- multiple `flags=` statements with trailing separators;
- delimiter escapes immediately before a statement separator;
- malformed incomplete substitutions;
- multiple command-line values where one value contains several statements;
- interaction with numeric selectors and future `x` translation;
- PAX metadata regeneration after each sequential rename;
- collisions created by an early substitution and consumed by a later one.
