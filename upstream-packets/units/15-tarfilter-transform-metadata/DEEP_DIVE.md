# Deep dive

## Question and observed failure

Unit 15 asks whether the existing Linux Fieldwork tarfilter repairs can become one coherent current-upstream contribution below the separate regex-dialect work in unit 01.

The exact imported baseline, Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`, exposes several coupled failures:

- `s/a/b/` uses Python `re.sub()` with no count and changes `a/a` to `b/b`; GNU tar changes it to `b/a`.
- `g` and numeric occurrence selectors are rejected by the narrow token parser.
- transforms update `member.name` only, leaving hard-link and symlink targets stale.
- `--strip-components` updates `member.name` only, so a retained hard link may point at the removed prefixed name.
- long PAX `path` and `linkpath` fields can override corrected logical values when copied unchanged into the output archive.

These results belong to `TransformAction` and the archive-member mutation loop. The fixtures use in-memory archives and GNU tar as the reference; no package, privilege, mount, network, or caller-selected cleanup path participates.

## Source mechanism

The baseline parser extracts non-empty tokens with one Python regular expression, accepts only a trailing `i`, stores `(compiled_regex, replacement)`, and later executes:

```python
member.name = r.sub(s, member.name)
```

That selects Python replacement count and replacement-string rules. The same loop lacks link-target ownership. The strip block similarly rewrites only `member.name`. PAX dictionaries are filtered for user-selected keys but otherwise preserved, so old explicit `path` or `linkpath` values retain authority during serialization.

The composed candidate adds four connected pieces:

1. delimiter-aware expression parsing;
2. a replacement callback and occurrence-aware substitution helper;
3. per-transform target scopes and application to selected names and links;
4. PAX invalidation when the corresponding logical field changes.

`SOURCE_MAP.md` records exact symbols and carrier identities.

## Reproduction narrative

The smallest replacement fixture contains one regular member named `a/a`. The baseline changes `s/a/b/` to `b/b` and rejects `s/a/b/g`. The candidate and GNU tar both produce:

- `b/a` for ordinary replacement;
- `b/b` for `g`;
- `[a]/a` for whole-match `&`;
- `x#y/a` for an escaped delimiter.

The target fixture contains `prefix/target`, hard link `prefix/hard -> prefix/target`, and symlink `prefix/sym -> prefix/target`. The baseline changes member names while both targets retain the prefix. The candidate matches GNU tar's default `rsh` target set and uppercase `S` opt-out, extracts successfully, preserves hard-link inode identity, and yields `sym -> target` in the default case.

The PAX fixture uses a 120-byte leaf. The baseline output still exposes the prefixed long path. The candidate writes the stripped leaf, rewrites the hard-link target, regenerates `path` and `linkpath`, and extracts with shared inode identity.

The numeric fixture uses `a/a/a/a`. The PR #68 predecessor rejects `2`; the final candidate and GNU tar agree for `2`, `2g`, `g2`, `0`, `0g`, `22`, `2g3`, and `i2g`. Non-ASCII numeral forms remain rejected.

Full commands and receipts are in `TESTS.md` and `artifacts/`.

## Approach history

### Approach A — retain PR #48 alone

- Mechanism: rewrite hard-link targets and discard stale PAX fields.
- Evidence: short-link and long-PAX tests eventually passed after a malformed retained patch was repaired.
- Result: the accepted regression encoded unchanged default symlink target text.
- Compatibility cost: diverges from GNU tar default `rsh` behavior.
- Disposition: superseded by issue #63 and PR #68.

### Approach B — retain PR #52 stacked composition

- Mechanism: compose first/global replacement and target scopes over an older stack.
- Evidence: direct GNU tar matrices and green CI.
- Result: useful experiment, but duplicated the canonical PR #56 work and remained attached to a stale base.
- Compatibility cost: omitted later replacement and numeric behavior.
- Disposition: closed unmerged and superseded by PRs #56, #68, and #102.

### Approach C — preserve historical PR #68 and PR #102 as an ordered patch pair

- Mechanism: apply PR #68, then the incremental numeric-selector patch from PR #102.
- Evidence: both exact Git blobs pass `git apply --check` and apply in order.
- Result: source composition succeeds, but the historical patches apply with line offsets; GNU patch 2.8 rejects the first parser hunk of PR #68.
- Compatibility cost: a release packet would inherit avoidable application-tool and offset ambiguity.
- Disposition: retained as provenance and negative-predecessor evidence, not selected as the release carrier.

### Approach D — regenerate one clean patch from exact baseline to composed source

- Mechanism: materialize the exact imported baseline, compose the canonical carriers, and generate a new one-file diff.
- Evidence: GNU `patch --fuzz=0` applies cleanly with no offsets and produces a byte-identical candidate; the matrix passes three direct runs plus the packet wrapper run.
- Result: selected candidate carrier.
- Compatibility cost: one 179-addition/23-deletion source patch requires careful complete-diff review; upstream may prefer two commits.
- Disposition: selected for the next upstream-native integration pass.

