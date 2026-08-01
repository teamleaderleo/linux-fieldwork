# Current handoff

Updated: `2026-08-01 08:09 +08:00`  
Worker or variant: `GPT-5.6 Thinking`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-12-proxysolver-result-propagation` |
| Branch creation base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Pre-handoff technical head | `83a91f4235ca451db862d8b0bdbd41b532c706e0` |
| Final packet branch tip | this HANDOFF update commit; exact SHA is recorded in the issue #397 `UNIT CHECKPOINT` |
| Upstream base repository/branch | `https://gitlab.mister-muffin.de/josch/mmdebstrap`, `main` |
| Public upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94`, re-observed 2026-08-01 |
| Candidate fork/branch | `NEEDS FORK` / `NEEDS BRANCH` |
| Candidate head | `NEEDS BRANCH` |
| Imported source | blob `5cd51fab89104d30b8b12bff18a49d38d9be0003`, 1,643 bytes |
| Composed patch | `patches/0001-proxysolver-propagate-solver-results.patch`, SHA-256 `74819e72482afe00abc3d4c7678a4f91cdbef61f3e2519296755a3a9fa049c48` |
| Owning issue/carriers | #397 unit 12; #133/#134; #165/#166; #201; #207 |
| Latest hosted evidence | PR #207 CI `30579889333`; PR #201 current-main run `30579465025` |
| Latest source refresh | `artifacts/2026-08-01-current-upstream-check.md` |

## Current bounded claim

Against exact imported source blob `5cd51fab89104d30b8b12bff18a49d38d9be0003`, the composed patch preserves success 0, propagates positive exit 7, preserves actual SIGTERM and SIGINT termination, unblocks inherited blocked SIGTERM, preserves stdout/dump bytes and inherited stderr, and leaves no fake solver PID alive. Current public metadata continues to corroborate that source identity. Exact canonical raw-byte comparison and native-suite conclusions remain open.

## Work completed in this pass

- resumed the existing unit branch and verified the full required packet bundle;
- re-read issue #397, the packet protocol/index, and the complete proxysolver carrier chain;
- verified the branch contains one composed source patch, one executable regression, complete technical records, decision log, public drafts, and handoff;
- refreshed the canonical public repository: main still displays `77ec9be5417ee44c96343d2347145585da1b1f94`, `proxysolver` still displays the 2021 last-change record, and no equivalent proxysolver issue surfaced among the visible open issues;
- refreshed Debian source corroboration: forky/sid still carries `mmdebstrap 1.5.7-3` and displays a 1,643-byte root `proxysolver`;
- attempted direct canonical git/raw retrieval; classified the failure as execution-environment DNS/cache tooling before source access;
- preserved the exact observation, commands, results, and remaining discriminator in `artifacts/2026-08-01-current-upstream-check.md`;
- updated this handoff and prepared the required internal issue checkpoint.

## Changed paths

Packet paths already present on the branch:

- `upstream-packets/units/12-proxysolver-result-propagation/README.md`
- `upstream-packets/units/12-proxysolver-result-propagation/SOURCE_MAP.md`
- `upstream-packets/units/12-proxysolver-result-propagation/DEEP_DIVE.md`
- `upstream-packets/units/12-proxysolver-result-propagation/TESTS.md`
- `upstream-packets/units/12-proxysolver-result-propagation/DECISIONS.md`
- `upstream-packets/units/12-proxysolver-result-propagation/UPSTREAM_ISSUE.md`
- `upstream-packets/units/12-proxysolver-result-propagation/UPSTREAM_PR.md`
- `upstream-packets/units/12-proxysolver-result-propagation/HANDOFF.md`
- `upstream-packets/units/12-proxysolver-result-propagation/patches/0001-proxysolver-propagate-solver-results.patch`
- `upstream-packets/units/12-proxysolver-result-propagation/scripts/test_proxysolver_result_propagation.py`

Added in this continuation:

- `upstream-packets/units/12-proxysolver-result-propagation/artifacts/2026-08-01-current-upstream-check.md`

## Distinguishing observations

- `Popen.__exit__()` waits but does not turn child failure into wrapper failure.
- `SystemExit(-15)` and `SystemExit(-2)` produce ordinary statuses 241 and 254.
- exact self-signal replay preserved `-SIGTERM` and `-SIGINT` in the expanded matrix.
- the inherited blocked-SIGTERM control passed because the candidate unblocks before replay.
- solver stderr remained inherited while stdout and dump stayed identical.
- the public canonical repository still displays main at `77ec9be5417ee44c96343d2347145585da1b1f94` and `proxysolver` last changed in 2021.
- Debian Sources displays current forky/sid `mmdebstrap 1.5.7-3` with a 1,643-byte root `proxysolver`, matching the imported file size.
- matching history and size corroborate identity; only byte retrieval plus `git hash-object` can close the exact source gate.

## Gates completed

- sequential application of historical ordinary and signal patches to the imported blob: PASS, no fuzz/offset;
- composed patch generation and complete diff review: PASS;
- local compilation of composed source: PASS;
- packet five-test matrix, first successful run: 5 tests in 14.097s, PASS;
- immediate rerun: 5 tests in 14.112s, PASS;
- simulated final repository layout: 5 tests in 13.536s, PASS;
- cleanup/PID disappearance assertions: PASS;
- public issue/pull-request overlap check: no equivalent surfaced;
- 2026-08-01 current public repository/package corroboration: PASS as metadata evidence only.

## Red or neutral runs classified

- first packet script attempt: fixture path packaging; historical status patch expected `upstream/mmdebstrap/proxysolver`; 0 product tests ran. Disposable layout corrected.
- historical PR #166 malformed patch head `f57b43b32d78ad5dcd58039c816907fe7abe27de`: patch packaging, superseded by green heads.
- 2026-08-01 `git ls-remote` against canonical Forgejo: `Could not resolve host`; environment DNS/network failure before repository access.
- canonical raw/archive and Debian source-file retrieval through the web reader: cache-miss/safe-URL tool boundary before file bytes; no product or patch behavior ran.

## Cleanup state

All local test roots used temporary directories and were removed. Every fake solver PID was confirmed gone. The failed network commands created no checkout or files. No package operation, mount, socket, upstream fork, public issue, pull request, comment, email, or other upstream contact occurred. Intentional retained state consists only of the Linux Fieldwork branch, packet, patch, script, dated evidence artifact, and internal #397 checkpoint.

## First incomplete step

Materialize canonical upstream main commit `77ec9be5417ee44c96343d2347145585da1b1f94` in a network-enabled environment, confirm `git hash-object proxysolver`, apply the composed patch, and run the packet regression from that exact checkout.

## Next safe action

```text
git clone https://gitlab.mister-muffin.de/josch/mmdebstrap.git /tmp/mmdebstrap-unit12
cd /tmp/mmdebstrap-unit12
git checkout 77ec9be5417ee44c96343d2347145585da1b1f94
git hash-object proxysolver
patch --batch --forward -p1 -i /absolute/path/linux-fieldwork/upstream-packets/units/12-proxysolver-result-propagation/patches/0001-proxysolver-propagate-solver-results.patch
python3 /absolute/path/linux-fieldwork/upstream-packets/units/12-proxysolver-result-propagation/scripts/test_proxysolver_result_propagation.py
```

Expected pre-patch hash: `5cd51fab89104d30b8b12bff18a49d38d9be0003`. Record any mismatch before editing the patch. After the packet regression passes, select the smallest native gate by inspecting current `coverage.py`, `coverage.txt`, and `tests/`.

## Unresolved blockers

- technical: exact canonical source-byte comparison, patch application, and native-context execution;
- compatibility: human review of exact signal replay, POSIX dependency, and stdout-flush failure precedence;
- overlap: public views found none, while a complete authenticated Forgejo issue/PR search should be repeated before submission;
- environment or tooling: this execution environment cannot resolve the canonical host and the web reader did not deliver raw file/archive bytes;
- authority: controlled fork/branch creation and every upstream public action remain unauthorized.

## Files to read first

1. `README.md`
2. `HANDOFF.md`
3. `artifacts/2026-08-01-current-upstream-check.md`
4. `SOURCE_MAP.md`
5. `DEEP_DIVE.md`
6. `TESTS.md`
7. `DECISIONS.md`
8. #397 unit 12 and carriers #133/#134, #165/#166, #201, #207

## External-contact state

`false; none occurred`. Public pages were read only. No upstream account action or message was created.

## Do not repeat

- do not treat PR #166 as the canonical clean signal carrier; use merged PR #207 and retain #166 as development history;
- do not re-propose negative `SystemExit`; its 241/254 behavior is demonstrated;
- do not map to `128 + signal` unless upstream chooses normal-exit semantics explicitly;
- do not fold parent-interruption/process-group ownership into this unit without a boundary decision;
- do not classify the first local red run or the 2026-08-01 retrieval failures as product failures;
- do not treat matching file size and last-change history as an exact byte hash;
- do not contact upstream without explicit authorization.
