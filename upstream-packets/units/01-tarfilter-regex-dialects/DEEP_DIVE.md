# Deep dive

## Question and observed failure

`tarfilter --transform` advertises GNU tar-style sed expressions, yet the imported implementation extracts the pattern and passes it directly to Python `re.compile()`. GNU tar uses basic regular expressions by default and extended regular expressions only when the `x` transform flag is present. Python gives several punctuation characters extended-style meaning by default.

The smallest distinguishing case under `LC_ALL=C` is member `aaa` with expression `s/a+/b/`:

- imported/predecessor behavior: Python treats `+` as repetition and produces `b`;
- GNU tar 1.35 default-basic behavior: `+` is literal and the name remains `aaa`;
- retained candidate: translates the default basic spelling before Python compilation and remains `aaa`.

The inverse spelling `s/a\+/b/` is active in GNU basic mode and literal in extended mode, so a single global punctuation replacement cannot solve the defect.

## Source mechanism

The imported `TransformAction` parses one sed-like substitution, recognizes only trailing `i`, and constructs `re.compile(tokens[0], flags)`. The source lacks an explicit regex-language boundary.

The retained candidate composes four source states:

1. target-scope and replacement handling from PR #68;
2. per-field numeric occurrence state from PR #102;
3. a stateful GNU basic/extended pattern translator from PR #151;
4. edge/parity repairs consolidated through PR #202 and PR #216.

Translation runs once during transform parsing. Archive streaming and per-field substitution continue through Python after the pattern is converted or rejected.

## Reproduction narrative

The focused tests create a PAX archive in memory, run a disposable patched copy of `tarfilter`, and compare its archive snapshot with GNU tar 1.35. Every candidate tree and archive lives under `TemporaryDirectory`.

The baseline test deliberately applies only the target-scope and occurrence patches. It requires:

- `s/a+/b/` to produce `b` on member `aaa`;
- `s/a+/b/x` to fail because `x` is unsupported;
- a valid GNU basic capture/backreference to fail.

The candidate then applies the dialect and edge patches and requires direct GNU equality across operators, anchors, groups, backreferences, intervals, repeated quantifiers, numeric selectors, and member/hard-link/symlink target fields.

## Approach history

### Directly use Python `re`

- Mechanism: compile the advertised GNU expression without translation.
- Result: default GNU basic punctuation silently acquires Python extended meaning; Python-only groups can execute.
- Compatibility cost: successful commands can produce different archive paths.
- Decision: rejected.

### Global punctuation replacements

- Mechanism: replace characters such as `+`, `?`, `|`, parentheses, and braces without parser state.
- Result: escapes, bracket expressions, group/alternation boundaries, contextual anchors, and repeated quantifiers require local context.
- Compatibility cost: corrupts literals or activates operators in the wrong locations.
- Decision: rejected.

### Invoke GNU tar or sed per member

- Mechanism: delegate matching externally for each transformed field.
- Result: process-launch cost and lifecycle complexity enter a streaming archive filter; target scopes, occurrence state, PAX updates, and archive output remain local concerns.
- Compatibility cost: substantial runtime and operational expansion.
- Decision: rejected for this unit.

### Implement complete POSIX/GNU regex compatibility

- Mechanism: add full locale, collation, bracket-class, escape, diagnostic, and performance parity.
- Result: expands one bounded interoperability fix into a large regex-engine project.
- Compatibility cost: review size and dependency/runtime policy grow sharply.
- Decision: deferred; the selected candidate supports the executed subset and rejects unresolved forms early.

### Stateful bounded translator

- Mechanism: scan the pattern with explicit dialect, escape, bracket, branch, anchor, group, and interval state; normalize the executed repeated-quantifier cases; reject unresolved syntax before archive processing.
- Result: direct equality with the retained GNU tar matrix and visible failure for unproved forms.
- Compatibility cost: bounded subset rather than a full GNU/POSIX claim.
- Decision: selected.

## Selected correction

