# Unit 01 — mmdebstrap tarfilter regex dialects

State: `ACTIVE`  
Priority-zero issue: #397, unit 01  
Worker or variant: `ChatGPT`  
Linux Fieldwork branch: `upstream/unit-01-tarfilter-regex-dialects`  
External contact authorized: `false`

## TL;DR

The regex dialect candidate is now regenerated on the clean unit-15 transform prerequisite and executes against the exact `tarfilter` bytes in the user's mmdebstrap 1.5.7-3 fork. The two-patch series applies with GNU patch 2.8 using zero fuzz and zero offsets, produces candidate blob `ca8e656c036172230c796a8a12cb17f262108c39`, compiles, and passes the complete direct GNU tar 1.35 matrix.

The historical regex patch cannot be shipped on the regenerated prerequisite: two hunks apply with offsets and the final parser hunk fails. The packet therefore retains a regenerated regex patch and the exact failure evidence. Upstream-native `coverage.py` execution and final composition with selected parallel tarfilter units remain.

## Accomplished behavior

Default transforms follow the characterized GNU basic-regex spelling. `x` selects the characterized extended spelling. The candidate preserves groups, backreferences, contextual anchors, numeric occurrences, and member/hard-link/symlink target scopes. It normalizes the executed repeated-quantifier cases and rejects Python-only groups, malformed active intervals, unresolved alphabetic escapes, and unsupported POSIX bracket constructs before archive output.

The active-`(?` guard also preserves the accepted neighbors proved by PR #220:

```text
s/\(?/X/x
s/[(?]/X/x
s/\(/X/x
```

## Why care

The source compiles transform patterns directly with Python `re`. For member `aaa`, default expression `s/a+/b/` produces `b` through Python while GNU tar basic mode leaves `aaa` unchanged. A successful command can therefore emit different archive member and link identities.

## Scope

### Included

- default basic versus explicit extended transform dialects;
- operator, group, backreference, anchor, interval, and repeated-quantifier subset in the executed matrix;
- Python-only group rejection and its accepted neighbors;
- malformed interval and unmatched extended-close parity;
- composition with unit-15 target scopes, PAX rewrite state, and numeric occurrences;
- direct GNU tar 1.35 comparison under `LC_ALL=C`.

### Excluded

- POSIX classes, collating elements, equivalence classes, locale-sensitive matching, and GNU alphabetic escapes;
- expression lists and persistent `flags=` state;
- replacement case conversion;
- complete diagnostics and regex resource policy;
- type-hardlink, no-option, PAX-idshift, dotfile, parent-retention, and regular-type work owned by units 16 and 18–22.

## Exact identities

| Identity | Value |
| --- | --- |
| User-controlled source repository | `teamleaderleo/mmdebstrap` |
| User fork branch/head | `master` at `574048f2a720057b75e56622003932f344dc700a` |
| User fork `tarfilter` blob | `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Public upstream source observed by unit 15 | `https://gitlab.mister-muffin.de/josch/mmdebstrap`, `main` at `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Canonical contribution destination | `https://salsa.debian.org/debian/mmdebstrap` |
| Canonical Salsa exact head | `UNRESOLVED` |
| Clean prerequisite patch | `patches/0001-transform-metadata-prerequisite.patch`, blob `38510533dc015182f3e87e9d2f3777eea5b8c93b` |
| Prerequisite result blob | `adb330efcc941bf5e646f195c245a3184e42f8e2` |
| Regenerated regex patch | `patches/0002-tarfilter-regex-dialects.patch`, blob `7e7d37a77b0215af033b0c97770c83cce130911a` |
| Candidate `tarfilter` blob | `ca8e656c036172230c796a8a12cb17f262108c39` |
| Candidate SHA-256 | `47e73119f2418fb1e7c47f3eb8f6e82e86a5903ff5c73c68fa5c5ac047ff6308` |
| Full matrix receipt SHA-256 | `573cf47dcb947f62910fd3cdd77fe8103a0499b99b2d5d63dc0f081fb60ea8c0` |
| Linux Fieldwork branch | `upstream/unit-01-tarfilter-regex-dialects` |
| Candidate source branch | `NEEDS BRANCH` |
| Delivery method | authorized later: Salsa fork and merge request |

## Canonical links

- issue #397 unit 01
- owning issue #212
- implementation/repair carriers: PRs #151, #216, and #220
- characterization: PR #113
- clean prerequisite: unit 15, derived from PRs #68 and #102
- carrier audit: [`CARRIER_AUDIT.md`](CARRIER_AUDIT.md)
- source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- tests: [`TESTS.md`](TESTS.md)
- exact application: [`artifacts/APPLICATION.txt`](artifacts/APPLICATION.txt)
- complete matrix: [`artifacts/FULL_MATRIX.txt`](artifacts/FULL_MATRIX.txt)
- parallel units: [`artifacts/PARALLEL_UNITS.md`](artifacts/PARALLEL_UNITS.md)
- current handoff: [`HANDOFF.md`](HANDOFF.md)

## Current result

### Demonstrated

- exact 1.5.7-3 fork head and base source blob;
- clean unit-15 prerequisite application with zero fuzz and offsets;
- historical regex carrier incompatibility classified by exact hunk results;
- regenerated regex patch application with zero fuzz and offsets;
- exact prerequisite and candidate blobs;
- Python compilation;
- baseline and prerequisite negative controls;
- 41 successful candidate/GNU comparisons;
- two numeric-occurrence/link-scope comparisons;
- 11 shared rejection comparisons;
- three explicit POSIX-boundary comparisons;
- representative fresh-application gate passed twice with identical digest;
- all issue #397 unit branches exist; adjacent tarfilter unit roles are recorded.

### Remaining

- port or select upstream-native transform tests and run them through current `coverage.py`;
- run the appropriate broader native gate;
- compose the selected independent tarfilter units and review the combined diff;
- create a candidate branch in the controlled fork when desired;
- resolve the exact canonical Salsa head and recheck live Salsa overlap;
- obtain explicit authorization before any external write.

## Candidate organization

1. `0001-transform-metadata-prerequisite.patch` — unit-15 replacement, target-scope, PAX, and numeric-occurrence prerequisite.
2. `0002-tarfilter-regex-dialects.patch` — one regenerated regex translator plus all grammar repairs.
3. PR #220 accepted-neighbor controls are included in `scripts/run_matrix.py`.

## Current disposition

`ACTIVE` — source application and the direct GNU matrix are green. Upstream-native execution and final cross-unit composition remain.

## Next human decision

No send decision yet. The next technical decision is whether to port this matrix into the upstream native test layout now or first compose the other selected tarfilter units on the controlled fork.

## Authority

Internal reads, branches, commits, tests, patch regeneration, and packet updates are authorized. No Salsa issue, merge request, comment, review, email, mailing-list post, or other upstream contact occurred.
