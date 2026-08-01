# Unit 10 — mmdebstrap package tests: exact subordinate-ID account matching

State: `ACTIVE`  
Priority-zero issue: #397, unit 10  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-10-subid-exact-match`  
External contact authorized: `false`

## TL;DR

Debian mmdebstrap package-test setup still checks `/etc/subuid` and `/etc/subgid` with an unanchored regular-expression search across whole records. A different account containing the test username can suppress the required subordinate-ID entry. The retained Linux Fieldwork correction compares colon-delimited field 1 literally and exactly for both files.

This pass reconstructed the complete carrier lineage, refreshed the public source identities, rewrote the candidate with upstream repository paths, and ran a fresh synthetic behavior/idempotency smoke. Full application against a directly checked-out current Salsa base and the relevant package/user-namespace integration gate remain.

## Accomplished behavior

The package-test setup recognizes an existing subordinate-ID assignment only when field 1 exactly equals `AUTOPKGTEST_NORMAL_USER`. Substring account names, delimiter-free malformed rows, and regex-significant usernames no longer suppress setup. Usernames beginning with `-` remain data after the grep option boundary. The subuid and subgid paths use identical logic, and an immediate rerun appends no duplicate.

## Why care

For user `debci`, a row such as `old-debci-helper:200000:65536` makes the current whole-line `grep debci` succeed. The real `debci` account then receives no range, and later namespace tests can fail far from the setup defect.

## Scope

### Included

- the two account-presence conditions in `debian/tests/testsuite`;
- exact literal field-1 matching for `/etc/subuid` and `/etc/subgid`;
- exact-present, substring, malformed, regex-significant, leading-hyphen, empty, absent, parity, and immediate-rerun controls;
- zero-fuzz patch packaging and complete shell syntax.

### Excluded

- subordinate-ID range overlap, width, bounds, allocation policy, and conflicting duplicate rows;
- mmdebstrap runtime numeric-UID support;
- the `dev-ptmx`/`bsdutils`, Deb822 source-filter, capability, signal, mirror, and broad sid harness lanes;
- any upstream issue, merge request, email, comment, or review action.

### Split boundary

Unit 10 owns only package-test account-record detection. Runtime numeric-ID support is already represented by upstream commit `6f0a2fcd7f0b21a69d6c2b7c90272a132ed58ff5`. The broader package-test harness remains under issue #53 and its focused successors.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | Debian `mmdebstrap` packaging |
| Canonical repository | `https://salsa.debian.org/debian/mmdebstrap.git` |
| Intended base branch | `master` |
| Upstream base commit | `c8a789205ded12daccfb16deaa35ddd1fc8d688f` from the current dgit master view; direct Salsa checkout still required |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | `NEEDS BRANCH` |
| Candidate head | `NEEDS BRANCH` |
| Linux Fieldwork branch | `upstream/unit-10-subid-exact-match` |
| Linux Fieldwork head | updated in `HANDOFF.md` after the packet commit sequence |
| Imported/local source identity | Debian `mmdebstrap 1.5.7-3`; `upstream/mmdebstrap/debian/tests/testsuite` blob `9f4eda87430da38b08a23a50a51e53b22cf7414b` |
| Patch or series path | `patches/0001-debian-tests-match-subid-account-field-exactly.patch` |
| Proposed destination | Debian Salsa `debian/mmdebstrap`, branch `master` |
| Delivery method | one Salsa merge request after explicit authorization |

## Canonical links

- Priority-zero unit: #397 unit 10
- Owning Linux Fieldwork issue: #80
- Canonical Linux Fieldwork product carrier: merged PR #92 / merge `3cc250da7798679bd20c1a1f34396f83c9b0ee04`
- Canonical proof carrier: merged PR #291 / merge `920a4b354386e32e7f13d004d62fba055a5f1518`
- Superseded carriers: PRs #215, #218, #225, and #252
- Adjacent central investigation: #53; related carriers PR #72 and PR #86
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- the released/current imported Debian 1.5.7-3 package-test block retains the whole-record unanchored checks;
- the correction changes exactly the two account-presence conditions;
- historical exact-head proof passed the full retained four-case test module and repository CI at PR #291 head `125d4e5097625b38850292525c7eb2f98818f5d9`;
- the refreshed upstream-path patch passed a local zero-fuzz synthetic application, `/bin/sh -n`, the full account-case matrix, subuid/subgid parity, and immediate rerun on 2026-08-01;
- active upstream runtime numeric-ID work changes a different source owner and does not consume this package-test defect.

### Not yet demonstrated

- zero-fuzz application against a direct checkout of the current Salsa `master` head;
- the exact current Salsa commit identity through a live clone/API receipt;
- an upstream-native package/autopkgtest run containing the relevant user-namespace cases;
- a controlled fork and candidate branch.

### Compatibility boundary

The append value, ordering, shell status, stdout/stderr behavior, file modes, ownership, and surrounding package-test flow remain unchanged. Only false-positive account detection changes.

## Candidate organization

One commit belongs in one merge request:

1. `debian/tests: match subid account fields exactly` — change the two conditions and retain the existing append policy.

The two lines share one invariant and one test matrix. Splitting subuid from subgid would invite semantic drift.

## Current disposition

`ACTIVE` — current-base application and an upstream-native package/user-namespace gate remain.

## Next human decision

No send decision is ready. The next technical step is a direct current-Salsa checkout, exact patch application, and focused package-test execution.

## Authority

Internal source reading, packet work, branch commits, local tests, rebases, and draft preparation are authorized by #397. External contact remains unauthorized. None occurred.
