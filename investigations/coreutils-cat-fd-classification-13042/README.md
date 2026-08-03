# uutils `cat`: bind input classification to the opened file descriptor

## TL;DR

Current `cat` classifies a pathname with `metadata(path)` and then separately opens that pathname. A directory-entry replacement between those operations can make the classification describe one object while `cat` reads another.

The controlled candidate treats stdin separately, then on Unix opens each pathname once, rejects directories from `file.metadata()`, performs output-is-input comparison on that descriptor, and reads the same descriptor. A narrow non-Unix directory precheck remains because some supported platforms cannot open directories as regular files and would otherwise lose the established “Is a directory” diagnostic.

## Explain like I'm five

`cat` currently asks, “What is behind this name?” Then it asks again, “Open whatever is behind this name.” Someone can change the name between those questions.

The repair says, “Open it once. Ask the opened thing what it is. Read that same opened thing.”

## Why care

The current sequence is a time-of-check/time-of-use identity error. In an attacker-writable directory, a checked regular file can be replaced before opening, or a checked special object can be replaced by a different readable object. Even without an attacker, concurrent rename activity can make diagnostics and consumed data disagree.

## Current state

- State: `EXECUTING`
- Canonical source head: `uutils/coreutils@a0cb02453f314bdd3addda6f321f7e03adceb56b`
- Controlled source branch: `teamleaderleo/coreutils:fieldwork/cat-fd-classification-toctou-13042-v2`
- Controlled staged head: `820678ece416b47f9889867a3ef6d6c0ab7addbb`
- Controlled draft PR: `teamleaderleo/coreutils#5`
- First incomplete step: inspect the `Fieldwork cat descriptor classification` workflow
- Cleanup state: transformer and workflow remain until a green push-side promotion
- Next safe action: classify the first failed gate or inspect the final source-only diff if green
- External-contact state: no canonical-upstream contact authorized or made

## Intent and precedent

uutils aims to be a reliable GNU-compatible implementation while supporting Unix, Windows, WASI, Android, BSDs, and macOS. Path inputs should remain `Path`/`OsStr`, behavior should be regression-tested, and changes must be rustfmt/clippy-clean.

Historical source shows that stdin handling was intentionally folded into a broad `InputType` classifier in 2022. That refactor reduced duplicate branching but also made all pathname inputs pass through a path-based metadata check before opening. Current issue `#13042` identifies that identity split.

## Question

Can `cat` classify and consume the same filesystem object on Unix while preserving existing stdin, directory, socket, symlink-loop, and output-is-input behavior across supported platforms?

## Source

- Project: uutils/coreutils
- Issue: `#13042`
- Requested revision: canonical `main`
- Resolved commit: `a0cb02453f314bdd3addda6f321f7e03adceb56b`
- Controlled comparison base: `teamleaderleo/coreutils:base/canonical-main-20260804`
- Controlled candidate branch: `fieldwork/cat-fd-classification-toctou-13042-v2`
- Candidate source commit: pending promotion
- Imported source: none; exact Git identities are the source boundary

## Environment

- Black-box oracle: GNU `cat` 9.7
- Probe host: Linux, x86_64
- Shell: bash
- Candidate execution: GitHub Actions Ubuntu 24.04
- Privileges: ordinary user

## Baseline behavior

Current `cat_path()` calls `get_input_type(path)`. That helper calls `metadata(path)`, follows symlinks, classifies the resulting type, and returns a broad enum. For most types, `cat_path()` then calls `File::open(path)` separately.

The path can resolve differently between those calls.

## Black-box diagnostic receipt

On Linux, GNU `cat` 9.7 and direct open behavior align:

| Input | `open(O_RDONLY)` | GNU diagnostic |
|---|---|---|
| directory | succeeds; descriptor metadata is directory | `Is a directory` |
| Unix socket | fails with `ENXIO` | `No such device or address` |
| symlink loop | fails with `ELOOP` | `Too many levels of symbolic links` |

This supports descriptor-first classification without recreating socket or loop diagnostics in a separate path classifier.

## Candidate

### Unix

1. Handle `-` as stdin before filesystem opening.
2. Open a non-stdin path once.
3. Use `file.metadata()` to reject a directory.
4. Check whether that same file is stdout.
5. Read that same file.

### Non-Unix

Retain a narrow path-based directory precheck, then open once. This is a compatibility concession for platforms where `File::open(directory)` fails with a generic access error before descriptor metadata can be inspected.

### Removed structure

The broad private `InputType` enum and path classifier are removed. File kinds that can be read require no preclassification; socket and symlink-loop errors already come from opening the path.

## Tests

### Descriptor identity unit test

1. Create a regular file.
2. Open it.
3. Rename the pathname away.
4. Create a directory at the original pathname.
5. Run the candidate directory check on the already-open file.
6. Assert that the descriptor is still recognized as a regular file while the pathname is now a directory.

This deterministically proves the identity distinction without a timing race.

### Diagnostic integration tests

- existing directory tests remain;
- bind a Unix-domain socket and require `No such device or address`;
- create a two-link symlink loop and require `Too many levels of symbolic links`;
- run the complete `cat` integration module;
- run focused clippy and rustfmt.

## Results

The candidate is staged behind a corrected fail-closed transformer. An initial self-review found that a marker-bounded replacement would duplicate its end marker; that tooling bug was fixed before any candidate execution.

No product result is claimed until the hosted gate completes.

## Interpretation

The important abstraction is not “file type by pathname.” It is “an opened input that may need one post-open rejection.” On Unix, directory status belongs to the opened descriptor; sockets and symlink loops are open failures; other readable types can proceed without a type enum.

The non-Unix precheck is deliberately narrower than the original classifier and exists to preserve user-visible diagnostics, not to drive which object is read on Unix.

## Evidence boundary

The deterministic identity test proves descriptor classification after a pathname replacement but does not attempt to exploit a live process race. Linux socket and symlink-loop errors were black-box verified. Windows, WASI, and BSD/macOS CI results remain pending. The candidate does not address path changes during later diagnostics or output path handling outside this input-open boundary.

## Next step

Inspect the controlled workflow. If green, confirm promotion leaves only `src/uu/cat/src/cat.rs` and `tests/by-util/test_cat.rs`, inspect every changed line, compare against current canonical main, and update this record with exact blobs and receipts.

## Authority

No canonical-upstream issue comment, pull request, review, email, patch submission, or other contact has been authorized or made.