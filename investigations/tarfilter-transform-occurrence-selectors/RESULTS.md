# Results

## Initial candidate run

- Candidate code head: `8c3ba696310fe0a631c74749df08055677fd109e`
- Pull-request merge ref tested: `85dc0d2caefeddbbac2f156dd206101077e474fe`
- Linux Fieldwork CI run: `30542362599`
- Job: `90869929455` (`lab-tools`)
- Conclusion: success
- Runner: Ubuntu 24.04.4, GNU tar 1.35

Repository discovery ran 41 tests in 4.853 seconds and passed. The first three focused occurrence tests passed:

```text
test_candidate_matches_gnu_numeric_occurrence_semantics ... ok
test_predecessor_rejects_numeric_selector ... ok
test_selector_is_applied_independently_to_link_targets ... ok
```

The same run passed the adjacent LF-14 archive corpus, sparse repair, strip validation, path filtering, PAX metadata, no-option passthrough, transform scope, replacement-language, repository safety, Debian, and security regressions.

## Complete-diff parser finding

The first implementation used Python `str.isdigit()` to recognize selector characters. That accepts Unicode numeral classes beyond ASCII `0` through `9`.

GNU tar 1.35 rejects the explored non-ASCII forms:

```text
s/a/b/٢   Arabic-Indic digit two
s/a/b/²   superscript two
s/a/b/０  full-width zero
```

The candidate now recognizes only ASCII characters in `0123456789`. The regression requires both the candidate and GNU tar to reject those three expressions.

## Failed rejection-test run

- Candidate head: `2e03fcecad2aee123095ee11992e47d883af5bb3`
- Linux Fieldwork CI run: `30542931175`
- Job: `90871808778`
- Conclusion: failure in the reference-test harness

The candidate rejected all three non-ASCII expressions before the failure. GNU tar also rejected them, but its diagnostic echoed raw expression bytes under the runner locale. `subprocess.run(text=True)` attempted strict UTF-8 decoding and raised `UnicodeDecodeError` before the test could assert the nonzero return code.

The correction keeps the rejection contract and decodes GNU tar diagnostic output with `errors="replace"`. The test does not depend on localized error wording.

## Corrected code run

- Candidate code head: `b1e5df6b3fb2b77d6e54fc57f27f83a5df3c7113`
- Linux Fieldwork CI run: `30543032983`
- Job: `90872143092` (`lab-tools`)
- Conclusion: success

The full repository suite passed after the ASCII-only parser correction and defensive reference-output decoding. The focused matrix now covers:

- predecessor rejection;
- ordinary and global substitution controls;
- numeric-only and numeric-plus-global selectors;
- zero and selectors beyond available matches;
- number placement around letter flags;
- repeated decimal runs with the last run controlling the start;
- case-insensitive composition;
- independent regular-member, hard-link-target, and symlink-target counting;
- rejection of non-ASCII numeral characters by both candidate and GNU tar.

## Documentation-complete head run

- Complete branch head: `aa2b454cbcae1180188d5d096a7a627b390548f0`
- Linux Fieldwork CI run: `30543253886`
- Job: `90872890121` (`lab-tools`)
- Conclusion: success

This run validates the six-file final review surface before the final receipt-only commit: investigation, result history, exploratory observations, incremental patch, reusable note, and executable regression.

## Result boundary

The result establishes the retained incremental patch against the PR #68 predecessor and GNU tar 1.35 for the tested numeric selector matrix. It excludes `x`, `flags=` statements, semicolon-separated expressions, complete BRE translation, case-conversion escapes, and duplicate-letter-flag compatibility.

This file is the final receipt-only commit. Its exact head requires one last green Linux Fieldwork CI run so the peer-review anchor includes the recorded validation history itself.
