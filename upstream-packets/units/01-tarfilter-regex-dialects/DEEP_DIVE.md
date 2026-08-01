# Deep dive

## Question and observed failure

`tarfilter --transform` advertises GNU tar-style sed expressions, yet the imported implementation extracts the pattern and passes it directly to Python `re.compile()`. GNU tar uses basic regular expressions by default and extended regular expressions only when the `x` transform flag is present. Python gives several punctuation characters extended-style meaning by default.

The smallest distinguishing case under `LC_ALL=C` is member `aaa` with expression `s/a+/b/`:

- imported/predecessor behavior: Python treats `+` as repetition and produces `b`;
- GNU tar 1.35 default-basic behavior: `+` is literal and the name remains `aaa`;
- retained candidate: translates the default basic spelling before Python compilation and remains `aaa`.

The inverse spelling `s/a\+/b/` is active in GNU basic mode and literal in extended mode, so a global punctuation replacement cannot solve the defect.

## Source mechanism

The imported `TransformAction` parses one sed-like substitution, recognizes only trailing `i`, and constructs `re.compile(tokens[0], flags)`. The source lacks an explicit regex-language boundary.

The retained candidate composes four source states:

1. target-scope and replacement handling from PR #68;
2. per-field numeric occurrence state from PR #102;
3. a stateful GNU basic/extended pattern translator from PR #151;
4. edge/parity repairs consolidated through PR #216.

Translation runs once during transform parsing. Archive streaming and per-field substitution continue through Python after the pattern is converted or rejected.

PR #220 adds proof-only tests around one subtle scanner boundary. Active `(?...)` forms reject, while escaped literal parentheses and bracket-expression content stay accepted.

## Reproduction narrative

The focused tests create a PAX archive in memory, run a disposable patched copy of `tarfilter`, and compare its archive snapshot with GNU tar 1.35. Every candidate tree and archive lives under `TemporaryDirectory`.

The baseline test deliberately applies only the target-scope and occurrence patches. It requires:

- `s/a+/b/` to produce `b` on member `aaa`;
- `s/a+/b/x` to fail because `x` is unsupported;
- a valid GNU basic capture/backreference to fail.

The candidate then applies the dialect and edge patches and requires direct GNU equality across operators, anchors, groups, backreferences, intervals, repeated quantifiers, numeric selectors, and member/hard-link/symlink target fields.

The group-guard control test inherits the complete edge matrix and adds:

```text
member: (
expressions: s/\(?/X/x, s/[(?]/X/x, s/\(/X/x
result: X in both candidate and GNU tar
```

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
- Compatibility cost: bounded subset instead of a full GNU/POSIX claim.
- Decision: selected.

## Selected correction

The candidate defaults to GNU basic syntax and enables extended syntax with `x`. It translates only the characterized operator spelling, retains numeric backreferences, preserves capture numbering during repeated-quantifier normalization, handles contextual basic anchors, and rejects unsupported or ambiguous grammar before reading archive data.

The latest product state adds:

- branch-leading basic `*` literal handling;
- literal `\0` handling;
- normalization of executed nested simple and interval quantifiers;
- rejection of Python-only active `(?...)` extensions;
- rejection of malformed active intervals;
- rejection of proven-invalid consecutive basic intervals;
- literal unmatched extended `)` when no group is open.

The latest proof state confirms that the Python-group guard remains narrow:

- escaped literal `\(` stays accepted;
- `(?` characters inside a bracket expression stay accepted;
- escaped `\(?` stays accepted.

## Why the changes belong together

The core translator and repairs share one parser boundary, overlap source lines, and rely on the same GNU differential oracle. Splitting the malformed-grammar repairs from the translator would publish a candidate with known success/error divergence. The repairs therefore belong in the same upstream review unit.

The target-scope and numeric-occurrence patches are prerequisites in the retained Linux Fieldwork test stack. Current upstream review must determine whether those behaviors already exist, should be extracted through unit 15, or require an ordered series before this dialect patch. That prerequisite decision does not divide the regex translator from its grammar repairs.

PR #220 contributes proof only, so its test belongs with the final upstream regression without adding a source commit.

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

## Current package-source analysis

The 2026-08-01 refresh established these package facts:

- Debian Sources lists `mmdebstrap 1.5.7-3` in sid and forky;
- the archive `tarfilter` is 11,453 bytes;
- Salsa tag `debian/1.5.7-3` points to abbreviated commit `6fde9997`;
- a GitHub package-version mirror commit `574048f2a720057b75e56622003932f344dc700a`, described as updating to `1.5.7-3`, carries `tarfilter` Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`;
- that blob equals the Linux Fieldwork imported source.

This is meaningful package-generation corroboration: the retained source is aligned with the currently published Debian source generation. It remains weaker than a direct digest of the Debian archive file and weaker than exact current Salsa `master`. The packet therefore records it as package-source evidence and keeps the canonical rebase gate open.

## Upstream-native test analysis

The published `1.5.7-3` README names the full suite:

```sh
./make_mirror.sh
CMD=./mmdebstrap ./coverage.sh
```

It also names individual execution through `coverage.py`:

```sh
CMD=./mmdebstrap ./coverage.py --dist unstable TEST-NAME
```

`coverage.py` stages a local `./tarfilter` as `shared/tarfilter`, or the installed `/usr/bin/mmtarfilter` when the source-tree file is absent. This gives the rebased candidate an upstream-native path: keep the candidate as `./tarfilter`, identify relevant named tests from `coverage.txt` and `tests/`, run the narrow names, then run the broader suite appropriate to the current tree.

No native command executed here because the runtime could not download or clone the source tree.

## Current-upstream rebase analysis

The canonical repository is the mmdebstrap Salsa project on `master`. The runtime exposed the project and release tags but did not provide the exact current `master` commit or raw tree. Local network commands failed DNS resolution for GitHub and Debian hosts.

Because issue #397 requires an exact current-upstream base and patch application without fuzz or offsets, the package snapshot cannot replace the canonical source gate. The next worker must clone/fetch Salsa, record `git rev-parse HEAD` and `git hash-object tarfilter`, and regenerate the final diff when any prerequisite context changed.

## Overlap analysis

Search date: `2026-08-01`.

- The current Debian BTS listing was searched for tarfilter transform and regex-dialect equivalents; no matching issue appeared.
- Web-indexed Salsa issue and merge-request searches returned no equivalent tarfilter regex carrier.
- Internal carrier review records no competing source translator and no path overlap with caching or LF-23 work at the repaired internal head.
- Exact live Salsa issue/MR inventory remains a required check after canonical access.

## Unresolved discriminators

1. What exact commit is current canonical Salsa `master`?
2. What is the exact canonical `tarfilter` blob at that commit?
3. Which prerequisite transform behaviors are already present there?
4. Do the four retained patches apply exactly, or must the regex unit be regenerated against current source?
5. Which named native tests exercise transform behavior, and what new native regression location fits the project?
6. Does the complete current-source diff remain one coherent MR after prerequisite extraction?
7. Does the live Salsa issue/MR inventory contain equivalent active work invisible to web indexing?

## Evidence limits

- Existing green receipts apply to the retained internal source composition.
- Package-source evidence establishes current Debian release generation, without satisfying exact Salsa `master` identity.
- No fresh patch application or test command ran in this continuation because raw source transfer remained unavailable.
- No controlled upstream fork or candidate branch exists.
- No external contact occurred.
