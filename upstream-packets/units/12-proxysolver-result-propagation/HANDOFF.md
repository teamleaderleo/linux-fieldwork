# Current handoff

Updated: `2026-08-01 15:48 +08:00`  
Worker or variant: `GPT-5.6 Thinking`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-12-proxysolver-result-propagation` |
| Branch creation base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Pre-handoff technical head | `9fc1066cbd7e3a70783440e8d0471e7dbe7934ef` |
| Final packet branch tip | this HANDOFF update commit; exact SHA is recorded in the issue #397 `UNIT CHECKPOINT` |
| Upstream base repository/branch | `https://gitlab.mister-muffin.de/josch/mmdebstrap`, `main` |
| Public upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94`, re-observed 2026-08-01 |
| Candidate fork/branch | `NEEDS FORK` / `NEEDS BRANCH` |
| Candidate head | `NEEDS BRANCH` |
| Imported source | blob `5cd51fab89104d30b8b12bff18a49d38d9be0003`, 1,643 bytes |
| Composed candidate source | blob `13aef7109250a21bc7a23af6eaa7b235aef9c92c` |
| Composed source patch | `patches/0001-proxysolver-propagate-solver-results.patch`, SHA-256 `74819e72482afe00abc3d4c7678a4f91cdbef61f3e2519296755a3a9fa049c48` |
| Native test draft | `native-tests/proxysolver-result-propagation`, SHA-256 `3505be52c6feec272c3fc177fb49e7c19bb326167f2013944f0494b685b20dd5` |
| Native registration draft | `native-tests/coverage.txt.stanza` |
| Owning issue/carriers | #397 unit 12; #133/#134; #165/#166; #201; #207 |
| Latest hosted evidence | PR #207 CI `30579889333`; PR #201 current-main run `30579465025` |
| Latest source refresh | `artifacts/2026-08-01-current-upstream-check.md` |
| Latest native-gate evidence | `artifacts/2026-08-01-native-gate-selection.md` |

## Current bounded claim

Against exact imported source blob `5cd51fab89104d30b8b12bff18a49d38d9be0003`, the composed source preserves success 0, propagates positive exit 7, preserves actual SIGTERM and SIGINT termination, unblocks inherited blocked SIGTERM, preserves stdout/dump bytes and inherited stderr, and leaves no fake solver PID alive. The new project-shaped native test independently distinguishes the imported exit-7 defect and passes repeatedly against composed candidate blob `13aef7109250a21bc7a23af6eaa7b235aef9c92c`. Current public metadata continues to corroborate the imported source identity. Exact canonical raw-byte comparison, canonical patch application, and real `coverage.py` execution remain open.

## Work completed in this continuation

- resumed the existing unit branch at `c09f40335ee6c21fd9f193c7df6e7740c7eb3899` and read the current handoff;
- retried the canonical clone and again observed DNS failure before repository access;
- inspected the current public mmdebstrap test harness boundary: `coverage.py` copies source-tree `proxysolver` into `shared/proxysolver`, reads `coverage.txt`, requires the `coverage.txt` and `tests/` name sets to agree, and supports selecting a named test;
- selected the smallest upstream-shaped placement: one `tests/proxysolver-result-propagation` shell test plus one `coverage.txt` stanza;
- wrote the complete copy-ready native test under `native-tests/` and its registration under `native-tests/coverage.txt.stanza`;
- validated the native-shaped test directly against the exact composed candidate twice, against the imported baseline as an expected negative control, and against the restored candidate once more;
- ran `/bin/sh -n` on the native test and `python3 -m py_compile` on the composed source;
- recorded missing `shellcheck` and `shfmt` as optional tooling gaps;
- documented exact commands, identities, result table, baseline traceback, cleanup, intended focused harness command, and remaining discriminator in `artifacts/2026-08-01-native-gate-selection.md`;
- updated `TESTS.md` and `DECISIONS.md` with the new evidence and integration boundary;
- retained the unit as `ACTIVE` and prepared this complete handoff.

## Changed paths in this continuation

Added:

- `upstream-packets/units/12-proxysolver-result-propagation/native-tests/proxysolver-result-propagation`
- `upstream-packets/units/12-proxysolver-result-propagation/native-tests/coverage.txt.stanza`
- `upstream-packets/units/12-proxysolver-result-propagation/artifacts/2026-08-01-native-gate-selection.md`

Updated:

- `upstream-packets/units/12-proxysolver-result-propagation/TESTS.md`
- `upstream-packets/units/12-proxysolver-result-propagation/DECISIONS.md`
- `upstream-packets/units/12-proxysolver-result-propagation/HANDOFF.md`

Complete packet paths:

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
- `upstream-packets/units/12-proxysolver-result-propagation/native-tests/proxysolver-result-propagation`
- `upstream-packets/units/12-proxysolver-result-propagation/native-tests/coverage.txt.stanza`
- `upstream-packets/units/12-proxysolver-result-propagation/artifacts/2026-08-01-current-upstream-check.md`
- `upstream-packets/units/12-proxysolver-result-propagation/artifacts/2026-08-01-native-gate-selection.md`

## Distinguishing observations

- `Popen.__exit__()` waits but does not turn child failure into wrapper failure.
- `SystemExit(-15)` and `SystemExit(-2)` produce ordinary statuses 241 and 254.
- exact self-signal replay preserved `-SIGTERM` and `-SIGINT` in both packet and native-shaped execution.
- the inherited blocked-SIGTERM control passed because the candidate unblocks before replay.
- solver stderr remained inherited while stdout and dump stayed identical.
- the imported baseline failed the native-shaped gate at `AssertionError: ('exit-7', 0, 7)`, proving the test independently detects the ordinary false-success defect.
- the candidate passed the native-shaped gate twice, then passed again after restoring it following the baseline negative control.
- the upstream harness already provides the right handoff boundary through `shared/proxysolver`; the test requires no real APT solver or package installation.
- exact `coverage.txt` context remains unavailable, so a context-bearing native integration patch would currently guess at upstream bytes.
- the public canonical repository still displays main at `77ec9be5417ee44c96343d2347145585da1b1f94` and `proxysolver` last changed in 2021.
- Debian Sources displays current forky/sid `mmdebstrap 1.5.7-3` with a 1,643-byte root `proxysolver`, matching the imported file size.
- matching history and size corroborate identity; byte retrieval plus `git hash-object` remains the exact source gate.

## Gates completed

- sequential application of historical ordinary and signal patches to the imported blob: PASS, no fuzz/offset;
- composed patch generation and complete diff review: PASS;
- local compilation of composed source: PASS;
- packet five-test matrix, first successful run: 5 tests in 14.097s, PASS;
- immediate packet rerun: 5 tests in 14.112s, PASS;
- simulated final repository layout: 5 tests in 13.536s, PASS;
- packet cleanup/PID disappearance assertions: PASS;
- native-shaped candidate direct gate: PASS twice;
- native-shaped imported baseline negative control: expected FAIL, status 1, exact exit-7 discriminator;
- restored candidate direct gate after baseline control: PASS;
- native test shell syntax: PASS;
- public issue/pull-request overlap check: no equivalent surfaced;
- 2026-08-01 current public repository/package corroboration: PASS as metadata evidence only.

## Red or neutral runs classified

- first packet script attempt: fixture path packaging; historical status patch expected `upstream/mmdebstrap/proxysolver`; 0 product tests ran. Disposable layout corrected.
- historical PR #166 malformed patch head `f57b43b32d78ad5dcd58039c816907fe7abe27de`: patch packaging, superseded by green heads.
- native baseline status 1 at `('exit-7', 0, 7)`: expected negative control, demonstrating the imported defect.
- 2026-08-01 canonical clone retry: `Could not resolve host`; environment DNS/network failure before repository access.
- canonical raw/archive and Debian source-file retrieval through the web reader: cache-miss/safe-URL tool boundary before file bytes; no product or patch behavior ran.
- `shellcheck` and `shfmt`: commands unavailable; optional tooling gap, no product execution.

## Cleanup state

All packet matrix roots used temporary directories and were removed. The native test owns a `mktemp -d` root and removes it through its shell trap. Every fake solver PID was confirmed gone. The direct harness fixture `/tmp/unit12-native-gate` was local-only test scaffolding and contains no credential or upstream checkout. Failed network commands created no checkout or repository files. No package operation, mount, socket, upstream fork, public issue, pull request, comment, email, or other upstream contact occurred. Intentional retained state consists only of the Linux Fieldwork branch, packet files, source patch, packet regression, native-test drafts, evidence artifacts, and internal #397 checkpoints.

## First incomplete step

Materialize canonical upstream main commit `77ec9be5417ee44c96343d2347145585da1b1f94` in a network-enabled environment, confirm `git hash-object proxysolver`, apply the composed source patch, and run both the packet regression and the native-shaped direct gate from that exact checkout.

## Next safe action

```text
git clone https://gitlab.mister-muffin.de/josch/mmdebstrap.git /tmp/mmdebstrap-unit12
cd /tmp/mmdebstrap-unit12
git checkout 77ec9be5417ee44c96343d2347145585da1b1f94
git hash-object proxysolver
patch --batch --forward -p1 -i /absolute/path/linux-fieldwork/upstream-packets/units/12-proxysolver-result-propagation/patches/0001-proxysolver-propagate-solver-results.patch
python3 /absolute/path/linux-fieldwork/upstream-packets/units/12-proxysolver-result-propagation/scripts/test_proxysolver_result_propagation.py
mkdir -p shared
cp proxysolver shared/proxysolver
sh /absolute/path/linux-fieldwork/upstream-packets/units/12-proxysolver-result-propagation/native-tests/proxysolver-result-propagation
```

Expected pre-patch hash: `5cd51fab89104d30b8b12bff18a49d38d9be0003`. Record any mismatch before editing the patch.

After the direct gates pass:

1. copy the native draft to `tests/proxysolver-result-propagation`;
2. place `Test: proxysolver-result-propagation` in exact current `coverage.txt` context;
3. generate and review the real native integration patch;
4. run the normal project prerequisites and `CMD=./mmdebstrap ./coverage.py proxysolver-result-propagation`;
5. run `shellcheck`/`shfmt` if upstream uses or provides them.

## Unresolved blockers

- technical: exact canonical source-byte comparison, source patch application, and exact-checkout execution;
- native integration: exact `coverage.txt` placement, generated native test patch, and focused `coverage.py` execution;
- compatibility: human review of exact signal replay, POSIX dependency, and stdout-flush failure precedence;
- overlap: public views found none, while a complete authenticated Forgejo issue/PR search should be repeated before submission;
- environment or tooling: this execution environment cannot resolve the canonical host; `shellcheck` and `shfmt` are absent;
- authority: controlled fork/branch creation and every upstream public action remain unauthorized.

## Files to read first

1. `HANDOFF.md`
2. `artifacts/2026-08-01-native-gate-selection.md`
3. `TESTS.md`
4. `native-tests/proxysolver-result-propagation`
5. `native-tests/coverage.txt.stanza`
6. `artifacts/2026-08-01-current-upstream-check.md`
7. `README.md`
8. `SOURCE_MAP.md`
9. `DEEP_DIVE.md`
10. `DECISIONS.md`
11. #397 unit 12 and carriers #133/#134, #165/#166, #201, #207

## External-contact state

`false; none occurred`. Public pages were read only. No upstream account action or message was created.

## Do not repeat

- do not treat PR #166 as the canonical clean signal carrier; use merged PR #207 and retain #166 as development history;
- do not re-propose negative `SystemExit`; its 241/254 behavior is demonstrated;
- do not map to `128 + signal` unless upstream chooses normal-exit semantics explicitly;
- do not fold parent-interruption/process-group ownership into this unit without a boundary decision;
- do not classify the packet fixture red run, expected native baseline failure, or retrieval failures as candidate product failures;
- do not treat matching file size and last-change history as an exact byte hash;
- do not invent a `coverage.txt` context hunk before exact canonical bytes are available;
- do not contact upstream without explicit authorization.
