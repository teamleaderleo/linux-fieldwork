# Unit 05 — mmdebstrap `run_qemu.sh` result precedence

State: `ACTIVE`  
Priority-zero issue: #397, unit 05  
Worker or variant: `GPT-5.6 Thinking upstream extraction pass`  
Linux Fieldwork branch: `upstream/unit-05-run-qemu-result-precedence`  
External contact authorized: `false`

## TL;DR

The canonical Linux Fieldwork composition has been extracted as one ordered four-patch series for `run_qemu.sh`. The series preserves results in this order:

```text
captured host failure
> completed guest or protocol failure
> first signal received during ordinary cleanup
> first cleanup failure
> success
```

All four patches applied in order without errors to the exact imported source blob `426aeeb854173569b24e64d6eb85019f45bdf0b6`, and the composed script passed `/bin/sh -n`. Debian Sources currently publishes mmdebstrap `1.5.7-3` and lists `run_qemu.sh` at the same 2,029-byte size as the imported file. A live byte-for-byte comparison against current Salsa `master`, an exact current upstream commit identity, and upstream-native execution remain incomplete.

## Accomplished behavior

`run_qemu.sh` captures the host command result before cleanup, reads a completed guest result without replacing an earlier host failure, retains the first INT or TERM received during ordinary cleanup, keeps the first cleanup failure while continuing later cleanup actions, runs cleanup once, and returns the earliest authoritative failure.

A signal received during cleanup after guest success returns 130 or 143. A guest failure completed before cleanup remains ahead of a later cleanup-time signal. Later handled INT or TERM signals do not replace an established result or interrupt bounded cleanup.

## Why care

The original shared `EXIT INT TERM` handler could:

- replace timeout or host failure with generic guest failure 1;
- make INT or TERM return a guest-dependent 0 or 1;
- invoke cleanup again through the still-installed EXIT trap;
- let a second signal replace the first signal result and interrupt cleanup;
- ignore the first signal received during ordinary cleanup;
- let a later cleanup-time signal replace a guest failure that had already completed.

Those outcomes misclassify the failure owner and can leave temporary state behind.

## Scope

### Included

- result selection inside `run_qemu.sh`;
- separate ordinary EXIT and explicit INT/TERM handlers;
- first-writer signal retention during ordinary cleanup;
- first cleanup-failure retention while later cleanup actions continue;
- once-only bounded cleanup;
- ordered four-patch packaging and exact local application receipt.

### Excluded

- QEMU or `debvm-run` command construction;
- timeout duration or timeout implementation;
- process-group delivery, foreground-child cancellation, or escalation;
- HUP and QUIT policy;
- guest image behavior, networking, mounts, root execution, and package installation;
- broader `run_qemu.sh` refactoring;
- public upstream contact.

### Split boundary

The four patches form one reviewable lifecycle correction. Each patch closes a distinct demonstrated predecessor failure, while the final behavior depends on their ordered composition. Process-group cancellation and additional signal families remain separate work.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://salsa.debian.org/debian/mmdebstrap.git` |
| Intended base branch | `master` |
| Upstream base commit | `LIVE SALSA HEAD UNRESOLVED`; published tag `debian/1.5.7-3` is shown at abbreviated commit `6fde9997` |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | `LOCAL PATCH SERIES ONLY` |
| Candidate head | composed script SHA-256 `8d2b0fdef2c93fcd3d97f296dfe58d3cbe198e8a02ac85930aa8c3c89aedb90f` |
| Linux Fieldwork branch | `upstream/unit-05-run-qemu-result-precedence` |
| Linux Fieldwork head | recorded in [`HANDOFF.md`](HANDOFF.md) after packet finalization |
| Imported/local source identity | Git blob `426aeeb854173569b24e64d6eb85019f45bdf0b6`; 2,029 bytes; SHA-256 `da89b51df80786f4e379b2ba5b033aab6c4e1d7acc8ba17cf57e67159a32e300` |
| Patch or series path | [`patches/`](patches/) |
| Proposed destination | repository-root `run_qemu.sh` |
| Delivery method | Salsa fork and merge request after explicit authorization |

## Canonical links

- Priority-zero unit: [#397 unit 05](https://github.com/teamleaderleo/linux-fieldwork/issues/397)
- Owning Linux Fieldwork issue: [#269](https://github.com/teamleaderleo/linux-fieldwork/issues/269)
- Policy review issue: [#297](https://github.com/teamleaderleo/linux-fieldwork/issues/297)
- Canonical Linux Fieldwork composition: [PR #319](https://github.com/teamleaderleo/linux-fieldwork/pull/319)
- Predecessor carriers: [PR #270](https://github.com/teamleaderleo/linux-fieldwork/pull/270), [PR #282](https://github.com/teamleaderleo/linux-fieldwork/pull/282), [PR #290](https://github.com/teamleaderleo/linux-fieldwork/pull/290), [PR #304](https://github.com/teamleaderleo/linux-fieldwork/pull/304)
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream merge-request draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- The imported source is exactly Git blob `426aeeb854173569b24e64d6eb85019f45bdf0b6`.
- Each retained patch has an exact Git blob identity recorded in `SOURCE_MAP.md`.
- `git apply --check` and `git apply` succeeded for patches 1 through 4 in order.
- The composed script passed `/bin/sh -n`.
- The composed script is 2,924 bytes with SHA-256 `8d2b0fdef2c93fcd3d97f296dfe58d3cbe198e8a02ac85930aa8c3c89aedb90f`.
- Canonical Linux Fieldwork CI run `30628645668`, job 889, passed 276 repository tests on PR #319 exact head `2fe3f99364df29de217536dc35a4d03b10f49640`.
- The five focused modules retain losing controls for every predecessor policy.

### Incomplete

- Resolve the full current commit SHA of canonical Salsa `master`.
- Fetch current upstream `run_qemu.sh` bytes and compare them with the imported blob.
- Apply or adapt the series on that exact live upstream head.
- Run upstream-native focused tests and ordinary project gates on the rebased candidate.
- Search current Salsa branches, issues, and merge requests for equivalent active work.
- Create a controlled fork only when needed for internal candidate execution or after the repository owner approves that step.

### Compatibility boundary

The selected order depends on the guest result being complete and durable before host ordinary cleanup begins. Re-evaluate patch 4 if upstream changes the guest-result publication or `debvm-run` return sequence. Signal suppression is justified only across bounded cleanup.

## Candidate organization

1. `0001-preserve-primary-result.patch` — separate ordinary and signal cleanup, preserve host/guest/cleanup results, and prevent EXIT re-entry.
2. `0002-retain-first-signal-through-cleanup.patch` — keep handled INT and TERM inert while explicit-signal cleanup completes.
3. `0003-retain-signal-during-exit-cleanup.patch` — record the first INT or TERM during ordinary EXIT cleanup.
4. `0004-preserve-completed-guest-before-cleanup-signal.patch` — place completed guest failure ahead of a later cleanup-time signal.

These belong in one merge request because each intermediate state has a demonstrated losing case and patch 4 selects the final event-order policy.

## Current disposition

`ACTIVE` — the internal source composition and extraction receipt are complete; live Salsa reconciliation and upstream-native execution remain.

## Next human decision

No publication decision is ripe yet. After the live rebase and upstream tests are complete, the repository owner will decide whether to authorize a Salsa merge request, request further testing, or hold the unit.

## Authority

Internal repository reads, branch creation, patch extraction, local application, syntax checks, packet writing, and issue checkpoints are authorized. No upstream issue, merge request, email, comment, review, or other public contact has been authorized or made.
