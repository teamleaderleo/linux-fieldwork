# uutils `cat`: bind input classification to the opened file descriptor

## TL;DR

Current `cat` classifies a pathname with `metadata(path)` and then separately opens that pathname. A directory-entry replacement between those operations can make the classification describe one object while `cat` reads another.

The refined candidate treats stdin separately, opens each non-stdin pathname once, classifies supported file types from that opened descriptor, performs output-is-input comparison on it, and reads it. Narrow path lookups remain only where no file was opened: cross-Unix failed-open diagnostic refinement and a non-Unix directory compatibility precheck.

## Explain like I'm five

`cat` currently asks, “What is behind this name?” Then it asks again, “Open whatever is behind this name.” Someone can change the name between those questions.

The repair says, “Open it once. Ask the opened thing what it is. Read that same opened thing.”

## Why care

The current sequence is a time-of-check/time-of-use identity error. Concurrent rename activity can make diagnostics and consumed data disagree; in an attacker-writable directory, the checked object can differ from the object actually read.

## Current state

- State: `EXECUTING`
- Canonical source head: `uutils/coreutils@a0cb02453f314bdd3addda6f321f7e03adceb56b`
- Controlled source branch: `teamleaderleo/coreutils:fieldwork/cat-fd-classification-toctou-13042-v2`
- Controlled staged head: `0a1e4aab8aaaff6a728aa13f8077802788d6174e`
- Controlled draft PR: `teamleaderleo/coreutils#5`
- First incomplete step: inspect the focused hosted workflow
- Cleanup state: transformer and workflow remain until green source-only promotion
- Next safe action: classify the first failed gate or inspect the final source-only diff if green
- External-contact state: no canonical-upstream contact authorized or made

## Intent and precedent

uutils aims to be a reliable GNU-compatible implementation while supporting Unix, Windows, WASI, Android, BSDs, and macOS. Paths remain `Path`/`OsStr`, behavior requires regression coverage, and changes must be rustfmt/clippy-clean.

Historical source shows that stdin handling was folded into a broad `InputType` path classifier in 2022. That reduced duplicate branching but made every pathname pass through a metadata check before opening. Issue `#13042` identifies that identity split.

## Question

Can `cat` classify and consume the same filesystem object while preserving stdin, directory, socket, symlink-loop, unknown-type, and output-is-input behavior across supported platforms?

## Source

- Project: uutils/coreutils
- Issue: `#13042`
- Resolved commit: `a0cb02453f314bdd3addda6f321f7e03adceb56b`
- Controlled comparison base: `teamleaderleo/coreutils:base/canonical-main-20260804`
- Controlled candidate branch: `fieldwork/cat-fd-classification-toctou-13042-v2`
- Candidate source commit: pending promotion
- Imported source: none; exact Git identities are the source boundary

## Environment

- Black-box oracle: GNU `cat` 9.7
- Probe host: Linux, x86_64
- Candidate execution: GitHub Actions Ubuntu 24.04
- Privileges: ordinary user

## Baseline behavior

`cat_path()` calls `get_input_type(path)`, which follows the pathname and returns a broad enum. For readable file types, `cat_path()` then calls `File::open(path)` separately. The path can resolve differently between those operations.

## Diagnostic boundary

On Linux:

| Input | `open(O_RDONLY)` | GNU diagnostic |
|---|---|---|
| directory | succeeds; descriptor metadata is directory | `Is a directory` |
| Unix socket | fails with `ENXIO` | `No such device or address` |
| symlink loop | fails with `ELOOP` | `Too many levels of symbolic links` |

Self-review did not assume every Unix target formats raw open errors identically. A failed open consumes no file, so the candidate may consult the pathname only to preserve the established socket diagnostic and retains the existing symlink-loop error mapping.

## Refined candidate

### Successful open

- use `file.metadata()`;
- reject directories;
- accept the same regular/FIFO/character/block types the old classifier accepted;
- retain `UnknownFiletype` for unsupported opened types;
- compare the descriptor to stdout;
- read that same descriptor.

### Failed open

- no file can be consumed, so a path lookup may refine a socket error without recreating the checked-object/read-object split;
- retain the platform-specific symlink-loop mapping.

### Non-Unix

Retain a narrow pre-open directory check where opening a directory cannot yield a descriptor suitable for post-open classification. After a successful open, preserve regular-versus-unknown classification from descriptor metadata.

### Removed structure

The private `InputType` enum and `get_input_type(path)` are removed. The user-visible `UnknownFiletype`, directory, socket, symlink-loop, and output-is-input errors remain.

## Tests

### Descriptor identity unit test

1. Create and open a regular file.
2. Rename its pathname away.
3. Create a directory at the original pathname.
4. Classify the already-open file.
5. Assert descriptor classification remains regular while the pathname is now a directory.

### Existing integration coverage reused

- `test_domain_socket`;
- `test_error_loop`;
- directory tests;
- complete `test_cat` integration module.

The final candidate adds no duplicate integration tests and is fenced to one source file.

## Self-review record

- fixed a marker-bound transformer bug before execution;
- rejected a first design that removed explicit socket/symlink-loop diagnostics;
- rejected a second design that removed unknown-file-type behavior;
- reused existing integration tests instead of adding duplicates;
- reduced the intended promoted diff to `src/uu/cat/src/cat.rs` only.

No product result is claimed until the hosted gate completes.

## Interpretation

The operation owner is the opened descriptor. Path information remains appropriate only when no descriptor exists or a platform cannot provide one for an established diagnostic.

## Evidence boundary

The deterministic test proves descriptor classification after pathname replacement but does not exploit a live process race. Linux open behavior was black-box verified; other platform CI remains pending. This candidate does not address output pathname changes outside the input-open boundary.

## Next step

Inspect the focused workflow. If green, confirm promotion leaves only `src/uu/cat/src/cat.rs`, review every changed line, compare against current canonical main, and update this record with exact blobs and receipts.

## Authority

No canonical-upstream issue comment, pull request, review, email, patch submission, or other contact has been authorized or made.