The candidate defaults to GNU basic syntax and enables extended syntax with `x`. It translates only the characterized operator spelling, retains numeric backreferences, preserves capture numbering during repeated-quantifier normalization, handles contextual basic anchors, and rejects unsupported or ambiguous grammar before reading archive data.

The latest edge state adds:

- branch-leading basic `*` literal handling;
- literal `\0` handling;
- normalization of executed nested simple and interval quantifiers;
- rejection of Python-only active `(?...)` extensions;
- rejection of malformed active intervals;
- rejection of proven-invalid consecutive basic intervals;
- literal unmatched extended `)` when no group is open.

## Why the changes belong together

The core translator and repairs share one parser boundary, overlap source lines, and rely on the same GNU differential oracle. Splitting the malformed-grammar repairs from the translator would publish a candidate with known success/error divergence. The repairs therefore belong in the same upstream review unit.

The target-scope and numeric-occurrence patches are prerequisites in the retained Linux Fieldwork test stack. Current upstream review must determine whether those behaviors already exist, should be extracted through unit 15, or require an ordered series before this dialect patch. That prerequisite decision does not divide the regex translator from its grammar repairs.

## Compatibility analysis

### Archive content and metadata

The correction changes transform matching and therefore member names plus the hard-link and symlink targets selected by prerequisite scope state. Archive payload bytes remain unchanged. PAX `path` and `linkpath` behavior belongs to the prerequisite target-scope state and unit 15.

### Exit and output behavior

Unsupported or malformed patterns fail during argument parsing before archive output. This prevents partial archives for grammar the candidate declines to interpret. Exact diagnostic wording parity remains outside the claim.

### Locale and encoding

The retained differential evidence uses `LC_ALL=C` and GNU tar 1.35. Locale-sensitive ranges, collating elements, equivalence classes, Unicode behavior, and archive-name encoding parity remain open.

### Performance

The candidate continues to use Python `re` after translation. Catastrophic-backtracking policy and regex resource limits remain open. The translator adds a linear parser pass over each expression.

### Existing callers

Callers relying on Python-only default regex meaning would see changed behavior. The advertised GNU tar contract and direct GNU differential are the selected compatibility authority. Python-only `(?...)` expressions change from accepted execution to early rejection.

## Current-upstream rebase analysis

The canonical repository is the mmdebstrap Salsa project on `master`. This session established no exact current Salsa commit because the available runtime could not retrieve it. The local container clone command failed with DNS resolution:

```text
git clone https://github.com/teamleaderleo/linux-fieldwork.git
fatal: unable to access 'https://github.com/teamleaderleo/linux-fieldwork.git/': Could not resolve host: github.com
```

The GitHub connector independently verified the Linux Fieldwork branch and source blobs. A GitHub mirror's `tarfilter` has the same Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` as the imported Linux Fieldwork file, which corroborates the retained base bytes only. The mirror does not establish current canonical state.

Because issue #397 requires an exact current-upstream base and patch application without fuzz or offsets, applying the retained stack to the old imported blob again would add no release evidence. The safe stopping point is a pinned rebase manifest and exact next command on a runtime with canonical Salsa access.

## Overlap analysis

Internal carrier review records no competing source translator and no path overlap with caching or LF-23 work at the repaired internal head. Current Salsa source, issues, and merge requests require a fresh search after canonical access. No current-upstream absence claim is made here.

## Unresolved discriminators

1. What exact commit is current canonical Salsa `master`?
2. Which prerequisite transform behaviors are already present in that commit?
3. Do the four retained patches apply exactly, or must the regex unit be regenerated against current source?
4. Which upstream-native test entry points exercise `tarfilter`?
5. Does a current active issue or merge request implement equivalent dialect handling?
6. Does the complete current-source diff remain one coherent MR after prerequisite extraction?

## Evidence limits

- Existing green receipts apply to the retained internal source composition, not a current canonical rebase.
- No test command ran in this session because source checkout and exact upstream retrieval were unavailable.
- No controlled upstream fork or candidate branch exists.
- No external contact occurred.
