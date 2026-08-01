# Source map

## Upstream source identity

| Item | Repository path or URL | Exact revision | Notes |
| --- | --- | --- | --- |
| Primary implementation | canonical mmdebstrap `make_mirror.sh`, function `update_cache()` | upstream `main` `77ec9be5417ee44c96343d2347145585da1b1f94`; blob `6c4be092edcf23b56b63a3befe238c099c45f590` | Source contains the cleanup-only `EXIT INT TERM` trap and explicit cleanup before trap clearing. |
| Controlled staging base | `teamleaderleo/mmdebstrap`, `master` | commit `574048f2a720057b75e56622003932f344dc700a`; `make_mirror.sh` blob `6c4be092edcf23b56b63a3befe238c099c45f590` | Repository history is downstream-specific, but the changed source file is byte-identical to canonical upstream. `master` was preserved. |
| Controlled source candidate | `teamleaderleo/mmdebstrap`, branch `linux-fieldwork/unit-14-make-mirror-update-cache-source` | commit `c94132e344f97cee95901623552df6bcde5039bb`; blob `7d92a29a05ade7f5da397a1a9d03e601092f9465` | One commit ahead of controlled `master`, zero behind, one changed file. |
| Linux Fieldwork import | `upstream/mmdebstrap/make_mirror.sh` | blob `6c4be092edcf23b56b63a3befe238c099c45f590` | Byte-identical source base used by retained matrices. |
| Upstream tests | `make_mirror.sh`, `coverage.sh`, `coverage.py` | same upstream base | Full mirror generation needs network and Debian mirror state; no focused native worker test exists in the retained upstream tree. |
| Contribution instructions | upstream README and Forgejo issue/PR surfaces | inspected 2026-07-31 | Canonical repository exposes issues and pull requests. |

## Linux Fieldwork carriers

| Carrier | Exact head or merge | Role | Classification |
| --- | --- | --- | --- |
| Issue #231 | closed final receipt | owning worker defect and baseline result | canonical issue |
| PR #238 | head `f6966f0ccd6c3ea91ae39c260f23e6e416b5c601` | original stacked patch and signal matrices | superseded construction |
| PR #259 | head `d270f558fa7c32569ea380fd614c34edaf60b3b3` | first clean restack | superseded stale base |
| PR #260 | head `fbdc5f038530087430d82e2ceae0f237f6660a2f` | clean four-file current-main transfer | superseded construction |
| PR #267 | head `c52a907f0b7a02a9cbe6ecb08dc5291b46f4f30a` | once-only finalizer and cleanup-failure repair | superseded by #286 |
| PR #286 | reviewed head `2c85afa8c947ff040b4c6d876d9b88cf545dbb59`; merge `782774b01002abf37878d834a54d0bbf8b226397` | landed patch 0001 and three focused suites | canonical component |
| PR #305 | head `0a6b9cc404bcc5e463964be7cbcf74d710528d86` | stacked cleanup-time signal successor | superseded construction |
| PR #322 | merge `9245dae2b7391b0f60b90c23ebdd1aca55aeb78c` | landed-state and successor routing refresh | evidence/routing |
| PR #324 | head `0906573b434710032f44807bfb5d6bb017a510f6`; merge `404540e46b35df682f1fc006bdadf837aafb1752` | landed patch 0002 and cleanup-time signal/rerun suites | canonical component |
| Controlled source commit | `teamleaderleo/mmdebstrap@c94132e344f97cee95901623552df6bcde5039bb` | collapsed one-file source candidate | current candidate |
| Controlled carrier branch | `teamleaderleo/mmdebstrap@adc13ac6103019e38d3c5b534fba8f05e0849248` | patch, guard script, and source-branch builder | internal staging/evidence |
| Issue #263 / PR #264 | PR head `257d05eb91bc6e5a83e16a38f0c2e255c1792371` | prompt descendant cancellation comparison | HOLD, excluded |
| Issue #271 / PR #273 | merge `885225866cc4dc7a4998d3b96e0e883900666d8f` | reusable cleanup re-entry rule in controlled harnesses | supporting evidence |
| PR #302 | merge `e93b0353871dd29ebf9eda32245b2607f9572cc7` | unified-diff carrier validator | supporting tooling |
| PR #224 | merge `386f5c8dbb01e5de1af45ac0eb325ee8567722e3` | top-level proxy launch and PID ownership | adjacent unit 13; deliberately excluded |

## Candidate code

