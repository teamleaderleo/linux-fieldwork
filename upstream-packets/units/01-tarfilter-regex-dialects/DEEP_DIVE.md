# Deep dive

## Defect

`tarfilter --transform` advertises GNU tar-style substitutions but passes patterns directly to Python `re.compile()`. GNU tar uses basic regular expressions by default and extended expressions only with `x`.

The minimal mismatch is:

```text
member: aaa
expression: s/a+/b/
Python-backed result: b
GNU basic result: aaa
```

The inverse escaped spelling also differs, so punctuation replacement without parser state fails.

## Exact current source boundary

The user's controlled repository `teamleaderleo/mmdebstrap` is at commit `574048f2a720057b75e56622003932f344dc700a`. Its `tarfilter` is Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`.

Unit 15 independently observed public upstream `main` at `77ec9be5417ee44c96343d2347145585da1b1f94` and the same relevant `tarfilter` blob. This establishes current relevant-file equality for the executed source. Exact canonical Salsa `master` remains a separate contribution-destination identity gate.

## Prerequisite transition

Unit 1 historically applied target-scope and occurrence patches before the regex patches. Unit 15 regenerated those semantics into one patch because the old PR #68 application form fails GNU patch 2.8.

The clean prerequisite:

```text
base blob:         ad776167a8473d5d15dbe22e850f4f6db35cf278
patch blob:        38510533dc015182f3e87e9d2f3777eea5b8c93b
prerequisite blob: adb330efcc941bf5e646f195c245a3184e42f8e2
```

It applies with zero fuzz and no offsets.

## Historical regex carrier failure

Applying the historical core regex patch after that prerequisite produced:

```text
hunk 1: offset +25
hunk 2: offset +19
hunk 3: failed
```

The source behavior remained recoverable, but the patch was no longer an exact carrier. Accepting offsets would make review depend on patch heuristics. Manual placement would leave no deterministic release artifact.

## Selected correction

The regex layer was regenerated directly from prerequisite blob `adb330ef...` to candidate blob `ca8e656c...`.

The regenerated patch adds:

- basic/extended dialect selection;
- bracket-expression copying and explicit unresolved POSIX rejection;
- contextual anchor handling;
- basic operator/literal reversal;
- capture and backreference preservation;
- branch-leading basic `*` handling;
- literal `\0` handling;
- repeated-quantifier normalization;
- Python-only active `(?...)` rejection;
- malformed active interval rejection;
- consecutive basic interval rejection;
- unmatched extended-close literal handling;
- `x` flag integration before Python compilation.

Exact identities:

```text
patch blob:     7e7d37a77b0215af033b0c97770c83cce130911a
candidate blob: ca8e656c036172230c796a8a12cb17f262108c39
candidate sha:  47e73119f2418fb1e7c47f3eb8f6e82e86a5903ff5c73c68fa5c5ac047ff6308
```

The patch applies in three hunks at exact lines 145, 395, and 425 with zero fuzz and no offsets.

## Parser model

`_translate_pattern()` scans once before `re.compile()` and tracks:

- selected dialect;
- bracket state;
- escaped versus active punctuation;
- branch start/end state;
- basic contextual anchors;
- group starts;
- active interval syntax.

`_normalize_repeated_quantifiers()` performs a second linear pass over the translated expression. It wraps the preceding atom in noncapturing groups when GNU's executed nested repetition semantics differ from Python's parser, preserving user capture numbering.

## Test model

The packet matrix uses three exact files:

1. base source, preserving the direct-Python mismatch;
2. unit-15 prerequisite, preserving the same pattern mismatch and rejecting `x`;
3. regenerated candidate.

Candidate output archives are compared with GNU tar 1.35 under `LC_ALL=C`. The matrix covers ordinary members, hard-link targets, symlink targets, numeric occurrences, successful transforms, shared rejection, and the explicit unsupported POSIX boundary.

All groups passed. A representative freshly materialized gate passed twice with an identical digest.

## Harness defect found and corrected

An early test harness created its baseline by reverse-applying the prerequisite inside the live candidate directory. That restored the old two-value transform loop and caused `ValueError: too many values to unpack` during candidate execution.

This was test ownership, not product behavior. The corrected harness keeps base, prerequisite, and candidate files separate. Every retained result uses the corrected layout.

## Parallel work

All issue #397 units have branches. Tarfilter units 15, 16, and 18–22 contain substantive changes.

- Unit 15 is the direct prerequisite and is vendored exactly.
- Unit 16 already vendors unit 15 before hard-link identity changes.
- Units 18–22 modify independent no-option, ownership, path-filter, parent-retention, and type-class paths.

A future combined branch must compose selected units and inspect source-line overlap. Their existence does not weaken the unit-01 result.

## Compatibility boundary

The claim covers the executed GNU tar 1.35 `LC_ALL=C` subset. The candidate deliberately rejects unresolved POSIX bracket constructs and alphabetic escapes. Locale/collation behavior, expression lists, replacement case state, full diagnostic parity, and regex resource limits remain outside the claim.

## Remaining technical work

1. Select or port transform-related native tests into the upstream project layout.
2. Run them through current `coverage.py` with local `./tarfilter`.
3. Run the appropriate broader native gate.
4. Compose selected parallel tarfilter units and review the complete diff.
5. Create a controlled candidate branch when desired.
6. Resolve exact canonical Salsa head and recheck live overlap immediately before authorization.
