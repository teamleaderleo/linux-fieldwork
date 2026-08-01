# Source map

## Upstream source identity

| Item | Repository path or URL | Exact revision | Notes |
| --- | --- | --- | --- |
| Canonical implementation | Forgejo `josch/mmdebstrap`, `make_mirror.sh`, `update_cache()` | `main` `77ec9be5417ee44c96343d2347145585da1b1f94`; blob `6c4be092edcf23b56b63a3befe238c099c45f590` | Reconfirmed by hosted clone on 2026-08-01. |
| Controlled canonical snapshot | `teamleaderleo/mmdebstrap`, branch `linux-fieldwork/upstream-main-snapshot` | `77ec9be5417ee44c96343d2347145585da1b1f94` | Preserves canonical Forgejo history without rewriting the user's downstream `master`. |
| Final candidate | `teamleaderleo/mmdebstrap`, branch `linux-fieldwork/unit-14-make-mirror-update-cache-upstream-main` | head `76728bbb8e084b54261713ba80762cd6f6ada79a`; source blob `7d92a29a05ade7f5da397a1a9d03e601092f9465` | Two commits ahead, zero behind canonical snapshot. |
| Staging repository default branch | `teamleaderleo/mmdebstrap`, `master` | `574048f2a720057b75e56622003932f344dc700a` | Downstream-specific history; deliberately preserved and no longer the candidate base. |
| Linux Fieldwork import | `upstream/mmdebstrap/make_mirror.sh` | blob `6c4be092edcf23b56b63a3befe238c099c45f590` | Exact source used by retained component matrices. |
| Upstream test registration | `coverage.txt` and `tests/make-mirror-update-cache-worker-lifecycle` | candidate head `76728bbb...` | Focused unprivileged native regression. |

## Linux Fieldwork carriers

| Carrier | Exact head or merge | Role | Classification |
| --- | --- | --- | --- |
| Issue #231 | closed final receipt | owning defect and baseline | canonical issue |
| PR #238 | `f6966f0ccd6c3ea91ae39c260f23e6e416b5c601` | original stacked patch/matrices | superseded construction |
| PR #259 | `d270f558fa7c32569ea380fd614c34edaf60b3b3` | first clean restack | superseded stale base |
| PR #260 | `fbdc5f038530087430d82e2ceae0f237f6660a2f` | clean transfer | superseded construction |
| PR #267 | `c52a907f0b7a02a9cbe6ecb08dc5291b46f4f30a` | once-only finalizer repair | superseded by #286 |
| PR #286 | reviewed `2c85afa8c947ff040b4c6d876d9b88cf545dbb59`; merge `782774b01002abf37878d834a54d0bbf8b226397` | ownership, terminating results, cleanup precedence | canonical component |
| PR #305 | `0a6b9cc404bcc5e463964be7cbcf74d710528d86` | cleanup-time signal construction | superseded construction |
| PR #322 | merge `9245dae2b7391b0f60b90c23ebdd1aca55aeb78c` | landed-state routing | evidence/routing |
| PR #324 | reviewed `0906573b434710032f44807bfb5d6bb017a510f6`; merge `404540e46b35df682f1fc006bdadf837aafb1752` | cleanup-time first-signal retention | canonical component |
| PR #224 | merge `386f5c8dbb01e5de1af45ac0eb325ee8567722e3` | top-level proxy owner lifecycle | adjacent unit 13, excluded |
| Issue #263 / PR #264 | head `257d05eb91bc6e5a83e16a38f0c2e255c1792371` | prompt descendant cancellation | HOLD, excluded |
| PR #273 | merge `885225866cc4dc7a4998d3b96e0e883900666d8f` | cleanup re-entry rule | supporting evidence |
| PR #302 | merge `e93b0353871dd29ebf9eda32245b2607f9572cc7` | patch carrier validator | supporting tooling |

## Controlled candidate and evidence carriers

| Carrier | Exact identity | Role |
| --- | --- | --- |
| Patch/automation branch | `teamleaderleo/mmdebstrap` `linux-fieldwork/unit-14-make-mirror-update-cache` | Internal patch, guarded application, canonical clone, test adapters, and receipts. |
| Canonical sync receipt | `linux-fieldwork/unit-14-canonical-sync-receipt.md` | Forgejo clone, exact head/blob, zero-fuzz application, static gates, ten dynamic cases. |
| Exact-candidate receipt | `linux-fieldwork/unit-14-candidate-matrix-receipt.md` | First collapsed candidate identity gate. |
| Native test receipt | `linux-fieldwork/unit-14-native-test-receipt.md` | `sh -n`, shellcheck, upstream shfmt options, direct native execution, diff hygiene. |
| Overlap receipt | `linux-fieldwork/unit-14-overlap-scan-receipt.md` | Live read-only canonical issue/PR scan; see receipt result. |

