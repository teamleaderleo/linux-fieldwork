# Unit 02 — mmdebstrap caching_proxy complete repair

State: `ACTIVE`  
Priority-zero issue: #397, unit 02  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-02-caching-proxy-complete-repair`  
External contact authorized: `false`

## TL;DR

The complete request, response, and atomic-cache repair already exists as the merged internal composition from PR #198. This unit is converting that proof carrier into a current-upstream candidate.

The former first gate is now complete. The internal staging repository `teamleaderleo/mmdebstrap` contains `linux-fieldwork/upstream-main-snapshot` at canonical commit `77ec9be5417ee44c96343d2347145585da1b1f94`, and its `caching_proxy.py` blob is exactly `e57a8516a0c76167894b05fc56be0e3165535488`, matching the Linux Fieldwork imported source byte for byte.

A controller branch and a clean source branch now exist in the GitHub staging repository. An internal workflow was added to export the committed composer, compile under ordinary and optimized Python, run the retained seven-test matrix, and publish only `caching_proxy.py` to the clean source branch. During this session the clean source branch did not advance, so no new candidate or test pass is claimed. No upstream contact has been made.

## Accomplished behavior

The proposed candidate validates the request target, authority, method, and bodyless framing before cache or origin activity; confines accepted cache paths; removes proxy credentials and hop-by-hop request fields; validates origin status and response framing before downstream commitment; writes through an exclusive hidden temporary file; publishes complete cache entries atomically; and closes after late failures without appending a second response.

## Why care

The baseline can turn request text into paths outside the intended cache root, forward proxy-only credentials to the selected origin, accept and cache an origin error under optimized Python, expose a partial final cache file, and append a second status after a downstream `200` has begun. A cache repeats these failures for later clients.

## Scope

Included:

- exact current-upstream source identity;
- one complete source candidate preserving the proven composition ordering;
- request-target, cache-path, request-header, origin-status, response-framing, declared-length, transfer-coding, publication, late-error, retry, concurrency, optimized-Python, and cleanup coverage;
- upstream issue and pull-request drafts;
- reproducible exporter and internal staging branches.

Excluded:

- same-UID parent-directory replacement races, owned by issue #227;
- miss coalescing;
- crash-durable file and directory synchronization;
- checksums or content authentication;
- remote deployment policy;
- broader URI syntax;
- any public issue, pull request, comment, email, review, or patch submission.

## Exact identities

| Identity | Value |
| --- | --- |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Canonical branch | `main` |
| Canonical base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Canonical snapshot branch | `teamleaderleo/mmdebstrap:linux-fieldwork/upstream-main-snapshot` |
| Verified source blob | `e57a8516a0c76167894b05fc56be0e3165535488` |
| GitHub staging repository | `teamleaderleo/mmdebstrap` |
| Staging default branch | `master` at `574048f2a720057b75e56622003932f344dc700a`; not used as canonical base |
| Controller branch | `linux-fieldwork/unit-02-caching-proxy-complete-repair` |
| Controller head | `60ea1c862787473ca362278bb2efb6f5e971b124` |
| Clean candidate branch | `linux-fieldwork/unit-02-caching-proxy-complete-repair-source` |
| Clean candidate head | `77ec9be5417ee44c96343d2347145585da1b1f94` — candidate not yet published |
| Linux Fieldwork branch | `upstream/unit-02-caching-proxy-complete-repair` |
| Internal composition | PR #198 head `5e69cd25e62d0e86364459d97c9df8568ff84187`; merge `8d9f7fa92f0cb2f553ca3578b78d7e04f4e4167f` |
| Composer blob | `00e28cc925ced0c01d9c8e300e7c94515367ca19` |
| Atomic input patch blob | `4fe75d312ebb097f1b9d5fa27f9f6e8da61235c1` |
| Proposed canonical delivery | Forgejo pull request after explicit authorization |

## Evidence

- The exact canonical snapshot commit is present in the GitHub staging repository.
- `caching_proxy.py` on that branch has blob `e57a8516…`, exactly matching the imported baseline.
- The complete internal candidate passed the seven-test matrix twice locally: `16.425s` and `15.297s`.
- Exact-head Linux Fieldwork CI passed at PR #198 head, run `30580697438` / 612.
- Peer staging review found useful controller/source separation and focused-test patterns in units 05, 07, 09, 10, 13, 14, 15, and 19.
- Full peer-branch observations are retained in [`artifacts/github-staging-scan-2026-08-01.md`](artifacts/github-staging-scan-2026-08-01.md).

## Pending demonstration

- successful execution of the unit-02 staging workflow or an equivalent full-checkout exporter run;
- clean candidate publication to the source branch;
- generated candidate and patch digests;
- clean patch application to exact canonical base;
- upstream-native test placement;
- ordinary/optimized focused rerun on the exact published candidate;
- cleanup and immediate rerun;
- final complete-diff and overlap review.

## Candidate organization

One source pull request remains preferred because the mechanisms share `ProxyRequestHandler.do_GET()` and their ordering carries correctness. Splitting the source changes would recreate the green-pieces/red-stack failure demonstrated by issue #145.

1. `caching_proxy.py`: complete request-to-publication repair.
2. Upstream-native regression coverage for request rejection, origin/header boundaries, framing, publication, retry, late failures, concurrency, optimized Python, and cleanup.

## Current disposition

`ACTIVE` — exact source verification is complete. Candidate export/publication and exact-candidate tests are the first incomplete gate.

## Authority

Internal repository reads, branches, commits, tests, reviews, packet drafting, and issue checkpoints are authorized. External contact remains unauthorized. No upstream contact was made.
