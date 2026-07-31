# Unit 11 — coverage.py cancellation owns the selected backend group

State: `ACTIVE`  
Priority-zero issue: #397, unit 11  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-11-coverage-backend-cancellation`  
External contact authorized: `false`

## TL;DR

The selected candidate starts each chosen coverage backend in a dedicated session/process group. Parent-only SIGINT sends TERM to that group, waits for the wrapper, prints a focused diagnostic, and exits 130. Existing Linux Fieldwork evidence proves the bounded claim for responsive null, QEMU-wrapper, and passwordless-sudo topologies. The next technical step is a clean application and focused rerun against current upstream `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`.

## Accomplished behavior

Each selected backend runs as leader of a caller-owned session/process group. When `coverage.py` receives SIGINT directly, it sends SIGTERM to that group, reaps the wrapper, reports interruption, and returns status 130. Responsive in-group work stops before later work can run. Ordinary unsignaled execution keeps its existing success behavior.

## Why care

The imported driver terminates only the immediate wrapper and then falls through to success. A nested backend pipeline can survive a parent-only cancellation, continue work, and leave the caller with status 0 or status 130 that says nothing about backend settlement.

## Scope

### Included

- parent-only SIGINT delivered to `coverage.py`;
- one dedicated session/process group per selected null, sudo, or QEMU backend;
- SIGTERM delivery to that owned group;
- wrapper reap and final status 130;
- focused responsive-topology regression coverage;
- ordinary unsignaled success control.

### Excluded

- TERM-to-KILL escalation;
- a cleanup timeout or survivor diagnostics;
- repeated SIGINT policy during cleanup;
- descendants that call `setsid()` or move to another group;
- real QEMU/debvm, mount, network, package, and remote-supervisor execution;
- public issue, pull request, merge request, email, or comment.

### Split boundary

Issue #341 and retained PR #347 own TERM-resistant descendants, repeated SIGINT, final-result publication, and escalation comparisons. Their synthetic matrix selected no product escalation policy. This unit retains PR #313's narrower responsive-topology result.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Intended base branch | `main` |
| Current upstream base commit observed 2026-08-01 | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | `NEEDS FORK` |
| Historical candidate head | Linux Fieldwork PR #313 `dfc6d0503fb844f4c428ce16a567a9fdcd35280a` |
| Linux Fieldwork branch | `upstream/unit-11-coverage-backend-cancellation` |
| Imported/local source identity | `upstream/mmdebstrap/coverage.py` blob `9a522484aef05deae514a98e4b6adf5feb6c886d` |
| Patch path | `patches/0001-coverage-own-selected-backend-group.patch` |
| Proposed destination | canonical mmdebstrap Forgejo repository |
| Delivery method | Forgejo fork and pull request; `NEEDS FORK` and explicit authorization |

## Canonical links

- Priority-zero unit: #397 unit 11
- Status-only predecessor: issue #141, PR #143, merged internal carrier PR #204
- Owning group-delivery issue: #306
- Canonical historical product carrier: PR #313
- Evidence refinement: PR #339; superseded carriers PR #332 and PR #336
- Stronger policy comparison: issue #341, PR #347, composed successor PR #353
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- Imported baseline parent-only SIGINT can return 0 while nested backend work survives.
- The status-only predecessor returns 130 while nested backend work can still survive.
- The group candidate creates ownership before backend execution and sends TERM to the owned group.
- Null, QEMU-wrapper, and actual passwordless-sudo responsive controls settled without later work.
- An unsignaled candidate run returned 0.
- Current Linux Fieldwork `main` still contains the exact unmodified immediate-child block in imported blob `9a5224...`, so the retained patch context remains exact locally.

### Pending

- fetch or create a controlled upstream fork;
- apply the retained patch to exact upstream commit `77ec9be...` with zero fuzz;
- compile and run the focused matrix on that exact candidate;
- inspect current upstream test conventions and trim the retained internal fixture into an upstream-sized regression;
- obtain explicit authorization before any external interaction.

### Compatibility boundary

`start_new_session=True` and `os.killpg()` are Linux/POSIX process controls. The unit is scoped to mmdebstrap's Linux test driver. `ProcessLookupError` handles the race where the group has already disappeared.

## Candidate organization

One product patch is retained:

1. `0001-coverage-own-selected-backend-group.patch` — add `signal`, start the backend in a new session, send TERM to its group on SIGINT, reap the wrapper, diagnose, and exit 130.

The upstream regression should travel in the same contribution because status correctness and selected-backend cancellation are one user-visible contract.

## Current disposition

`ACTIVE` — current-upstream application and execution remain.

## Next human decision

Authorize creation or use of a controlled mmdebstrap fork only after the exact current-base application and focused rerun are complete.

## Authority

Internal reads, branch creation, packet commits, local patch preparation, and tests are authorized. External contact remains unauthorized and none was made.