| File | Lines or symbols | Change | Owning commit or patch |
| --- | --- | --- | --- |
| `make_mirror.sh` | `update_cache()` | add cleanup-signal status slot and first-signal recorder | candidate `c94132e...`; packet patch 0001 |
| `make_mirror.sh` | `update_cache_finish()` | one finalizer, bounded cleanup, explicit precedence | candidate `c94132e...`; packet patch 0001 |
| `make_mirror.sh` | `update_cache_exit_cleanup()` | preserve implicit EXIT status | candidate `c94132e...`; packet patch 0001 |
| `make_mirror.sh` | `update_cache_signal_exit()` | record explicit signal and ignore later handled signals | candidate `c94132e...`; packet patch 0001 |
| `make_mirror.sh` | terminal success path | call `update_cache_finish 0`; remove direct cleanup/trap clearing | candidate `c94132e...`; packet patch 0001 |

## Candidate tests

| File | Test or fixture | Baseline failure | Candidate expectation |
| --- | --- | --- | --- |
| `tests/test_make_mirror_update_cache_signal_ownership.py` | worker signal ownership and precedence | false success, later work, duplicate cleanup, wrong-owner proxy kill | nonzero signal result, worker cleanup once, parent proxy ownership |
| `tests/test_make_mirror_update_cache_signal_matrix.py` | INT/QUIT/TERM matrix | cleanup-only trap resumes | 130/131/143, clean rerun |
| `tests/test_make_mirror_update_cache_cleanup_failure.py` | successful work plus cleanup 74 | EXIT re-enters cleanup | one cleanup, final 74, rerun 0 |
| `tests/test_make_mirror_update_cache_cleanup_signals.py` | signal during cleanup | default signal interrupts cleanup or replaces first result | first signal retained, cleanup completes, precedence preserved |
| `tests/test_make_mirror_update_cache_cleanup_signals_rerun.py` | cleanup-time signal, later signal, cleanup failure, rerun | partial state or replaced result | 143 retained, state removed, immediate rerun 0 |

## Patch and branch links

- Linux Fieldwork branch: `upstream/unit-14-make-mirror-update-cache`
- Controlled staging repository: `https://github.com/teamleaderleo/mmdebstrap`
- Candidate source branch: `linux-fieldwork/unit-14-make-mirror-update-cache-source`
- Candidate head: `c94132e344f97cee95901623552df6bcde5039bb`
- Compare: controlled `master` `574048f2...` to source candidate `c94132e...`; one commit, one file, 46 additions, 6 deletions
- Candidate source blob: `7d92a29a05ade7f5da397a1a9d03e601092f9465`
- Carrier branch: `linux-fieldwork/unit-14-make-mirror-update-cache`
- Retained patch: `patches/0001-update-cache-worker-lifecycle.patch`
- Patch SHA-256: `980720d262d0f5d4a568be54851e144652ae6d882a8ad0e8aa228c8ffed2ae42`
- Guarded application: `sh linux-fieldwork/apply-unit-14.sh --check` and `--apply` on the carrier branch
- Canonical delivery branch: `NEEDS FORGEJO FORK OR ACCEPTED PATCH ROUTE`

## Operation ownership map

| Operation | Owner before candidate | Owner after candidate | Evidence |
| --- | --- | --- | --- |
| `$rootdir` creation/removal | worker creates; mixed trap cleanup | worker only | PR #286 ownership suite |
| `$PROXYPID` stop/wait | top-level creates, worker trap kills | top-level only | PR #286 ownership suite; PR #224 parent suite; candidate static assertion |
| ordinary worker result | implicit shell flow; cleanup can replace/re-enter | common worker finalizer | PR #286 cleanup-failure suite |
| explicit INT/QUIT/TERM | cleanup-only handler resumes | worker finalizer exits 130/131/143 | PR #286 signal matrix |
| signal during ordinary cleanup | default action interrupts cleanup | first handled signal recorded; later handled signals ignored | PR #324 cleanup-signal suite |
| cleanup failure | can replace or trigger duplicate cleanup | returned only after success and no signal | PRs #286/#324 precedence suites |

## Overlap and current upstream state

Search date: 2026-07-31. The official repository page showed `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`, and current `make_mirror.sh` remained blob `6c4be092edcf23b56b63a3befe238c099c45f590`. Searches of the indexed official issue and pull-request surfaces for `make_mirror`, `update_cache`, proxy ownership, and cleanup signals found no matching public carrier. The official issue list contained six open issues, none in this area. Search indexing can miss unindexed or newly created work, so a direct overlap recheck remains required immediately before any authorized submission.

The controlled GitHub repository has downstream-specific history and is therefore a staging fork, not proof that its full tree is canonical upstream. The changed file identity is exact, and the source candidate is a one-file commit based on that verified blob. Final delivery still needs a canonical Forgejo-compatible route or an explicitly accepted patch submission method.

## Files deliberately not changed

- top-level proxy launch/cleanup code in `make_mirror.sh`;
- `caching_proxy.py`;
- APT command sequences inside `update_cache()`;
- `coverage.py` and `coverage.sh`;
- package metadata and dependencies;
- process-group or supervisor logic;
- Linux Fieldwork retained historical patches and tests.
