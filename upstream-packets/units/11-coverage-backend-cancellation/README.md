# Unit 11 — coverage.py cancellation owns the selected backend group

State: `READY FOR AUTHORIZATION`  
Priority-zero issue: #397, unit 11  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-11-coverage-backend-cancellation`  
Internal review surface: PR #401  
External contact authorized: `false`

## TL;DR

The selected candidate starts each chosen coverage backend in a dedicated session/process group. Parent-only SIGINT sends TERM to that group, waits for the wrapper, prints a focused diagnostic, and exits 130.

The retained upstream-root patch applied with zero fuzz to canonical mmdebstrap `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`. Exact canonical null, QEMU-wrapper, and passwordless-sudo controls passed twice, including the PR #339 QEMU handler-entry refinement. The technical unit is complete for its responsive-topology claim. A human send/hold decision and controlled fork remain.

## Accomplished behavior

Each selected backend runs as leader of a caller-owned session/process group. When `coverage.py` receives SIGINT directly, it sends SIGTERM to that group, reaps the wrapper, reports interruption, and returns status 130. Responsive in-group work stops before later work can run. Ordinary unsignaled execution keeps its existing success behavior.

## Why care

The imported driver terminates only the immediate wrapper and then falls through to success. A nested backend pipeline can survive a parent-only cancellation, continue work, and leave the caller with status 0. The status-only repair returns 130 while still allowing nested work to survive. The selected candidate owns both the cancellation result and the selected backend boundary.

## Scope

### Included

- parent-only SIGINT delivered to `coverage.py`;
- one dedicated session/process group per selected null, sudo, or QEMU backend;
- SIGTERM delivery to that owned group;
- wrapper reap and final status 130;
- responsive null, QEMU-wrapper, and actual passwordless-sudo controls;
- PR #339 handler-entry refinement for the QEMU losing controls;
- ordinary unsignaled success, cleanup, and immediate rerun.

### Excluded

- TERM-to-KILL escalation;
- cleanup timeout or survivor diagnostics;
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
| Exact upstream base executed | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Last upstream commit touching `coverage.py` | `c82fc7e261c7a2fd85e499484108408fd42331d2` |
| Canonical/imported `coverage.py` blob | `9a522484aef05deae514a98e4b6adf5feb6c886d` |
| Canonical `run_null.sh` blob | `e0a8c106f9d3d636baea286d2ab33834748dffc9` |
| Canonical `run_qemu.sh` blob | `426aeeb854173569b24e64d6eb85019f45bdf0b6` |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | `NEEDS FORK` |
| Historical mechanism head | PR #313 `e90fc438f530f7bd78ffd6fd1ba24c665bd96913` |
| Historical evidence head | PR #313 `dfc6d0503fb844f4c428ce16a567a9fdcd35280a` |
| Refined QEMU test head | PR #339 `8253ab2ef6fed22b34fc5f5d6d20cda75c25e2c7` |
| Refined QEMU test blob | `0c2a050faf8e98320fc0c4fe4634d46bdf7f0dfa` |
| Retained upstream-root patch blob | `f1a2c75adfa009b6f1ac29e5a31bef526400444f` |
| Historical prefixed patch blob | `4f2a749e50d42655ebb6519ca6550d2f666985bc` |
| Linux Fieldwork branch | `upstream/unit-11-coverage-backend-cancellation` |
| Internal review surface | PR #401 |
| Proposed destination | canonical mmdebstrap Forgejo repository |
| Delivery method | Forgejo fork and pull request after explicit authorization |

## Canonical execution receipt

Linux Fieldwork Actions run `30689911760` passed on branch head `83efaa3b3baee05c6b8f96138a3ee619942ce984`.

- `canonical-upstream-gate`: exact canonical checkout, blob equality, zero-fuzz packet-patch application, compilation, six null/source controls twice;
- `canonical-refined-topology-gate`: canonical source and wrappers inserted into exact PR #339 carrier, 14 null/QEMU-wrapper/sudo controls twice;
- no test skips occurred;
- actual passwordless-sudo root-worker controls ran;
- both immediate reruns passed;
- GitHub runner cleanup reported orphan-process cleanup completion.

Artifacts:

- `8815289674`, `unit-11-canonical-upstream-gate`, SHA-256 `25e62dec929f27e628816568d6264f2bee45474c00b00c3c047f53209608ef1d`;
- `8815290820`, `unit-11-canonical-refined-topology-gate`, SHA-256 `63634782bfd230129238ee71aa60ad83ae5b43dfcf3291123cfdbd0770bdf63e`.

## Canonical links

- Priority-zero unit: #397 unit 11
- Internal review surface: PR #401
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

- imported baseline parent-only SIGINT returns 0 after deliberate survivor release;
- status-only predecessor returns 130 after deliberate survivor release;
- both losing variants leave later-capable nested work alive before release;
- group candidate returns 130 and leaves no live responsive in-group process;
- later-work markers remain absent for the group candidate;
- ordinary foreground-group SIGINT remains clean;
- unsignaled null, QEMU-wrapper, and sudo candidate runs succeed;
- exact packet patch applies with zero fuzz to canonical source and compiles;
- complete focused matrices survive an immediate rerun.

### Evidence limits

- real QEMU/debvm and package operations were outside the focused synthetic wrapper controls;
- TERM-resistant, deferring, or group-escaping descendants remain outside the claim;
- the full mirror-backed coverage matrix was not run because it requires prepared Debian mirror state and exceeds this source unit's discriminator;
- upstream maintainer review has not occurred.

## Candidate organization

One product patch is retained:

1. `patches/0001-coverage-own-selected-backend-group.patch` — add `signal`, start the backend in a new session, send TERM to its group on SIGINT, reap the wrapper, diagnose, and exit 130.

The focused regression evidence remains reproducible through `scripts/test_current_import.py` and the exact PR #339 carrier identities recorded in `TESTS.md`.

## Current disposition

`READY FOR AUTHORIZATION` — the exact current-base application, focused execution, cleanup, and immediate rerun are complete. External submission remains prohibited until a human authorizes send and a controlled fork is selected or created.

## Next human decision

Choose `SEND` or `HOLD`. A `SEND` decision must authorize controlled-fork creation/use and public Forgejo interaction.

## Authority

Internal reads, branch creation, packet commits, tests, CI, and internal PR #401 are authorized. External contact remains unauthorized and none was made.
