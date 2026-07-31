# Changed unified-diff carrier validation

## TL;DR

Linux Fieldwork now has a source-independent validator for the grammar of newly added or modified `.patch` files. It checks textual file sections, unified-diff hunk headers, declared old/new line counts, and carrier identity before behavioral tests run.

The gate catches malformed patch packaging. It does not prove that a patch applies to its intended source, applies with zero fuzz, composes after prerequisite patches, or implements the right behavior.

## Explain like I'm five

A patch says, “remove this many old lines and add this many new lines.”

Several recent repair sheets said one number while containing another. The repair idea could be correct, but the sheet itself could not be followed. This validator counts the instructions before the larger test starts.

It also makes sure the sheet is a real file in the project rather than a shortcut to some other file.

## Why care

Recent investigations repeatedly reached the same first failure:

```text
candidate mechanism not yet executed
→ retained patch header has a stale or incorrect count
→ patch application fails or requires fuzz
→ every downstream behavioral test turns red
```

That is a patch-carrier defect, not product evidence. Catching it in the ordinary repository gate shortens feedback and keeps failure ownership accurate.

A repository gate must also avoid false rejection. Unified-diff hunk content can contain bytes that resemble file headers or format-patch framing. The parser must use section state and declared counts rather than treating every lookalike line as top-level syntax.

## Exact boundary

Owning issue: #294. Canonical review carrier: PR #302.

Branch: `tooling/unified-diff-hunk-validator-current-main`.

Current-main source generation began from `a636a071de07cc94f797c899c082a271df79e833`. The semantic parser-review head before this record refresh is `b0f25a3a6ada3ebb71c9f56544fdf0394ff60770`.

Changed surfaces:

- `tools/validate_unified_diffs.py`;
- `tests/test_validate_unified_diffs.py`;
- `tests/fixtures/unified-diff-validator/valid.patch`;
- `.github/workflows/linux-fieldwork-ci.yml`;
- this record.

## Candidate contract

The validator:

- accepts files or directories;
- recursively scans directories for `*.patch`;
- supports Git unified-diff metadata;
- supports ordinary Git-separated and plain multi-file unified diffs;
- supports multiple hunks per textual file section;
- supports omitted hunk counts, where the count means one;
- supports zero-count insertion and deletion hunks;
- ignores the standard `\ No newline at end of file` marker;
- accepts Git binary and genuine metadata-only patches without textual hunks;
- accepts a format-patch signature after a complete hunk;
- treats `-- ` as a valid deletion line while a hunk still needs old lines;
- rejects malformed hunk headers;
- rejects unpaired textual file headers;
- rejects textual file headers without a hunk;
- rejects hunks without a preceding textual file header;
- rejects empty `diff --git` file-section shells with no textual, binary, or metadata-change payload;
- rejects bare or invalidly prefixed hunk-body lines;
- rejects extra body lines after the declared counts are already satisfied;
- rejects declared old/new counts that do not match the hunk body;
- rejects symbolic-link patch paths rather than following them outside carrier identity;
- provides text and JSON output;
- returns nonzero when any finding exists.

The pull-request workflow checks only patch files added, copied, modified, renamed, or type-changed by that pull request. Historical retained patches therefore do not block unrelated work merely because they apply to a stacked or old source state.

## Why this approach

A repository-wide `patch --dry-run` or `git apply --check` against every retained patch would be misleading. Many investigations intentionally carry:

- patches for imported source copies;
- patches that apply after a prerequisite patch;
- historical evidence against an older exact source;
- competing variants retained for comparison.

Hunk grammar and line counts are source-independent. Source applicability and zero-fuzz application are source-dependent. Keeping those gates separate catches a recurring packaging defect without pretending all retained patches share one application context.

Rejecting symbolic links keeps the checked object equal to the tracked carrier path. Following a link could validate bytes outside the proposed repository object and make the result depend on runner state.

## Focused controls

