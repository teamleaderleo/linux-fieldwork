# GNU replacement case-conversion observations

Observed on 2026-07-30 under `LC_ALL=C`.

## Safe GNU tar 1.35 archive results

Input member: `AbC-def`.

```text
expression                    result
s/AbC/\L&/                    abc-def
s/AbC/\U&/                    ABC-def
s/AbC/\l&/                    abC-def
s/AbC/\u&/                    AbC-def
s/AbC/\E&/                    AbC-def
s/.*/\Uab\Lcd\Eef/           ABcdef
s/.*/pre\L&\Epost/            preabc-defpost
s/.*/\Lx\Uy\Ez/              xYz
s/[a-z]/\u&/g                 ABC-DEF
s/.*/\\L&/                   \LAbC-def
```

Input capture examples under extended regex syntax:

```text
AbC-def + s/(AbC)-(def)/\L\1\E-\U\2\E/x  -> abc-DEF
AbC-def + s/(AbC)-(def)/\l\1-\u\2/x       -> abC-Def
```

These backreference examples remain raw observations because the PR #68 predecessor rejects `x`; regex-dialect support is owned by #108.

## PR #68 predecessor results

The replacement function drops unknown-control backslashes:

```text
\L&                  -> LAbC-def
\U&                  -> UAbC-def
\l&                  -> lAbC-def
\u&                  -> uAbC-def
\E&                  -> EAbC-def
\Uab\Lcd\Eef         -> UabLcdEef
pre\L&\Epost          -> preLAbC-defEpost
\Lx\Uy\Ez            -> LxUyEz
```

For global `s/[a-z]/\u&/g`, each selected lowercase character receives a literal `u`, producing `AubC-udueuf`. This is a useful per-match reset negative control.

## Target-field result

For regular `AbC-def`, hard link `AbC-hard -> AbC-def`, and symlink `sym -> AbC-def`, default `s/AbC/\L&/` produces:

GNU tar:

```text
abc-def
abc-hard -> abc-def
sym -> abc-def
```

PR #68 predecessor:

```text
LAbC-def
LAbC-hard -> LAbC-def
sym -> LAbC-def
```

## GNU sed 4.9 empty-capture semantics

```text
input a-  s/(b?)-/x\u\1y/     -> axY
input a-  s/(b?)-/x\u\1\Ey/   -> axy
input a-  s/(b?)-/x\l\1Y/     -> axy
input a-  s/(b)?-/x\u\1y/     -> axY
input b-  s/(b?)-/x\u\1y/     -> xBy
```

A participating empty capture leaves one-shot state pending. `\E` clears it before later literal text. A non-empty capture consumes the pending conversion.

## GNU tar 1.35 reference crash

With core dumps disabled, these tested forms exit by `SIGSEGV` when capture 1 participated and matched an empty string:

```text
s/(b?)-/x\u\1/x
s/(b?)-/\u\1x/x
s/(b?)-/\u\1\Ex/x
s/(b?)-/x\l\1/x
s/(b*)-/x\u\1/x
```

Controls:

```text
s/(b?)-/x\1/x     empty capture without case conversion succeeds
s/(b)?-/x\u\1/x   tested non-participating group succeeds
s/(b?)-/x\u&/x    whole non-empty match succeeds
```

Issue #124 owns crash characterization. Generic CI excludes these tar commands.

## Unresolved matrix

A later candidate should expand safe coverage for:

- Unicode case conversion outside `LC_ALL=C`;
- one-shot controls before literal, whole-match, and capture segments;
- multiple empty segments before the first emitted character;
- persistent-mode switches surrounding empty captures;
- case state across numeric occurrence selection;
- case state in semicolon expression lists;
- member/link PAX regeneration after converted long paths;
- collision behavior when case conversion maps distinct names together;
- replacement parser errors for trailing control backslashes and malformed captures.
