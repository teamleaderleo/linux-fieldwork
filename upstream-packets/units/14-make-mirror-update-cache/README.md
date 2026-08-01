# Unit 14 — mmdebstrap make_mirror update_cache worker lifecycle

State: `ACTIVE`  
Priority-zero issue: #397, unit 14  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-14-make-mirror-update-cache`  
External contact authorized: `false`

## TL;DR

The final internal correction is a two-stage worker-lifecycle repair. The `update_cache()` subshell cleans only its APT state, leaves the top-level proxy to its owner, converges ordinary completion, implicit EXIT, explicit signals, and cleanup-time signals through one finalizer, retains the first handled signal through bounded cleanup, and preserves this result order:

```text
existing ordinary or explicit-signal failure
> first signal recorded during ordinary cleanup
> cleanup failure
> success
```

Current upstream `main` is pinned at `77ec9be5417ee44c96343d2347145585da1b1f94`. Its `make_mirror.sh` blob is still `6c4be092edcf23b56b63a3befe238c099c45f590`, byte-identical to the Linux Fieldwork import used by every retained regression. This pass extracted the two landed internal patches into one upstream-facing patch under `patches/` and preserved the exact evidence and remaining gates.

## Accomplished behavior

The `update_cache()` pipeline worker owns its temporary APT root and final status. It never signals the parent-owned caching proxy. INT, QUIT, and TERM select 130, 131, and 143. Cleanup runs once. The first handled signal arriving during ordinary cleanup is retained while later handled signals are ignored until bounded cleanup finishes. Existing command or explicit-signal failure outranks a cleanup-time signal, which outranks cleanup failure.

## Why care

The upstream baseline can convert a worker-only signal into status 0, continue later work, clean APT state twice, and kill a proxy owned by the top-level shell. The first internal repair closes those failures but initially restores default signal handling before cleanup, allowing a later handled signal to interrupt cleanup or replace the first selected result. Partial cleanup can change the next mirror run.

## Scope

### Included

- worker-only APT cleanup ownership;
- ordinary, implicit EXIT, INT, QUIT, TERM, and cleanup-time signal finalization;
- first-result and cleanup-failure precedence;
- once-only cleanup and immediate rerun evidence;
- one composed patch against current upstream `main`.

### Excluded

- top-level proxy launch, PID registration, stop/wait, and cache-publication ownership, owned by unit 13 and merged PR #224;
- prompt cancellation of unowned foreground descendants, held by issue #263 / PR #264;
- HUP, TERM-to-KILL escalation, hostile descendants, permanently blocking cleanup, real APT/network mirror execution, and the complete multi-architecture loop.

### Split boundary

The worker patch composes with the top-level lifecycle only through the pipeline result. It does not modify top-level proxy ownership. Prompt process-group supervision remains disproportionate without measured harmful latency or a supported supervisor contract.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Intended base branch | `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | `NEEDS BRANCH` |
| Candidate head | `NEEDS BRANCH` |
| Linux Fieldwork branch | `upstream/unit-14-make-mirror-update-cache` |
| Linux Fieldwork head | recorded in `HANDOFF.md` after final packet commit |
| Imported/local source identity | `upstream/mmdebstrap/make_mirror.sh`, blob `6c4be092edcf23b56b63a3befe238c099c45f590` |
| Patch or series path | `upstream-packets/units/14-make-mirror-update-cache/patches/0001-update-cache-worker-lifecycle.patch` |
| Proposed destination | canonical mmdebstrap Forgejo repository |
| Delivery method | Forgejo fork and pull request; controlled fork still required |

## Canonical links

- Priority-zero unit: #397 unit 14
- Owning Linux Fieldwork issue: #231
- Canonical Linux Fieldwork compositions: merged PR #286 and merged PR #324
- Historical construction carriers: PRs #238, #259, #260, #267, and #305
- Routing refresh: merged PR #322
- Adjacent holds/controls: issue #263 / PR #264; issue #271 / PR #273; patch validator PR #302; top-level lifecycle PR #224
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- upstream source identity has no drift from the retained import;
- PR #286 exact-head CI `30624335126` / 842 passed 249 repository tests and the worker ownership, signal, cleanup-failure, and rerun controls;
- PR #324 exact-head CI `30630467076` / 916 passed repository discovery, both cleanup-time signal matrices, all PR #286 regressions, zero-fuzz two-patch application, and complete shell syntax;
- current public overlap search on 2026-07-31 found no indexed upstream issue or pull request describing this worker lifecycle;
- the two internal patches were collapsed into one retained upstream-facing patch with SHA-256 `980720d262d0f5d4a568be54851e144652ae6d882a8ad0e8aa228c8ffed2ae42`;
- local synthetic exact-position application verified the combined hunk counts and line arithmetic with `patch --fuzz=0`.

### Not yet demonstrated

- application of the new single combined carrier to a checked-out full upstream tree in this environment;
- upstream-native focused or integration tests on a candidate branch;
- complete review of a public-repository candidate diff;
- controlled fork and branch identity.

### Compatibility boundary

The candidate uses POSIX `/bin/sh` functions and traps already exercised by the retained real-shell matrices. It deliberately completes bounded cleanup after the first handled cleanup-time signal. It adds no process-group dependency, supervisor, network behavior, package dependency, or top-level proxy change.

## Candidate organization

One patch is selected for upstream review because both internal patches edit the same finalizer and implement one worker result/cleanup contract:

1. `0001-update-cache-worker-lifecycle.patch` — confines ownership, centralizes finalization, records cleanup-time signals, completes cleanup once, and applies the complete precedence rule.

The two original retained patches remain canonical provenance under `investigations/make-mirror-update-cache-subshell/`.

## Current disposition

`ACTIVE` — the source extraction and current-base identity are complete. A controlled upstream branch, full-tree application, upstream-native gates, and exact candidate diff review remain.

## Next human decision

No send decision is ripe yet. The next repository action is to create or identify a controlled mmdebstrap fork, apply the retained patch to upstream `main`, and run the focused upstream gates. External contact still requires explicit authorization after the technical gate is complete.

## Authority

Internal repository reads, branch creation, packet commits, source extraction, local checks, public-source reads, and draft preparation are authorized. No upstream issue, pull request, comment, email, review, or other external contact is authorized or made.
