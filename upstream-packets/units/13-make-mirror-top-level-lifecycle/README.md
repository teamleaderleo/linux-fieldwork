# Unit 13 — make_mirror top-level signal and proxy ownership

State: `ACTIVE`  
Priority-zero issue: #397, unit 13  
Worker or variant: `ChatGPT`  
Linux Fieldwork branch: `upstream/unit-13-make-mirror-top-level-lifecycle`  
External contact authorized: `false`

## TL;DR

PR #224 supplies the selected top-level `make_mirror.sh` lifecycle patch. It terminates after signal cleanup, waits for each owned proxy, closes both proxy launch-to-PID registration windows, retains the first signal, applies cache and QEMU cleanup only under real ownership, preserves an active published cache, and permits immediate clean reruns.

The user supplied `teamleaderleo/mmdebstrap` as a controlled GitHub fork. Its repository history follows the `deepin-community/mmdebstrap` packaging lineage rather than canonical upstream Forgejo history, but its `master` branch carries the exact current `make_mirror.sh` blob required by this unit. A dedicated candidate branch now exists. The fork therefore solves source transport and branch ownership for unit 13 without proving that every file or commit is synchronized with canonical upstream.

Fresh source application, `/bin/sh -n`, focused rerun, and complete candidate diff remain before authorization readiness. The local execution runner still cannot resolve `github.com`, so this pass produced no fresh shell-test result.

## Accomplished behavior

The proposed correction gave the top-level shell explicit ownership of cancellation and both proxy children. INT, QUIT, and TERM cleaned once and exited 130, 131, or 143. Each proxy launch retained the first signal until `$!` was registered, then stopped and waited for that exact child. Private-cache deletion began only after readiness, QEMU temporary cleanup followed its real lifetime, and a cache already selected by `shared/cache` survived late cleanup.

## Why care

The baseline can turn cancellation into success or a later unrelated failure. It can resume mirror work after cleanup, run cleanup twice, leave a newly launched proxy outside ownership, retain port 8080, and interfere with an immediate rerun. Broad cleanup can also delete a cache that has already become active.

## Scope

### Included

- top-level ordinary EXIT cleanup;
- top-level INT/QUIT/TERM statuses and continuation;
- both `caching_proxy.py` launch-to-PID registration intervals;
- proxy signal, wait, reaping, and PID clearing;
- first-signal precedence during launch;
- first-readiness private-cache ownership transition;
- QEMU temporary-directory ownership;
- active-cache publication preservation;
- focused real-shell negative controls and reruns.

### Excluded

- `update_cache()` pipeline-subshell cleanup and result precedence;
- proxy TERM-to-KILL escalation;
- HUP and hostile descendants;
- process-group delivery policy;
- full network mirror, APT, and QEMU execution in the focused regression;
- any public upstream issue, pull request, email, or comment.

### Split boundary

Unit 13 owns the parent shell and its top-level resources. Unit 14 owns the `update_cache()` worker subshell and its APT-root cleanup. PRs #305/#324 are adjacent evidence; their patch remains outside this candidate.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Intended upstream base branch | `main` |
| Canonical upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Canonical upstream file identity | `make_mirror.sh` blob `6c4be092edcf23b56b63a3befe238c099c45f590` |
| Controlled GitHub fork | `teamleaderleo/mmdebstrap` |
| Fork provenance | fork of `deepin-community/mmdebstrap`; downstream packaging lineage |
| Fork default branch | `master` at `574048f2a720057b75e56622003932f344dc700a` |
| Fork file identity | `make_mirror.sh` blob `6c4be092edcf23b56b63a3befe238c099c45f590` |
| Candidate source branch | `linux-fieldwork/unit-13-make-mirror-top-level-lifecycle` |
| Candidate branch head | `574048f2a720057b75e56622003932f344dc700a` before source application |
| Candidate source identity | retained patch from PR #224 head `13b3c529e983b3ad967725f99f4e31d867fa4742` |
| Linux Fieldwork branch | `upstream/unit-13-make-mirror-top-level-lifecycle` |
| Linux Fieldwork branch base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Canonical patch blob | `25f9474945a6eb0efa52415f1fcd18e784655d59` |
| Packet patch | `patches/0001-make-mirror-top-level-signal-proxy-ownership.patch` |
| Proposed destination | canonical `josch/mmdebstrap` Forgejo after explicit authorization |
| Current branch purpose | controlled execution and review transport; no upstream contact |

The controlled GitHub fork is suitable for this unit because the changed file has exact byte identity with canonical upstream. Its unrelated commit lineage must remain explicit in every comparison and draft.

## Canonical links

- Priority-zero unit: #397 unit 13
- Owning Linux Fieldwork issue: #157
- Canonical Linux Fieldwork composition: merged PR #224
- Parent predecessor carriers: PRs #159 and #205
- Adjacent worker carriers: PRs #305 and #324
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- baseline cleanup-only TERM resumes later work, cleans twice, and exits 0;
- candidate TERM exits 143, omits later work, and runs one owner cleanup;
- INT/QUIT/TERM map to 130/131/143;
- proxy children are signaled, waited, and cleared;
- both launch-registration intervals retain cancellation until PID ownership;
- first TERM wins over a later INT during launch handoff;
- first launch has zero signal-time cache deletion calls and reruns through startup preflight;
- second launch deletes owned private cache state;
- an active published cache survives late cleanup;
- immediate unsignaled reruns succeed;
- exact #224 focused matrix passed twice and exact-head CI `30586490855` passed;
- canonical upstream, Debian dgit, Linux Fieldwork import, and controlled fork carry the same `make_mirror.sh` blob;
- the controlled candidate branch exists and is currently identical to fork `master`.

### Not yet demonstrated

- source patch committed on the controlled candidate branch;
- fresh zero-fuzz patch application against the controlled fork checkout;
- fresh complete shell syntax and focused unittest execution;
- complete diff of the patched candidate branch;
- full upstream `make_mirror.sh` mirror build;
- upstream `coverage.sh` after the candidate;
- escalation, HUP, process-group, hostile-descendant, and permanently blocking cleanup behavior.

### Compatibility boundary

The candidate uses conventional numeric signal statuses and does not re-raise signals. Parent-only delivery may remain deferred during an unrelated foreground wait. Cleanup helper failure can leave retained state while the primary command or signal status remains authoritative. The proxy receives TERM only; no escalation policy is added.

## Candidate organization

One upstream source commit is proposed because every edit participates in the same top-level owner invariant and partial commits create unsafe intermediate states.

1. `make_mirror.sh: own signal exit and proxy launch lifecycle`

The packet retains two focused regression modules as evidence. Their final upstream location remains a destination-specific review decision.

## Current disposition

`ACTIVE` — technical execution remains.

The canonical patch, exact source base, split boundary, controlled branch, public drafts, and historical evidence are complete. Source application and focused execution are the first incomplete technical step.

## Next human decision

No send decision is needed yet. The controlled branch may be used for internal source application and testing. Any pull request, issue, comment, email, or canonical-upstream fork action still requires explicit authorization.

## Authority

The user's creation of `teamleaderleo/mmdebstrap` supplied a controlled fork for internal work. This pass created the dedicated candidate branch in that fork and made no contact with canonical upstream. External issue creation, pull request, email, comment, review, or other upstream interaction remains unauthorized.