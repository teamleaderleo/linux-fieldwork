# mmdebstrap package-test exact subordinate-ID account matching

## In simple words

The package-test entrypoint checks whether its ordinary user already has subordinate UID/GID ranges using an unanchored regex search across each whole file. Another account containing the username can satisfy that search, so the real test user receives no range and later user-namespace tests fail for the wrong reason.

The candidate compares field 1 exactly and literally for both `/etc/subuid` and `/etc/subgid`. The existing append value and setup order remain unchanged.

## Coordination and duplicate search

- Focused issue: #80
- Central mmdebstrap investigation: #53
- Related reusable tooling: PR #72

Open and closed repository issues and pull requests were searched. No existing candidate covered this exact field-matching boundary.

## Exact source boundary

- Imported package: Debian `mmdebstrap 1.5.7-3`
- Source: `upstream/mmdebstrap/debian/tests/testsuite`
- Candidate patch: `0001-match-subid-user-field-exactly.patch`
- Regression: `tests/test_mmdebstrap_subid_account_match.py`
- Reusable note: `notes/security/subordinate-id-files-require-exact-account-field-matching.md`

The imported source remains unchanged; the candidate is retained as an applyable patch.

## Baseline

The original checks are:

```sh
grep "$AUTOPKGTEST_NORMAL_USER" /etc/subuid
grep "$AUTOPKGTEST_NORMAL_USER" /etc/subgid
```

They search the whole record as a regular expression.

For user `debci`, this unrelated record is a false positive:

```text
old-debci-helper:200000:65536
```

A username containing regex-significant punctuation can also change the match semantics.

## Candidate

Use field-aware fixed exact matching:

```sh
cut -s -d: -f1 /etc/subuid | grep -Fxq -- "$AUTOPKGTEST_NORMAL_USER"
cut -s -d: -f1 /etc/subgid | grep -Fxq -- "$AUTOPKGTEST_NORMAL_USER"
```

Only the two conditions change. The existing records appended on absence remain:

```text
<user>:100000:65536
```

## Executable regression

The regression applies the patch to an exact temporary source copy, extracts each real patched `if` block, substitutes a temporary file path, and executes it with `/bin/sh -eu`.

It requires:

- the baseline to contain the unanchored searches;
- exactly two source lines to change;
- exact account presence to avoid an append;
- a substring-only account to require an append;
- a delimiter-free malformed record to require an append;
- regex-significant input to be treated literally;
- empty and absent files to receive a record;
- identical behavior for subuid and subgid;
- an immediate rerun to remain idempotent.

The substring collision and delimiter-free record are negative controls. The
`cut -s` option suppresses lines without the required field delimiter instead
of accepting them as account names.

## Evidence boundary

Static source and executable synthetic files prove the matching defect. No evidence shows that Debian CI run `72574145` used colliding account names; that historical failure is independently owned by the `dev-ptmx` fixture in PR #86.

This candidate does not validate subordinate range overlap, numeric limits, duplicate conflicting entries or allocator policy.

## Cleanup and rerun

Tests operate only in `TemporaryDirectory` paths, apply one text patch, invoke `/bin/sh`, and remove all files through cleanup. They create no users, namespaces, mounts, packages or persistent host state.

## Self-review

- source and both matching blocks were read;
- fixed-string, whole-field and option-terminator semantics are asserted;
- absent, empty, exact, substring, delimiter-free and literal-metacharacter cases are covered;
- subuid and subgid remain symmetrical;
- append behavior and setup ordering are unchanged;
- rerun idempotency is proved;
- imported source and external trackers are untouched.

## Disposition

**Fix candidate.** Retain for exact-head CI and peer review as a separate package-test robustness correction.

## Authority

No Debian or external upstream issue, email, merge request, patch submission, comment or review is authorized by this investigation.
