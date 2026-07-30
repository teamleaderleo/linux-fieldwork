# Tarfilter replacement case conversion

## In simple words

GNU tar replacement text supports case-control escapes. The retained Linux Fieldwork replacement function from PR #68 treats unknown escapes by dropping the backslash, so `\L`, `\U`, `\l`, `\u`, and `\E` become literal letters.

This branch records the missing behavior with safe GNU tar comparisons and GNU sed empty-capture controls. It contains no correction patch and deliberately excludes the known GNU tar crash input from generic CI.

## Coordination and ownership

- Parent transform record: #36.
- Local replacement defect: #125.
- GNU tar 1.35 empty-capture crash: #124.
- Regex-dialect characterization: #108 / PR #113.
- Expression-list characterization: #117 / PR #122.
- Numeric occurrence candidate: #98 / PR #102.
- Characterization branch: `investigation/tarfilter-transform-case-conversion`.
- Imported source remains unchanged.
- No upstream contact is authorized or made.

A repository issue, PR, branch, investigation, note, and test search found no existing case-conversion candidate.

## Exact source and test boundary

- Imported source: `upstream/mmdebstrap/tarfilter`.
- Imported blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`.
- Characterized predecessor: `investigations/tarfilter-transform-target-scopes/tarfilter-transform-target-scopes.patch` from PR #68.
- Safe archive reference: GNU tar 1.35 under `LC_ALL=C`.
- Empty-capture semantic reference: GNU sed 4.9 under `LC_ALL=C`.
- Regression: `tests/test_tarfilter_transform_case_conversion.py`.

The regression copies the imported source into `TemporaryDirectory`, applies the PR #68 patch, and compares safe archive metadata directly with GNU tar. It uses GNU sed for documented empty-capture replacement state and never invokes the known crashing GNU tar expressions.

## Current predecessor behavior

The retained replacement function handles whole-match `&`, capture references, escaped `&`, escaped backslash, and the active delimiter. Every other escaped character loses its backslash and becomes literal text.

Representative results for member `AbC-def`:

| Replacement | PR #68 predecessor | GNU tar |
| --- | --- | --- |
| `\L&` | `LAbC-def` | `abc-def` |
| `\U&` | `UAbC-def` | `ABC-def` |
| `\l&` | `lAbC-def` | `abC-def` |
| `\u&` | `uAbC-def` | `AbC-def` |
| `\E&` | `EAbC-def` | `AbC-def` |
| `\Uab\Lcd\Eef` | `UabLcdEef` | `ABcdef` |
| `pre\L&\Epost` | `preLAbC-defEpost` | `preabc-defpost` |
| `\Lx\Uy\Ez` | `LxUyEz` | `xYz` |

A global `s/[a-z]/\u&/g` control proves case state must reset for each match. The predecessor emits a literal `u` before every lowercase match; GNU tar uppercases each selected character.

## Shared literal-backslash control

Two replacement backslashes before `L` mean a literal `\L`, followed by ordinary whole-match expansion:

```text
s/.*/\\L&/  -> \LAbC-def
```

The predecessor and GNU tar agree on this case. A correction must preserve it while recognizing one-backslash case controls.

## Archive target fields

The regression applies `s/AbC/\L&/` to:

- regular member `AbC-def`;
- hard-link member `AbC-hard -> AbC-def`;
- symlink `sym -> AbC-def`.

GNU tar lowercases both selected member names and both link targets. The predecessor inserts literal `L` in every selected field. This keeps case conversion integrated with the reviewed default `rsh` target scope rather than testing member names alone.

## Empty-capture semantics

GNU sed documents that one-shot `\u` or `\l` can remain pending when the next replacement segment expands to an empty string. The pending conversion then affects the first later emitted character unless `\E` clears it.

The safe GNU sed matrix requires:

```text
input a-  s/(b?)-/x\u\1y/     -> axY
input a-  s/(b?)-/x\u\1\Ey/   -> axy
input a-  s/(b?)-/x\l\1Y/     -> axy
input a-  s/(b)?-/x\u\1y/     -> axY
input b-  s/(b?)-/x\u\1y/     -> xBy
```

The first three distinguish an empty participating capture, explicit reset, and lowercasing. The fourth shows the tested non-participating optional group behavior. The fifth is the non-empty control.

## Reference crash boundary

GNU tar 1.35 crashes when a one-shot converter is applied to a participating capture that matched an empty string. Issue #124 retains the isolated reproduction and signal matrix.

Generic repository CI does not run those tar expressions. A later source candidate should follow GNU sed's documented output and should not reproduce the tar crash.

## Replacement-engine requirements for a later candidate

A correction needs compiled replacement segments and per-match state:

1. literal text;
2. whole-match reference;
3. numbered capture reference;
4. persistent lowercase mode (`\L`);
5. persistent uppercase mode (`\U`);
6. one-shot lowercase (`\l`);
7. one-shot uppercase (`\u`);
8. case reset (`\E`).

While emitting a replacement:

- apply a pending one-shot conversion to the first emitted character;
- keep it pending across empty segments;
- apply persistent mode to every emitted character until switched or reset;
- let `\E` clear both persistent and pending state;
- reset every case-control state for each regex match;
- preserve literal escaped backslash, `&`, and delimiter behavior;
- run the same replacement program independently for member names and link targets.

## Executable contract

```sh
python3 -m unittest tests.test_tarfilter_transform_case_conversion -v
python3 -m unittest discover -s tests -v
```

The characterization requires:

- nine safe predecessor/GNU tar divergences;
- one literal-backslash shared control;
- one member/hard-link/symlink target comparison;
- five GNU sed empty-capture state cases;
- exact PR #68 patch application;
- GNU tar and GNU sed version/locale boundaries.

## Cleanup and evidence limits

All copied sources, path fixtures, links, and archives live under `TemporaryDirectory`. The test accepts no caller-selected cleanup root and performs no privileged operation.

This record establishes replacement case-control state. It does not implement the correction. Regex dialect translation remains #108, expression lists remain #117, numeric selectors remain #98, and the GNU tar crash remains #124.

## Handoff

Start here, then read `observations.md`, the reusable replacement-state note, and the regression. The source candidate should begin after this safe characterization and the transform predecessors have independent exact-head verdicts. A dedicated crash harness belongs to #124, outside the generic suite.
