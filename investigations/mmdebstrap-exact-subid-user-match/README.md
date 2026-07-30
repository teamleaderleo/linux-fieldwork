# mmdebstrap package-test exact subordinate-ID account matching

## In simple words

The package-test entrypoint checks whether its ordinary user already has subordinate UID/GID ranges using an unanchored regex search across each whole file. Another account containing the username can satisfy that search, so the real test user receives no range and later user-namespace tests fail for the wrong reason.

The candidate compares field 1 exactly and literally for both `/etc/subuid` and `/etc/subgid`. The existing append value and setup order remain unchanged.

## Coordination and duplicate search

- focused issue: #80
- historical candidate: PR #92
- central mmdebstrap investigation: #53
- related reusable tooling: PR #72
- current-main delivery branch: `fix/mmdebstrap-exact-subid-user-match-current-main`

Open and closed issues and pull requests were searched before creating the current-main carrier. No separate current-main PR covered this exact field-matching boundary.

## Exact source boundary

- current-main base at branch creation: `67cea0c3882250664fdf8d362c7c9d40ce4d6611`
- imported package: Debian `mmdebstrap 1.5.7-3`
- source: `upstream/mmdebstrap/debian/tests/testsuite`
- source blob: `9f4eda87430da38b08a23a50a51e53b22cf7414b`
- candidate patch: `0001-match-subid-user-field-exactly.patch`
- regression: `tests/test_mmdebstrap_subid_account_match.py`
- reusable note: `notes/security/subordinate-id-files-require-exact-account-field-matching.md`

The imported source remains unchanged; the candidate is retained as an applyable patch. The four current-main files preserve PR #92's reviewed unit and add explicit complete-source shell syntax plus a leading-hyphen option-terminator control.

## Baseline

The original checks are:

```sh
grep "$AUTOPKGTEST_NORMAL_USER" /etc/subuid
grep "$AUTOPKGTEST_NORMAL_USER" /etc/subgid
```

They search the whole record as a regular expression. For user `debci`, this unrelated record is a false positive:

```text
old-debci-helper:200000:65536
```

A username containing regex-significant punctuation can change the match semantics. A value beginning with `-` can also be interpreted as a grep option.

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

The regression applies the patch to an exact temporary source copy, checks the complete patched testsuite with `/bin/sh -n`, extracts each real patched `if` block, substitutes a temporary file path, and executes it with `/bin/sh -eu`.

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

## Evidence boundary

Static source and executable synthetic files prove the matching defect. No evidence says Debian CI run `72574145` used colliding account names; that historical failure is independently owned by the `dev-ptmx` fixture.

This candidate does not validate subordinate range overlap, numeric limits, duplicate conflicting entries or allocator policy.

## Cleanup and rerun

Tests operate only in `TemporaryDirectory` paths, apply one text patch, invoke `/bin/sh`, and remove all files through cleanup. They create no users, namespaces, mounts, packages or persistent host state.

## Disposition

**CURRENT-MAIN REVIEW CANDIDATE.** Exact-head repository CI and complete-diff review are required before local merge. PR #92 remains the historical development record.

## Authority

No Debian or external upstream issue, email, merge request, patch submission, comment or review is authorized by this investigation.
