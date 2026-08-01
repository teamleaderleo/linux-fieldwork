# Unit 12 — mmdebstrap proxysolver faithful result propagation

State: `ACTIVE`  
Priority-zero issue: #397, unit 12  
Worker or variant: `ChatGPT`  
Linux Fieldwork branch: `upstream/unit-12-proxysolver-result-propagation`  
External contact authorized: `false`

## TL;DR

The ordinary-exit repair from PR #134 and the signal-identity repair retained by PR #207 compose into one 17-line source patch. The composed candidate preserves success 0, propagates positive exit 7, replays SIGTERM and SIGINT as actual signal termination, preserves stdout/dump bytes and inherited solver stderr, unblocks an inherited blocked SIGTERM, and leaves no fake solver process behind. The exact current upstream checkout still needs to be materialized and tested before this unit can become ready for authorization.

## Accomplished behavior

`proxysolver` waits for the real APT solver after forwarding its stdout to both the caller and the requested dump file. Positive child failures become the same wrapper exit code. Signal-derived negative subprocess return codes cause the wrapper to flush stdout, restore and unblock the signal, and terminate by that same signal after the dump and subprocess contexts close.

## Why care

The imported wrapper currently reaches normal Python end-of-file after a failed child. A solver that emits a partial EDSP response and exits 7 therefore appears successful. The first repair fixed positive statuses but converted SIGTERM into unrelated ordinary status 241. Both outcomes obscure the first failing process and can make partial retained output appear complete.

## Scope

### Included

- `proxysolver` child completion and result translation;
- exact positive exit-code propagation;
- exact signal identity after output closure and flush;
- stdout/dump equality, inherited stderr, blocked-mask handling, and child cleanup controls;
- one composed source patch and one packet-specific executable regression.

### Excluded

- termination of a still-running solver when the wrapper itself receives an external signal;
- redesign of dump-file creation or solver-exec diagnostics;
- stdout sink failure policy during the explicit pre-signal flush;
- non-POSIX platforms;
- adjacent cancellation owners in `coverage.py`, `make_mirror.sh`, or `run_qemu.sh`.

### Split boundary

This unit owns the result of a child that has completed. Parent cancellation while the child remains active requires separate signal-forwarding and process-group ownership work and stays outside this source unit.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Intended base branch | `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` observed 2026-07-31 |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | `NEEDS BRANCH` |
| Candidate head | `NEEDS BRANCH` |
| Linux Fieldwork branch | `upstream/unit-12-proxysolver-result-propagation` |
| Linux Fieldwork branch base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Imported/local source identity | Git blob `5cd51fab89104d30b8b12bff18a49d38d9be0003` |
| Patch or series path | `patches/0001-proxysolver-propagate-solver-results.patch` |
| Patch SHA-256 | `74819e72482afe00abc3d4c7678a4f91cdbef61f3e2519296755a3a9fa049c48` |
| Proposed destination | canonical mmdebstrap Forgejo repository |
| Delivery method | Forgejo fork and pull request; fork and branch absent |

## Canonical links

- Priority-zero unit: #397 unit 12
- Workflow carrier: PR #398, merge `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Ordinary result issue/carrier: #133 / merged PR #134
- Signal identity issue/development carrier: #165 / PR #166
- Current-main execution carrier: PR #201
- Canonical signal evidence carrier: merged PR #207
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- baseline child exit 7 becomes wrapper 0;
- composed candidate child exit 7 becomes wrapper 7;
- success remains 0;
- ordinary-only `SystemExit(-SIGTERM)` and `SystemExit(-SIGINT)` become 241 and 254;
- composed candidate is observed as `-SIGTERM` and `-SIGINT`;
- inherited blocked SIGTERM is unblocked before exact replay;
- stdout and dump contents remain byte-identical;
- solver stderr remains inherited and unchanged;
- every recorded fake solver PID is gone;
- the five-test matrix passed twice, then passed from a simulated final repository layout.

### Not yet demonstrated

- direct byte comparison against a materialized checkout of upstream main commit `77ec9be5417ee44c96343d2347145585da1b1f94`;
- patch application and the packet regression inside that exact upstream checkout;
- upstream-native test-suite or package gates;
- a controlled fork, candidate branch, and exact candidate head;
- human acceptance of exact self-signal policy and the stated output-failure boundary.

### Compatibility boundary

The candidate uses `signal.pthread_sigmask`, so its exact signal replay path is Linux/POSIX-specific. An outer supervisor can translate the replayed signal. Failure while flushing wrapper stdout can replace the child signal result.

## Candidate organization

The source lines overlap and implement one result decision, so this unit retains one source patch:

1. `patches/0001-proxysolver-propagate-solver-results.patch`

The packet regression is retained separately at `scripts/test_proxysolver_result_propagation.py`.

## Current disposition

`ACTIVE` — exact current-upstream materialization, application, and native-context execution remain.

## Next human decision

No send decision is requested yet. The next owner action is to provide or create a controlled mmdebstrap fork after the exact current-upstream gate passes.

## Authority

Internal repository reads, branch creation, packet commits, patch composition, local disposable tests, reviews, and issue checkpoints are authorized. External issues, pull requests, comments, email, and any other upstream contact remain unauthorized; none occurred.
