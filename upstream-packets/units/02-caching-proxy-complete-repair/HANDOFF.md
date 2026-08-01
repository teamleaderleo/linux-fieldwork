# Handoff — unit 02 caching_proxy complete repair

## State

`ACTIVE`

The internal composition is complete and green. The upstream packet, current-upstream review, source map, decisions, test receipts, drafts, and reproducible exporter now exist. The first incomplete step is exact raw-source identity verification in a full checkout.

## Exact stopping point

- Linux Fieldwork repository: `teamleaderleo/linux-fieldwork`
- Branch: `upstream/unit-02-caching-proxy-complete-repair`
- Last material packet head before this handoff-only commit: `c9cc0e24d06c68d3a1bbfc426c28330db890b03b`
- Final branch tip containing this handoff: recorded in the unit checkpoint on issue #397 and in the worker’s final response
- Packet: `upstream-packets/units/02-caching-proxy-complete-repair/`
- State: `ACTIVE`
- External contact: unauthorized; none made

## Exact upstream identity

- Project: mmdebstrap
- Canonical repository: `https://gitlab.mister-muffin.de/josch/mmdebstrap`
- Intended branch: `main`
- Current head observed: `77ec9be5417ee44c96343d2347145585da1b1f94`
- Target file: `caching_proxy.py`
- Upstream repository view: target file last attributed to the 2023-06-14 comment-only change
- Debian 1.5.7 cross-check: target file displayed as 4,439 bytes
- Linux Fieldwork imported file: `upstream/mmdebstrap/caching_proxy.py`
- Imported Git blob: `e57a8516a0c76167894b05fc56be0e3165535488`
- Exact byte equality at the upstream head: `PENDING`

## Exact internal candidate identity

- Owning issue: #188
- Canonical composition: merged PR #198
- Final composition head: `5e69cd25e62d0e86364459d97c9df8568ff84187`
- Merge commit: `8d9f7fa92f0cb2f553ca3578b78d7e04f4e4167f`
- Complete composer: `investigations/caching-proxy-complete-stack/compose_impl.py`
- Composer blob: `00e28cc925ced0c01d9c8e300e7c94515367ca19`
- Imported baseline blob: `e57a8516a0c76167894b05fc56be0e3165535488`
- Atomic input patch blob: `4fe75d312ebb097f1b9d5fa27f9f6e8da61235c1`
- Final exact-head CI: `30580697438` / run 612, success
- Predecessor exact-head CI: `30578916643` / run 572, success
- Local complete matrix: seven tests, passed twice (`16.425s`, `15.297s`)

## Completed in this session

1. Read issue #397, the durable packet protocol, the packet index, issue #188, PR #198, the focused carrier issues and pull requests, and the separate issue #227 boundary.
2. Confirmed no existing canonical unit branch or workspace.
3. Posted the internal claim on issue #397.
4. Created `upstream/unit-02-caching-proxy-complete-repair` from current Linux Fieldwork `main`.
5. Created the required unit workspace:
   - `README.md`
   - `SOURCE_MAP.md`
   - `DEEP_DIVE.md`
   - `TESTS.md`
   - `DECISIONS.md`
   - `UPSTREAM_ISSUE.md`
   - `UPSTREAM_PR.md`
   - `HANDOFF.md`
6. Recorded the exact internal source, carrier, CI, cleanup, compatibility, and exclusion evidence.
7. Identified the canonical upstream repository and exact displayed `main` head.
8. Performed a current issue-index overlap scan; no visible title described this complete repair.
9. Added `scripts/export_candidate.sh`, which invokes the merged semantic composer, compiles the candidate, emits `patches/0001-caching-proxy-complete-repair.patch`, and records source/patch digests and line counts.
10. Drafted an issue-first fallback and a preferred pull-request description.
11. Made no upstream contact.

## First incomplete step

Verify the exact current upstream source in a full checkout:

```sh
git clone https://gitlab.mister-muffin.de/josch/mmdebstrap.git
git -C mmdebstrap checkout --detach 77ec9be5417ee44c96343d2347145585da1b1f94
git -C mmdebstrap hash-object caching_proxy.py
```

Expected result for direct clean extraction:

```text
e57a8516a0c76167894b05fc56be0e3165535488
```

If the hash differs, stop and compare the complete file before running the exporter. Update `README.md`, `SOURCE_MAP.md`, `DEEP_DIVE.md`, `TESTS.md`, and this handoff with the new base/blob and overlap result.

## Next safe technical action

In a full Linux Fieldwork checkout at this branch:

```sh
./upstream-packets/units/02-caching-proxy-complete-repair/scripts/export_candidate.sh
cat upstream-packets/units/02-caching-proxy-complete-repair/artifacts/export-receipt.txt
python3 -m unittest -v tests/test_caching_proxy_complete_stack.py
```

Then:

1. review and commit `patches/0001-caching-proxy-complete-repair.patch` plus `artifacts/export-receipt.txt`;
2. apply the patch with `git apply --check` to exact upstream head `77ec9be…`;
3. adapt the seven-case matrix into upstream-native test placement;
4. run ordinary and optimized Python focused tests;
5. run cleanup and exact-head rerun;
6. perform a complete upstream diff review;
7. repeat issue/PR overlap search immediately before authorization;
8. update the drafts with exact accomplished receipts;
9. move to `READY FOR AUTHORIZATION` only when every gate is complete.

## Candidate review order

1. method/body framing;
2. target/Host authority;
3. raw cache-key policy and descendant checks;
4. origin request-header sanitization;
5. origin status and response framing validation;
6. downstream header normalization and response commitment;
7. exclusive hidden temporary creation and atomic replacement;
8. pre-commit 502 versus post-commit log-and-close;
9. loopback bind and lifecycle cleanup.

## Required gates still unexecuted

- exact upstream raw-source blob equality;
- packet exporter run;
- generated candidate and patch digests;
- clean patch application to current upstream;
- upstream-native focused tests;
- ordinary/optimized parity on the upstream candidate;
- current-upstream complete-diff review;
- exact-candidate cleanup and rerun;
- controlled fork and candidate branch;
- send-date overlap refresh;
- explicit external authorization.

## Known boundaries

- same-UID parent-swap races remain issue #227;
- misses remain uncoalesced;
- publication is pathname-atomic, without crash-durable fsync guarantees;
- checksums/authentication remain outside scope;
- remote deployment policy remains outside scope;
- accepted URI syntax stays intentionally narrow.

## Recovery rule

Use this packet and the issue #397 unit checkpoint as the source of truth. Do not infer state from chat history.

## Authority

Internal repository work remains authorized. External contact remains unauthorized. No public issue, fork, branch, pull request, merge request, comment, review, email, patch post, or package upload was made.