## Selected correction

The selected correction is `patches/0001-tarfilter-transform-metadata.patch`, generated from the exact baseline to the composed PR #68 plus PR #102 source state. It keeps the existing Python pattern dialect and changes only replacement parsing, selector state, target ownership, link rewriting, and PAX invalidation.

This is the smallest coherent source state currently supported by the carrier history. Splitting before upstream-native review would either duplicate parser state or edit the same member loop twice without proving a cleaner review boundary.

## Why the changes belong together

The affected behavior shares one parsed transform object and one application loop. Replacement count, numeric selection, and target scopes must travel together so member names and each selected link target use the same occurrence policy. PAX invalidation depends on whether those exact logical fields changed. Component stripping uses the same link/PAX invariant even though it does not use the transform parser.

A potential ordered series remains viable:

1. replacement parser and occurrence semantics;
2. link-target, strip, and PAX consistency.

That series becomes preferable only if a current upstream checkout demonstrates clean independent tests and a complete diff with minimal overlapping edits.

## Compatibility analysis

### Archive names and logical content

Regular-file payload bytes remain unchanged. Member names change only according to the requested strip or transform. Numeric occurrence counting resets independently for each member name and each selected link target.

### Links and extraction

Hard-link targets follow selected strip and transform operations. Default transforms include hard-link and symlink targets; uppercase scope flags disable their respective targets. The focused default archive extracts successfully, the regular file and hard link share one inode, and the symlink target matches GNU tar.

### PAX metadata

When `member.name` changes, explicit `path` is removed. When a hard-link or symlink target changes, explicit `linkpath` is removed. Python's PAX writer regenerates long values from the corrected logical fields. Other PAX keys retain existing filtering behavior.

### Diagnostics and unsupported grammar

Unsupported and duplicate letter flags fail. Non-ASCII numeral characters fail like GNU tar. The candidate does not claim complete GNU transform grammar. Unit 01 owns basic/extended pattern translation; expression lists, persistent `flags=`, case conversion, locale/collation, and broader malformed-expression parity remain separate.

### Cleanup and host state

All matrix work uses `TemporaryDirectory` or `mktemp -d` with a fixed trap-owned root. It creates no mounts, sockets, containers, packages, privileged state, or external messages. Immediate reruns leave no matching temporary directory.

## Negative controls and losing mutations

The matrix can lose in four distinct ways:

- exact baseline must produce `b/b` for ordinary replacement and reject `g`;
- exact baseline must preserve stale link targets under a default transform;
- exact baseline must preserve a stale prefixed long PAX path under strip;
- the PR #68 predecessor must reject a numeric selector.

Candidate results are compared with GNU tar, extraction, inode identity, and explicit PAX values. Removing either the integrated semantic patch or the numeric portion makes a named negative control fail.

## Current upstream and historical review

On 2026-08-01, the public canonical repository showed `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`. Its repository listing reported `tarfilter` last changed by commit prefix `87b9b385b3` on 2024-09-13. Current source inspection retained the baseline parser and name-only transform loop. The visible open issue list contained six unrelated reports, and targeted search found no active equivalent carrier.

Historical Linux Fieldwork review corrected two important carrier defects:

- PR #48 initially contained malformed patch metadata and later encoded the wrong default symlink scope.
- PR #102's first numeric parser used `str.isdigit()`, which over-accepted Unicode numerals; the final patch uses ASCII digits only.

These findings remain visible in `SOURCE_MAP.md`, `TESTS.md`, and `DECISIONS.md`.

## Remaining questions

1. **Upstream-native test location and style.** Discriminator: inspect a current upstream checkout, identify the accepted tarfilter test entry point, convert the retained matrix, and execute it.
2. **One commit or ordered series.** Discriminator: review the complete current-upstream diff and test ownership after conversion; choose the form with fewer overlapping edits and clearer independent regressions.
3. **Current checkout integration.** Discriminator: apply the clean patch to a full checkout at `77ec9be5417ee44c96343d2347145585da1b1f94`, run focused repository gates, and record the candidate commit.
4. **Controlled fork and branch.** Discriminator: repository owner creates or identifies an authorized controlled fork. No public action occurs before that decision.

## Evidence boundary

Demonstrated on Python 3.13.5 and GNU tar 1.35 using the exact imported source blob and the visible current-upstream source identity. The matrix covers focused in-memory PAX archives, GNU tar differential behavior, extraction, hard-link inode identity, cleanup, and immediate rerun. It does not establish the full upstream test suite, Debian package integration, other tar implementations, other Python versions, every transform grammar feature, or maintainer acceptance.

## Reopen triggers

- upstream `tarfilter` changes from the inspected implementation;
- unit 01 changes the parsed transform representation in an incompatible way;
- upstream-native tests reveal an independent split boundary;
- a public equivalent carrier appears;
- Python PAX serialization changes the regeneration behavior;
- explicit external authorization or destination policy changes.
