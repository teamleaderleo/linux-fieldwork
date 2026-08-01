# Upstream merge request draft

Status: `DRAFT`  
Proposed destination: `debian/mmdebstrap` on Salsa  
Proposed base branch: `master`  
Candidate branch or patch series: `NEEDS BRANCH`; packet patch at `patches/0001-debian-tests-match-subid-account-field-exactly.patch`  
External contact authorized: `false`

## Proposed title

`debian/tests: match subordinate-ID account fields exactly`

## Draft

### Summary

This change makes the package-test setup recognize subordinate UID and GID assignments by exact account field. It extracts colon-delimited field 1 from `/etc/subuid` and `/etc/subgid`, then compares the ordinary autopkgtest user as a fixed whole string.

The previous whole-record regular-expression search could treat an unrelated account such as `old-debci-helper` as the requested `debci` account. The setup would then skip the range required by later user-namespace cases.

### Before

With:

```text
AUTOPKGTEST_NORMAL_USER=debci
old-debci-helper:200000:65536
```

`grep "$AUTOPKGTEST_NORMAL_USER" /etc/subuid` returns success and the setup appends no `debci` record.

Regex-significant characters in the username also affect the search semantics.

### After

The setup counts a record only when field 1 equals the requested account literally and completely. Substring accounts and malformed delimiter-free rows do not suppress setup. Leading-hyphen identities remain data after the grep option terminator.

Missing entries still receive the existing value:

```text
<user>:100000:65536
```

An immediate rerun leaves the files unchanged.

### Implementation

Both conditions use:

```sh
cut -s -d: -f1 FILE | grep -Fxq -- "$AUTOPKGTEST_NORMAL_USER"
```

The two adjacent lines form one correction. The append values, shell flow, user setup, mirror setup, and package-test invocation remain unchanged.

### Tests

Executed on the candidate logic in a temporary Debian 13 environment:

- zero-fuzz patch application to a reconstructed exact hunk;
- `/bin/sh -n` on the reconstructed patched shell;
- exact account present;
- substring account collision;
- delimiter-free malformed input;
- regex-significant username;
- leading-hyphen username;
- empty and absent file;
- subuid/subgid parity;
- immediate rerun idempotency;
- equal source line counts and exactly two replacements.

Historical exact-source proof also applied the correction with zero fuzz to Debian mmdebstrap 1.5.7-3 package-test source and parsed the complete patched testsuite.

Pending before submission:

- direct current-Salsa `master` checkout and `git apply --check`;
- focused Debian package/user-namespace test;
- applicable shell formatting/lint gates;
- public overlap recheck.

### Compatibility

Exact valid account rows keep their current behavior. The intentional changes are limited to rows that previously matched through substring, regular-expression interpretation, or delimiter-free malformed content. The package-test’s range value and setup sequence stay the same.

Numeric UID/GID support in mmdebstrap runtime is separate from this Debian package-test account-name predicate.

### Related issue

A separate issue is unnecessary unless the project requests one.

## Proposed commits or patch order

1. `debian/tests: match subid account fields exactly`

## Reviewer notes

- `cut -s` is deliberate: without it, a delimiter-free line equal to the username is emitted as field 1 and recreates the false positive.
- `grep -F` disables regular-expression interpretation.
- `grep -x` compares the complete extracted field.
- `grep --` protects a leading-hyphen identity.
- subuid and subgid remain intentionally symmetrical.

## Submission checklist

- [ ] Candidate rebased onto the current intended Salsa base.
- [ ] Complete current-base diff reviewed.
- [x] Baseline synthetic regression loses and candidate passes.
- [ ] Upstream-native focused tests pass.
- [x] Cleanup and immediate rerun pass in the synthetic matrix.
- [ ] Active equivalent work rechecked immediately before submission.
- [ ] Fork and candidate branch exist.
- [x] Draft omits Linux Fieldwork routing from the proposed public body.
- [ ] Placeholder patch author replaced with the authorized contributor identity.
- [ ] Explicit authorization recorded.
- [ ] Public merge request and exact submitted head recorded after submission.