## Candidate commits

1. `b2a9a09b36fd13f22a024ebf8522ac58543eac28` — `make_mirror: make update_cache cleanup worker-owned`
2. `76728bbb8e084b54261713ba80762cd6f6ada79a` — `tests: cover make_mirror update_cache worker lifecycle`

## Candidate code

| File | Symbol or area | Change | Owning commit |
| --- | --- | --- | --- |
| `make_mirror.sh` | `update_cache()` | worker-local cleanup-signal status and first-signal recorder | `b2a9a09b...` |
| `make_mirror.sh` | `update_cache_finish()` | one finalizer; bounded cleanup; explicit precedence | `b2a9a09b...` |
| `make_mirror.sh` | EXIT/INT/QUIT/TERM wrappers | preserve implicit status; explicit 130/131/143; ignore later handled signals | `b2a9a09b...` |
| `make_mirror.sh` | successful completion | route through `update_cache_finish 0`; remove direct cleanup/trap clearing | `b2a9a09b...` |
| `tests/make-mirror-update-cache-worker-lifecycle` | native regression | extract actual candidate functions and exercise signal/cleanup/rerun cases | `76728bbb...` |
| `coverage.txt` | test registry | register native lifecycle regression | `76728bbb...` |

## Complete candidate diff

Compare canonical snapshot `77ec9be...` to candidate `76728bbb...`:

- two commits ahead, zero behind;
- `make_mirror.sh`: 46 additions, 6 deletions;
- `coverage.txt`: 2 additions;
- `tests/make-mirror-update-cache-worker-lifecycle`: 261 additions;
- no other path changed.

## Candidate tests

| Test | Baseline/predecessor failure | Candidate expectation |
| --- | --- | --- |
| Retained ownership module | false success, later work, duplicate cleanup, wrong-owner proxy kill | 143, one worker cleanup, parent proxy ownership, clean rerun |
| Retained signal matrix | cleanup-only trap resumes | INT/QUIT/TERM 130/131/143 and reruns |
| Retained cleanup-failure module | EXIT cleanup re-entry | one cleanup; success+cleanup failure returns 74 |
| Retained cleanup-time matrix | default signal interrupts cleanup or later signal replaces first | first signal retained; cleanup completes; precedence preserved |
| Retained rerun matrix | partial state or changed result | state removed; immediate rerun 0 |
| Native upstream regression | final source extraction and real signal barriers | static owner fence, signal/cleanup precedence, complete cleanup, rerun |

## Patch and branch links

- Linux Fieldwork packet branch: `upstream/unit-14-make-mirror-update-cache`
- Controlled repository: `https://github.com/teamleaderleo/mmdebstrap`
- Canonical snapshot branch: `linux-fieldwork/upstream-main-snapshot`
- Candidate branch: `linux-fieldwork/unit-14-make-mirror-update-cache-upstream-main`
- Candidate head: `76728bbb8e084b54261713ba80762cd6f6ada79a`
- Retained source patch: `patches/0001-update-cache-worker-lifecycle.patch`
- Patch SHA-256: `980720d262d0f5d4a568be54851e144652ae6d882a8ad0e8aa228c8ffed2ae42`
- Final canonical delivery branch: created only after explicit authorization on an accepted Forgejo/patch route.

## Operation ownership map

| Operation | Baseline owner/result | Candidate owner/result | Evidence |
| --- | --- | --- | --- |
| `$rootdir` removal | mixed cleanup trap | worker only | retained and native tests |
| `$PROXYPID` stop/wait | top-level creates; worker trap kills | top-level only | ownership suite and native source assertion |
| ordinary result | cleanup can replace or re-enter | common finalizer preserves primary status | cleanup-failure matrices |
| explicit INT/QUIT/TERM | cleanup-only handler resumes | 130/131/143 through finalizer | signal matrices |
| signal during cleanup | default action interrupts or replaces result | first signal recorded; later handled signals ignored | cleanup-time matrices/native test |
| cleanup failure | can replace/repeat | visible only after success with no selected signal | precedence matrices/native test |

## Overlap and current upstream state

Canonical Forgejo `main` and `make_mirror.sh` were re-read by hosted clone on 2026-08-01. The exact current identities remain `77ec9be...` and blob `6c4be092...`. The final overlap disposition is recorded in `linux-fieldwork/unit-14-overlap-scan-receipt.md`; any match requires manual review before authorization.

## Files deliberately not changed

- top-level proxy launch and cleanup code;
- `caching_proxy.py`;
- APT command sequences within `update_cache()`;
- product dependencies and packaging;
- process-group or supervisor logic;
- full mirror test setup.
