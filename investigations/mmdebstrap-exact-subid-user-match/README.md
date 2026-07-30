# mmdebstrap package-test exact subordinate-ID account matching

## In simple words

The package-test entrypoint checked whether its ordinary user already had subordinate UID/GID ranges using an unanchored regex search across each whole file. Another account containing the username could satisfy that search, so the real test user received no range and later user-namespace tests failed for the wrong reason.

Merged PR #92 compares field 1 exactly and literally for both `/etc/subuid` and `/etc/subgid`. The existing append value and setup order remain unchanged.

## Coordination

- completed issue: #80
- merged candidate: PR #92 / main commit `3cc250da7798679bd20c1a1f34396f83c9b0ee04`
- historical mmdebstrap investigation: #53
- related reusable tooling: PR #72
- review-control branch: `test/mmdebstrap-exact-subid-controls`

## Exact source boundary

- imported package: Debian `mmdebstrap 1.5.7-3`
- source: `upstream/mmdebstrap/debian/tests/testsuite`
- source blob at merge: `9f4eda87430da38b08a23a50a51e53b22cf7414b`
- candidate patch: `0001-match-subid-user-field-exactly.patch`
- regression: `tests/test_mmdebstrap_subid_account_match.py`
- reusable note: `notes/security/subordinate-id-files-require-exact-account-field-matching.md`

The imported source remains unchanged; the candidate is retained as an applyable patch.

## Baseline

The original checks were:

```sh
grep "$AUTOPKGTEST_NORMAL_USER" /etc/subuid
grep "$AUTOPKGTEST_NORMAL_USER" /etc/subgid
```

They searched the whole record as a regular expression. For user `debci`, this unrelated record was a false positive:

```text
old-debci-helper:200000:65536
```

A username containing regex-significant punctuation could change the match semantics. A value beginning with `-` could also be interpreted as a grep option.

## Candidate

The retained patch uses field-aware fixed exact matching:

```sh
cut -s -d: -f1 /etc/subuid | grep -Fxq -- "$AUTOPKGTEST_NORMAL_USER"
cut -s -d: -f1 /etc/subgid | grep -Fxq -- "$AUTOPKGTEST_NORMAL_USER"
```

Only the two conditions change. The existing records appended on absence remain:

```text
<user>:100000:65536
```

## Executable regression

The regression applies the retained patch to an exact temporary source copy, checks the complete patched testsuite with `/bin/sh -n`, extracts each real patched `if` block, substitutes a temporary file path, and executes it with `/bin/sh -eu`.

It requires:

- the baseline to retain the unanchored searches;
- exactly two source lines to change;
- exact account presence to avoid an append;
- a substring-only account to require an append;
- a delimiter-free malformed record to require an append;
- regex-significant input to be treated literally;
- a leading-hyphen exact account to remain present without grep option parsing;
- empty and absent files to receive a record;
- identical behavior for subuid and subgid;
- an immediate rerun to remain idempotent;
- exact patch application and complete testsuite shell syntax.

The leading-hyphen and complete-source syntax cases were added during post-merge review. They strengthen the documented `grep --` and source-validity claims without changing the product patch.

## Evidence boundary

Static source and executable synthetic files prove the matching defect. No evidence says Debian CI run `72574145` used colliding account names; that historical failure is independently owned by the `dev-ptmx` fixture.

This candidate does not validate subordinate range overlap, numeric limits, duplicate conflicting entries or allocator policy.

## Cleanup and rerun

Tests operate only in `TemporaryDirectory` paths, apply one text patch, invoke `/bin/sh`, and remove all files through cleanup. They create no users, namespaces, mounts, packages or persistent host state.

## Disposition

The product candidate is merged locally. The review-control follow-up carries tests and documentation only. Any upstream destination remains a separate decision.

## Authority

No Debian or external upstream issue, email, merge request, patch submission, comment or review is authorized by this investigation.
