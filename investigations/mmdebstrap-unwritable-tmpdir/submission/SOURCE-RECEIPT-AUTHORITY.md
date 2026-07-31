# Debian submission source-receipt authority

## TL;DR

The hosted verification workflow for Debian bug #1135727 checked the submitted patch's exact source boundary with inline Python `assert` statements. Those statements are debugging checks and disappear under optimized Python.

This repair uses explicit `SystemExit` diagnostics and executes the exact extracted workflow receipt under both ordinary Python and `python -O`.

The already-sent patch, email record, recipients, Debian bug thread, and imported source are unchanged.

## Explain like I'm five

The workflow checks that the patch changed the intended sentences exactly once.

The old checks were written in erasable ink. They work in normal Python, but optimized Python may erase them. The new checks are ordinary program logic and cannot disappear that way.

## Why care

This workflow is part of the evidence chain for an authorized external submission. It proves that the retained patch applies to the declared pristine source and owns exactly three files with specific source, documentation, coverage, and shell-test markers.

Evidence-authority checks should fail explicitly under every supported interpreter mode. A green result must not depend on debug-only language behavior.

## Observed boundary

Owning issue: #308. Branch: `repair/mmdebstrap-1135727-explicit-source-receipt`.

Base: current `main` at `77ba71c2c7f1a86a23e58ef365c2925cdfdc032f`.

The predecessor workflow used eight inline assertions:

- four exact source-line counts;
- one documentation count;
- one coverage-registration count;
- two shell-test containment checks.

The hosted command currently invokes ordinary `python3`, so this is evidence hardening. No false green under the current ordinary hosted mode was observed.

## Candidate

The workflow receipt now defines:

- `require_exact_count(text, needle, label)` for exact-once boundaries;
- `require_contains(text, needle, label)` for preserved containment boundaries;
- focused `SystemExit` diagnostics that include the boundary label, observed count when relevant, and missing text.

The semantic contract is preserved:

- source, documentation, and coverage markers must occur exactly once;
- the two focused shell-test markers must remain present;
- the same pristine imported revision, patch bytes, file inventory, executable bit, syntax gates, focused runtime probe, and sent-mail record remain authoritative.

## Focused regression

`tests/test_mmdebstrap_1135727_submission_source_receipt.py`:

- extracts the exact heredoc from `.github/workflows/verify-mmdebstrap-1135727-submission.yml`;
- parses it with `ast` and rejects any `ast.Assert` node;
- builds a disposable complete source, coverage, and shell-test fixture;
- executes the extracted block under ordinary Python and `python -O`;
- removes and duplicates a required source line;
- removes the documentation line;
- removes and duplicates the coverage marker;
- removes each shell-test marker;
- requires both interpreter modes to fail with the same explicit diagnostic;
- uses only temporary directories and leaves no repository state.

## Local execution

An isolated copy of the exact receipt logic was executed under the local ordinary and optimized interpreters.

Observed:

- complete fixture: status 0 in both modes;
- missing source line: status 1 in both modes;
- duplicate source line: status 1 in both modes;
- missing documentation: status 1 in both modes;
- missing and duplicate coverage: status 1 in both modes;
- each missing shell marker: status 1 in both modes;
- ordinary and optimized negative diagnostics matched.

The local Python startup emitted an unrelated spreadsheet-runtime warmup warning on stderr before each child process. It did not alter the return statuses or the matching explicit receipt diagnostics. Hosted exact-head execution remains authoritative.

## Why this approach

Running the workflow only under `python -O` would prove one mode while changing the production invocation. Static text matching alone would not prove that the extracted checks actually fail.

Executing the exact heredoc in both modes keeps the production command unchanged, proves optimizer parity, and makes future edits to the workflow block part of the regression automatically.

## Complete-diff boundary

The candidate changes exactly:

- the inline source-receipt block in the dedicated workflow;
- one focused repository test;
- this tracked record.

It does not modify:

- `0001-honor-explicit-tmpdir.patch`;
- `email.txt` or attachments;
- `verify_submission_record.py`;
- the imported mmdebstrap source;
- the public Debian bug;
- any recipient, tag, acknowledgement, or external-contact authority.

## Evidence boundary

The focused test proves the receipt block's ordinary/optimized behavior on disposable text fixtures. The dedicated workflow must still prove exact patch application, source ownership, executable mode, Perl and shell syntax, focused runtime behavior, and sent-mail record on the hosted runner.

This unit does not rerun the complete 283-case source matrix or Debian autopkgtest, and it does not make a new external submission.

## Disposition

`REPAIR` until exact-head Linux Fieldwork CI and `Verify Debian bug 1135727 submission` both pass on the same reviewed head.

A green result should move this internal evidence repair to `MERGE LOCALLY`.

## Authority

Internal Linux Fieldwork work only. No new external contact is included or authorized.
