# Current handoff

Updated: `2026-07-31 17:02 PDT`  
Worker or variant: `ChatGPT`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-12-proxysolver-result-propagation` |
| Branch creation base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Final packet branch tip | this HANDOFF finalization commit; exact SHA is recorded in the issue #397 UNIT CHECKPOINT |
| Upstream base repository/branch | `https://gitlab.mister-muffin.de/josch/mmdebstrap`, `main` |
| Public upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` observed 2026-07-31 |
| Candidate fork/branch | `NEEDS FORK` / `NEEDS BRANCH` |
| Candidate head | `NEEDS BRANCH` |
| Imported source | blob `5cd51fab89104d30b8b12bff18a49d38d9be0003` |
| Composed patch | `patches/0001-proxysolver-propagate-solver-results.patch`, SHA-256 `74819e72482afe00abc3d4c7678a4f91cdbef61f3e2519296755a3a9fa049c48` |
| Owning issue/carriers | #397 unit 12; #133/#134; #165/#166; #201; #207 |
| Latest hosted evidence | PR #207 CI `30579889333`; PR #201 current-main run `30579465025` |

## Current bounded claim

Against exact imported source blob `5cd51fab89104d30b8b12bff18a49d38d9be0003`, the composed patch preserves success 0, propagates positive exit 7, preserves actual SIGTERM and SIGINT termination, unblocks inherited blocked SIGTERM, preserves stdout/dump bytes and inherited stderr, and leaves no fake solver PID alive. Current-upstream checkout and native-suite conclusions remain open.

## Work completed in this pass

- read issue #397, packet README/index/templates, and the proxysolver carrier chain;
- read workflow carrier PR #398;
- claimed unit 12 internally and created its canonical branch;
- reconciled ordinary-status issue/PR #133/#134;
- reconciled signal issue/development #165/#166;
- reconciled current-main execution carrier #201 and clean canonical evidence PR #207;
- refreshed public upstream main, issue overlap, package version, and contribution-path observations without contacting upstream;
- composed the two source repairs into one upstream-root patch;
- added a packet-specific regression with SIGTERM, SIGINT, inherited blocked SIGTERM, stderr, output/dump, success/failure, source, and child-cleanup controls;
- ran the matrix twice and once from a simulated final repository layout;
- wrote the full packet, decisions, upstream draft, and this handoff.

## Changed paths

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

## Distinguishing observations

- `Popen.__exit__()` waits but does not turn child failure into wrapper failure.
- `SystemExit(-15)` and `SystemExit(-2)` produce ordinary statuses 241 and 254.
- exact self-signal replay preserved `-SIGTERM` and `-SIGINT` in the expanded matrix.
- the inherited blocked-SIGTERM control passed because the candidate unblocks before replay.
- solver stderr remained inherited while stdout and dump stayed identical.
- the public upstream listing says `proxysolver` last changed in 2021, while main currently points at `77ec9be5417ee44c96343d2347145585da1b1f94`.

## Gates completed

- sequential application of historical ordinary and signal patches to the imported blob: PASS, no fuzz/offset;
- composed patch generation and complete diff review: PASS;
- local compilation of composed source: PASS;
- packet five-test matrix, first successful run: 5 tests in 14.097s, PASS;
- immediate rerun: 5 tests in 14.112s, PASS;
- simulated final repository layout: 5 tests in 13.536s, PASS;
- cleanup/PID disappearance assertions: PASS;
- public issue/pull-request overlap search: no equivalent surfaced.

## Red or neutral runs classified

- first packet script attempt: fixture path packaging; historical status patch expected `upstream/mmdebstrap/proxysolver`; 0 product tests ran. Disposable layout corrected.
- historical PR #166 malformed patch head `f57b43b32d78ad5dcd58039c816907fe7abe27de`: patch packaging, superseded by green heads.

## Cleanup state

All local test roots used temporary directories and were removed. Every fake solver PID was confirmed gone. No package operation, mount, socket, external network action, imported source edit, public issue, pull request, comment, email, or other upstream contact occurred. Intentional retained state consists only of the Linux Fieldwork branch, packet, patch, script, and internal #397 checkpoint.

## First incomplete step

Materialize canonical upstream main commit `77ec9be5417ee44c96343d2347145585da1b1f94`, confirm `git hash-object proxysolver`, apply the composed patch, and run the packet regression from that exact checkout.

## Next safe action

```text
git clone https://gitlab.mister-muffin.de/josch/mmdebstrap.git /tmp/mmdebstrap-unit12
cd /tmp/mmdebstrap-unit12
git checkout 77ec9be5417ee44c96343d2347145585da1b1f94
git hash-object proxysolver
patch --batch --forward -p1 -i /absolute/path/linux-fieldwork/upstream-packets/units/12-proxysolver-result-propagation/patches/0001-proxysolver-propagate-solver-results.patch
python3 /absolute/path/linux-fieldwork/upstream-packets/units/12-proxysolver-result-propagation/scripts/test_proxysolver_result_propagation.py
```

Expected pre-patch hash: `5cd51fab89104d30b8b12bff18a49d38d9be0003`. Record any mismatch before editing the patch.

## Unresolved blockers

- technical: exact upstream checkout application and native-context execution;
- compatibility: human review of exact signal replay, POSIX dependency, and stdout-flush failure precedence;
- overlap: public search found none, while a complete authenticated Forgejo search should be repeated before submission;
- environment or tooling: this pass lacked clone/raw-file access to the external Forgejo repository;
- authority: external contact remains unauthorized.

## Files to read first

1. `README.md`
2. `SOURCE_MAP.md`
3. `DEEP_DIVE.md`
4. `TESTS.md`
5. `DECISIONS.md`
6. #397 unit 12 and carriers #133/#134, #165/#166, #201, #207

## External-contact state

`false; none occurred`. Public pages were read only. No upstream account action or message was created.

## Do not repeat

- do not treat PR #166 as the canonical clean signal carrier; use merged PR #207 and retain #166 as development history;
- do not re-propose negative `SystemExit`; its 241/254 behavior is demonstrated;
- do not map to `128 + signal` unless upstream chooses normal-exit semantics explicitly;
- do not fold parent-interruption/process-group ownership into this unit without a boundary decision;
- do not classify the first local red run as a product failure;
- do not contact upstream without explicit authorization.
