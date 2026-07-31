# Debian submission source-receipt authority

## TL;DR

The hosted verification workflow for Debian bug #1135727 checked the submitted patch's exact source boundary with inline Python `assert` statements. Those debug-only checks disappear under optimized Python.

This repair replaces them with explicit `SystemExit` diagnostics and executes the exact extracted workflow receipt under ordinary Python and `python -O`.

The sent patch, email, recipients, Debian bug thread, imported source, and external-contact authority are unchanged.

## Explain like I'm five

The workflow checks that the patch changed the intended sentences exactly once. The old checks were written in erasable ink. The new checks are ordinary locked checks that run in both Python modes.

## Why care

This workflow is part of the evidence chain for an authorized external submission. Evidence-authority checks must not depend on Python debug mode, even though the hosted command normally runs without optimization.

This is evidence hardening. No false green under the ordinary hosted mode was observed.

## Exact boundary

Owning issue: #308. Canonical PR: #311. Branch: `repair/mmdebstrap-1135727-explicit-source-receipt-current-main`.

Current-main base: merged patch-validator commit `e93b0353871dd29ebf9eda32245b2607f9572cc7`.

The candidate changes exactly:

- `.github/workflows/verify-mmdebstrap-1135727-submission.yml`;
- `tests/test_mmdebstrap_1135727_submission_source_receipt.py`;
- this record.

The predecessor workflow used eight inline assertions:

- four exact source-line counts;
- one documentation count;
- one coverage-registration count;
- two shell-test containment checks.

## Candidate contract

The workflow receipt now defines:

- `require_exact_count(text, needle, label)` for the original exact-once boundaries;
- `require_contains(text, needle, label)` for the original containment boundaries;
- explicit diagnostics containing the boundary label, observed count when relevant, and missing text.

The same pristine imported revision, patch bytes, three-file ownership inventory, executable bit, syntax gates, focused runtime probe, and sent-mail record remain authoritative.

## Focused regression

The repository test:

- extracts the exact heredoc from the workflow;
- parses it with `ast` and rejects any `ast.Assert` node;
- creates a disposable complete source, coverage, and shell-test fixture;
- executes the exact block under ordinary Python and `python -O`;
- removes and duplicates a required source line;
- removes the documentation line;
- removes and duplicates the coverage marker;
- removes each shell-test marker;
- requires both modes to fail with the same final explicit diagnostic;
- compares the final diagnostic rather than all stderr, so unrelated startup warnings cannot create false disagreement;
- leaves no repository state.

## Exact hosted evidence

The first reviewed head `db6b325e9e38835f12f50b755db694a0c36ba677` passed:

- Linux Fieldwork CI `30626251682` / 865;
- Verify Debian bug 1135727 submission `30626251692` / 14;
- Verify mmdebstrap explicit TMPDIR handling `30626251731` / 129;
- Deep review mmdebstrap TMPDIR handling `30626251673` / 96.

The first current-main restack `dd9d958796229d82a0323dae223a19ee3e04eda7` also passed all four relevant workflows:

- Linux Fieldwork CI `30628486206` / 888;
- Verify Debian bug 1135727 submission `30628486170` / 15;
- Verify mmdebstrap explicit TMPDIR handling `30628486188` / 131;
- Deep review mmdebstrap TMPDIR handling `30628486113` / 98.

Both generations ran all four focused ordinary/optimized receipt tests. Both dedicated submission workflows passed exact patch application, exact changed-file and source ownership, syntax and focused runtime behavior, and the sent-mail record.

After run 888, patch-validator PR #302 merged into `main` as `e93b035…`, changing the default repository gate but not this unit's three files. The exact workflow and focused-test blobs are now restacked unchanged on that merged main generation. This record is the only changed candidate blob.

## Why this approach

Changing the production workflow to run only with `python -O` would prove one mode while changing normal invocation. Static text matching alone would not prove failure behavior.

Executing the exact extracted block in both modes preserves production behavior, proves optimizer parity, and automatically puts later workflow edits inside the regression.

## Complete-diff review

Review confirmed:

- source, documentation, and coverage remain exact-count checks;
- shell markers remain containment checks;
- the pristine source revision and changed-file inventory are unchanged;
- the patch, mail record, verifier, imported source, and public thread are untouched;
- all fixtures are disposable;
- the merged changed-patch validator remains intact;
- no secret, live target, destructive action, or new external interaction is involved.

## Evidence boundary

The focused test proves the receipt block's ordinary and optimized behavior on disposable text fixtures. The dedicated workflow still owns exact patch application, source ownership, executable mode, Perl and shell syntax, focused runtime behavior, and the sent-mail record.

This unit does not run the complete 283-case source matrix or Debian autopkgtest and does not make a new external submission.

## Disposition

`HOLD` only for one exact-head run on the merged validator generation.

A green unchanged head should move this internal evidence repair to `MERGE LOCALLY`.

## Authority

Internal Linux Fieldwork work only. No new external contact is included or authorized.
