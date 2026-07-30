# Archive transform replacements need case state

## In simple words

Replacement text is a small program. Case controls such as `\L`, `\U`, `\l`, `\u`, and `\E` change how later replacement output is emitted. Treating every unknown escape as a literal character loses that program state.

## Compile replacement segments

Parse replacement text once into explicit segments:

```text
Literal(text)
WholeMatch
Capture(number)
LowerMode
UpperMode
LowerNext
UpperNext
EndCase
```

Preserve separate segments for escaped backslash, escaped `&`, and escaped delimiter so a literal `\L` stays distinct from the `\L` control.

## Per-match execution state

For each regex match, start with:

```text
persistent mode: none
pending one-shot: none
```

When a text-producing segment emits characters:

1. apply a pending one-shot conversion to the first emitted character;
2. clear the pending conversion after one character;
3. apply persistent lower/upper mode to the full emitted text;
4. append the result.

Control segments update state:

- `\L`: persistent lowercase;
- `\U`: persistent uppercase;
- `\l`: lowercase the next emitted character;
- `\u`: uppercase the next emitted character;
- `\E`: clear persistent and pending state.

Reset state for every regex match. A global substitution must never carry case mode from one match into the next.

## Empty segments

A capture can participate and still expand to an empty string. GNU sed keeps one-shot state pending across that empty segment:

```text
x\u\1y
```

When capture 1 is empty, `y` becomes uppercase. `\E` between the empty capture and `y` clears the pending conversion.

Represent this directly: an empty segment emits no character and therefore does not consume pending one-shot state.

## Persistent and one-shot precedence

Apply one-shot conversion to the first character, then persistent mode to the resulting text. Tests should cover interactions such as:

```text
\L...\U...\E
\U...\L...\E
\l under persistent upper
\u under persistent lower
```

Record the selected order from the reference implementation and keep it isolated inside one emission helper.

## Archive fields

Compile one replacement program per substitution, then execute it independently for:

- member names;
- hard-link targets;
- symlink targets.

Each field and each regex match gets fresh case state. After a changed value, remove stale PAX `path` or `linkpath` metadata so the writer regenerates it.

## Reference-tool crashes

A differential reference can fail as a process rather than produce output. GNU tar 1.35 crashes on tested empty participating captures combined with one-shot conversion.

Keep two evidence paths:

- ordinary supported cases compared directly with GNU tar;
- empty-capture semantics compared with GNU sed documentation and a safe GNU sed harness.

Run any tar crash characterization in a dedicated subprocess with core dumps disabled, timeout, temporary cwd, exact version receipt, and isolated reporting. Do not place intentional reference crashes in the normal unit suite.

## Differential matrix

A useful replacement matrix includes:

- whole-match lower and upper mode;
- one-shot lower and upper;
- explicit reset;
- mode switching;
- literal escaped control spelling;
- capture references under each control;
- global per-match reset;
- empty participating capture;
- non-participating optional capture;
- member, hard-link, and symlink target fields;
- a predecessor control proving unknown escapes become literal letters.

## Provenance and boundary

- Parent issue: #36.
- Case-conversion issue: #125.
- GNU tar crash issue: #124.
- Investigation: `investigations/tarfilter-transform-case-conversion/`.
- Imported source: `upstream/mmdebstrap/tarfilter`, blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`.

This note covers replacement case-control state. Regex dialect translation, expression-list parsing, numeric occurrence selection, and locale-aware Unicode case behavior remain separate contracts.
