# Unit 14 — mmdebstrap make_mirror update_cache worker lifecycle

State: `ACTIVE`  
Priority-zero issue: #397, unit 14  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-14-make-mirror-update-cache`  
External contact authorized: `false`

## TL;DR

The complete worker lifecycle is implemented and tested as a two-commit candidate on exact canonical mmdebstrap `main`. The `update_cache()` subshell cleans only its APT state, leaves the top-level proxy to its owner, routes ordinary completion, implicit EXIT, explicit signals, cleanup-time signals, and cleanup failure through one finalizer, retains the first handled signal through bounded cleanup, and applies:

```text
existing ordinary or explicit-signal failure
> first signal recorded during ordinary cleanup
> cleanup failure
> success
```

The final candidate is `teamleaderleo/mmdebstrap` branch `linux-fieldwork/unit-14-make-mirror-update-cache-upstream-main`, head `76728bbb8e084b54261713ba80762cd6f6ada79a`, two commits ahead and zero behind canonical snapshot `77ec9be5417ee44c96343d2347145585da1b1f94`. The source, exact-candidate matrix, and registered native regression are green. A classified live overlap receipt and the canonical delivery/authorization decision remain.

## Accomplished behavior

The `update_cache()` worker owns its temporary APT root and final status. It never signals the parent-owned caching proxy. INT, QUIT, and TERM select 130, 131, and 143. Cleanup runs once. The first handled signal arriving during ordinary cleanup is retained while later handled signals are ignored until bounded cleanup finishes. Existing command or explicit-signal failure outranks a cleanup-time signal, which outranks cleanup failure.

The candidate also registers `tests/make-mirror-update-cache-worker-lifecycle` in `coverage.txt`. The test extracts the actual finalizer and handlers from `make_mirror.sh` and exercises real shell signals, cleanup barriers, precedence, state removal, and rerun.

## Why care

The baseline can convert a worker-only signal into status 0, continue later work, clean APT state twice, and kill a proxy owned by the top-level shell. A first terminating repair still allowed signals during cleanup to interrupt cleanup or replace an already selected result. Partial cleanup can alter the next mirror run.

## Scope

### Included

- worker-owned APT cleanup;
- implicit EXIT, ordinary success/failure, INT/QUIT/TERM, cleanup-time signals, and cleanup failure;
- first-result precedence and later-signal suppression;
- once-only cleanup and immediate rerun;
- upstream-native focused regression;
- canonical upstream history, source branch, exact evidence, and final draft.

### Excluded

- top-level proxy launch, PID registration, stop/wait, and cache-publication ownership, owned by unit 13 / PR #224;
- prompt cancellation of unowned foreground descendants, held by issue #263 / PR #264;
- HUP, TERM-to-KILL escalation, hostile descendants, permanently blocking cleanup, real mirror generation, root, and QEMU.

### Split boundary

The worker patch composes with the top-level lifecycle only through the pipeline result. It does not modify top-level proxy ownership. Broader process-group supervision remains held without measured harmful latency or a supported supervisor contract.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Intended base branch | `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Base source blob | `make_mirror.sh` `6c4be092edcf23b56b63a3befe238c099c45f590` |
| Controlled repository | `https://github.com/teamleaderleo/mmdebstrap` |
| Canonical snapshot branch | `linux-fieldwork/upstream-main-snapshot` |
| Candidate branch | `linux-fieldwork/unit-14-make-mirror-update-cache-upstream-main` |
| Candidate source commit | `b2a9a09b36fd13f22a024ebf8522ac58543eac28` |
| Candidate head | `76728bbb8e084b54261713ba80762cd6f6ada79a` |
| Candidate source blob | `make_mirror.sh` `7d92a29a05ade7f5da397a1a9d03e601092f9465` |
| Linux Fieldwork branch | `upstream/unit-14-make-mirror-update-cache` |
| Retained source patch | `patches/0001-update-cache-worker-lifecycle.patch` |
| Patch SHA-256 | `980720d262d0f5d4a568be54851e144652ae6d882a8ad0e8aa228c8ffed2ae42` |
| Proposed destination | canonical mmdebstrap Forgejo repository |
| Delivery method | Forgejo pull request or accepted patch route after explicit authorization; GitHub branch is controlled staging and evidence |

## Canonical links

- Priority-zero unit: #397 unit 14
- Owning Linux Fieldwork issue: #231
- Canonical components: merged PR #286 and merged PR #324
- Historical construction: PRs #238, #259, #260, #267, #305
- Routing refresh: merged PR #322
- Adjacent top-level owner: merged PR #224
- Broader cancellation hold: issue #263 / PR #264
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue fallback: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- current canonical Forgejo history cloned and mirrored exactly;
- canonical base and retained import share source blob `6c4be092...`;
- composed patch applied with zero fuzz;
- candidate shell syntax and diff hygiene passed;
- worker/proxy ownership source assertions passed;
- ten exact-candidate lifecycle tests passed in 3.459 seconds;
- native test passed `sh -n`, shellcheck, upstream shfmt options, direct execution, and `git diff --check`;
- candidate is two commits ahead, zero behind, with only three intended paths;
- cleanup, status precedence, later-work suppression, state removal, and immediate rerun are covered;
- final upstream pull-request draft is complete.

### Remaining

- read and classify `linux-fieldwork/unit-14-overlap-scan-receipt.md` when the hosted read-only scan lands;
- create a Forgejo-compatible fork/branch or confirm an accepted patch route as part of an explicitly authorized submission;
- record authorization or hold decision.

### Compatibility boundary

The product change adds no command, package dependency, process group, supervisor, APT behavior, or top-level proxy change. Cleanup is treated as bounded and completes after the first handled signal. The native test uses Python's standard library inside the project's shell-test convention and adds no product runtime dependency.

## Candidate organization

1. `make_mirror: make update_cache cleanup worker-owned`
2. `tests: cover make_mirror update_cache worker lifecycle`

The source behavior remains one composed patch. The separate native-test commit keeps review of the lifecycle and review of its regression distinct.

## Current disposition

`ACTIVE` — technical implementation, current-upstream rebase, exact-candidate tests, native regression, cleanup/rerun, complete diff review, and draft are complete. The live overlap receipt is the first incomplete technical routing gate. After a clean scan, only authorization and canonical delivery setup remain.

## Next human decision

After the overlap receipt is classified, choose one:

- authorize creation of the canonical Forgejo delivery branch and submission of the prepared two-commit pull request;
- hold the unit and name the reason.

## Authority

Internal repository reads, controlled branches, canonical read-only clone, hosted tests, packet commits, and draft preparation are authorized. No canonical-upstream issue, pull request, comment, email, review, or other write occurred.
