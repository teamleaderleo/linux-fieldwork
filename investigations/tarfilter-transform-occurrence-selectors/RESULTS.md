# Results

## First exact-head run

- Candidate code head: `8c3ba696310fe0a631c74749df08055677fd109e`
- Pull-request merge ref tested: `85dc0d2caefeddbbac2f156dd206101077e474fe`
- Linux Fieldwork CI run: `30542362599`
- Job: `90869929455` (`lab-tools`)
- Conclusion: success
- Runner: Ubuntu 24.04.4, GNU tar 1.35

## Executed evidence

Repository discovery ran 41 tests in 4.853 seconds and passed.

The new focused tests passed:

```text
test_candidate_matches_gnu_numeric_occurrence_semantics ... ok
test_predecessor_rejects_numeric_selector ... ok
test_selector_is_applied_independently_to_link_targets ... ok
```

The same run also passed the adjacent LF-14 archive corpus, sparse repair, strip validation, path filtering, PAX metadata, no-option passthrough, transform scope, and replacement-language tests, plus the repository safety and Debian/security regressions.

## Result boundary

The run establishes the retained incremental patch against the PR #68 predecessor and GNU tar 1.35 for the tested numeric selector matrix. It does not extend the claim to `x`, `flags=`, semicolon-separated statements, complete BRE translation, case-conversion escapes, or duplicate-letter-flag compatibility.

## Follow-up

Documentation-only validation-record commits follow this code head. A final exact-head CI receipt is required before merge so the review points at the complete branch state.
