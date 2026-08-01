# Upstream issue draft

Status: `NOT NEEDED`  
Proposed destination: Debian mmdebstrap Salsa project if maintainers require a separate issue  
External contact authorized: `false`

## Disposition

The candidate is a bounded two-line package-test correction with a direct reproducer and regression evidence. A merge request can carry the complete problem statement, source analysis, and tests. No separate public issue is currently needed.

Reopen this draft only when:

- the Debian project requires an issue before a merge request;
- a current-base checkout reveals a design decision that needs maintainer input;
- active overlap exists and coordination belongs in an issue;
- the correction cannot be demonstrated without a public environment question.

## Proposed title

`mmdebstrap package test can mistake a substring account for an existing subid entry`

## Draft

### Summary

The Debian package-test setup searches complete `/etc/subuid` and `/etc/subgid` records for `AUTOPKGTEST_NORMAL_USER` as a regular expression. Another account containing that value can satisfy the check, leaving the real test user without the range required by later user-namespace cases.

### Observed behavior

For:

```text
AUTOPKGTEST_NORMAL_USER=debci
/etc/subuid: old-debci-helper:200000:65536
```

this predicate succeeds:

```sh
grep "$AUTOPKGTEST_NORMAL_USER" /etc/subuid
```

The setup block appends no `debci` record.

### Expected behavior

The check recognizes an existing assignment only when colon-delimited field 1 exactly equals the requested account identity.

### Minimal reproduction

```sh
printf '%s\n' 'old-debci-helper:200000:65536' > subuid
AUTOPKGTEST_NORMAL_USER=debci
if grep "$AUTOPKGTEST_NORMAL_USER" subuid; then
    echo 'baseline treats unrelated account as present'
fi
```

### Source analysis

The owner is Debian packaging file `debian/tests/testsuite`, in the setup block that adds subordinate-ID records before invoking the mmdebstrap package-test coverage path.

### Evidence

A synthetic matrix covers exact account presence, substring collision, delimiter-free input, regex-significant input, a leading-hyphen identity, empty and absent files, subuid/subgid parity, and immediate rerun. The proposed predicate is:

```sh
cut -s -d: -f1 /etc/subuid | grep -Fxq -- "$AUTOPKGTEST_NORMAL_USER"
```

with the corresponding subgid form.

### Compatibility and scope

The append value and test ordering remain unchanged. This report addresses account detection only. Range overlap, numeric bounds, duplicate conflicts, allocation policy, and runtime numeric-ID support are separate topics.

### Proposed direction

Extract field 1 with `cut -s -d: -f1` and compare it as a fixed whole string with `grep -Fxq --` for both subuid and subgid.

## Submission checklist

- [ ] Current public issue and merge-request overlap rechecked.
- [ ] Affected current Salsa revision confirmed by direct checkout.
- [x] Reproduction is minimal and safe.
- [x] Draft contains no credentials or unsafe artifacts.
- [ ] Exact external destination confirmed.
- [ ] Explicit authorization recorded.
- [ ] Submitted public reference and timestamp recorded in `README.md` and `DECISIONS.md`.