The complete focused file contains nineteen controls:

- the repository fixture that also triggers the changed-file workflow gate;
- valid Git-separated multi-file and multi-hunk patches;
- valid plain multi-file patches without `diff --git` separators;
- omitted counts;
- zero-count insertion and deletion;
- no-newline markers;
- format-patch signature handling;
- a valid deleted line encoded as `-- `;
- hunk content that resembles `---` and `+++` file headers;
- mode-only Git patches;
- empty Git file-section rejection;
- malformed hunk headers;
- old/new count mismatches;
- extra body after satisfied counts;
- missing, unpaired, and headerless textual sections;
- invalid body prefixes and bare empty hunk lines;
- non-patch prose;
- symbolic-link carrier rejection;
- recursive directory discovery, explicit JSON schema, and failure status.

Initial exact-file local execution, before the section-boundary review repairs:

```text
python3 -m compileall -q tools tests
python3 -m unittest discover -s tests -v
```

Result: compilation passed; the then-current focused tests passed. The local Python environment emitted an unrelated spreadsheet-runtime warmup warning before execution, but both commands completed with status 0.

Complete-diff review then found five source-independent authority gaps:

1. process substitution could hide a failing changed-file `git diff` as an empty list;
2. a plain multi-file patch or an extra line after satisfied hunk counts could be parsed incorrectly;
3. a valid deletion line `-- ` could be mistaken for a format-patch signature while counts were incomplete;
4. a bare `diff --git` shell with no payload could be accepted as metadata-only;
5. a `.patch` symbolic link could make the validator follow bytes outside the tracked carrier identity.

The workflow now writes the NUL-delimited path list under direct `set -e` control. The parser tracks textual and Git sections, distinguishes in-hunk content from top-level framing, requires real section payload, and rejects symbolic-link carriers. Hosted exact-head repository CI is the first authoritative execution of the complete nineteen-test file and changed-patch workflow step.

## Workflow behavior

For pull requests, the workflow obtains the exact base and head SHAs from the event, writes added or modified `*.patch` paths to a disposable NUL-delimited file, and invokes:

```text
python3 tools/validate_unified_diffs.py -- <changed patch paths>
```

The `git diff` command runs directly under `set -e`; a discovery failure cannot be hidden as an empty patch list. The disposable list is removed by an EXIT trap. NUL delimiters preserve unusual path names.

Workflow-dispatch runs skip the changed-file step because they have no pull-request base/head pair.

## Complete-diff review

The five-file review checked:

- parser Git-section, textual-section, and hunk state;
- plain versus Git-separated multi-file boundaries;
- content lines resembling file headers or email framing;
- omitted and zero count semantics;
- extra-body detection;
- binary and metadata-only boundaries;
- tracked carrier identity and symbolic-link behavior;
- text and JSON result authority;
- changed-file diff filtering;
- NUL-safe path transfer;
- fail-closed discovery;
- disposable-list cleanup;
- direct execution of the new gate by this PR's valid patch fixture;
- separation from source application and semantic claims.

No imported source, product candidate, external workflow, secret, live target, destructive action, or external interaction is included.

## Evidence boundary

This establishes patch syntax, section payload, hunk-count integrity, and direct carrier-file identity only.

It does not establish:

- source identity;
- source applicability;
- zero-fuzz application;
- correct patch order;
- semantic correctness;
- complete candidate composition;
- behavior under the target tool or platform.

Every investigation that proposes a patch must still apply its exact retained bytes to the exact declared source with zero fuzz when that is part of the claim, compile or parse the resulting source, and run the distinguishing behavioral controls.

## Disposition

`REVIEW REPAIRED — HOLD` until exact-head Linux Fieldwork CI passes and confirms that the changed valid fixture executes through the new workflow step.

A green result on an unchanged head should move this internal repository tool to `MERGE LOCALLY`.

## Authority

Internal Linux Fieldwork tooling only. External contact authorized: false.
