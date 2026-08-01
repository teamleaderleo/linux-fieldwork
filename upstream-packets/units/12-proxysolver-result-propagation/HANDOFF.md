# Current handoff

Updated: `2026-08-01 16:10 +08:00`  
Worker or variant: `GPT-5.6 Thinking`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-12-proxysolver-result-propagation` |
| Branch creation base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Pre-handoff technical head | `c98cfbb9e27a4d742757eb2d382dcaba69b5b99c` |
| Final packet branch tip | this HANDOFF update commit; exact SHA is recorded in issue #397 if a new checkpoint is posted |
| Canonical upstream | `https://gitlab.mister-muffin.de/josch/mmdebstrap`, `main` |
| Public upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94`, re-observed 2026-08-01 |
| Controlled fork | `teamleaderleo/mmdebstrap` |
| Fork default branch | `master` |
| Saved upstream branch | `linux-fieldwork/upstream-main-snapshot` |
| Unit-12 candidate branch | `NEEDS BRANCH`; none observed |
| Candidate head | `NEEDS BRANCH` |
| Fork `master` proxysolver | blob `5cd51fab89104d30b8b12bff18a49d38d9be0003` |
| Fork snapshot proxysolver | blob `5cd51fab89104d30b8b12bff18a49d38d9be0003` |
| Fork `master` coverage.txt | blob `be105dd37f44c54b51a6f02ff4358f18c2ce618c` |
| Composed candidate source | blob `13aef7109250a21bc7a23af6eaa7b235aef9c92c` |
| Composed source patch | `patches/0001-proxysolver-propagate-solver-results.patch`, SHA-256 `74819e72482afe00abc3d4c7678a4f91cdbef61f3e2519296755a3a9fa049c48` |
| Native test draft | `native-tests/proxysolver-result-propagation`, SHA-256 `3505be52c6feec272c3fc177fb49e7c19bb326167f2013944f0494b685b20dd5` |
| Native registration draft | `native-tests/coverage.txt.stanza` |
| Owning issue/carriers | #397 unit 12; #133/#134; #165/#166; #201; #207 |
| Latest source refresh | `artifacts/2026-08-01-current-upstream-check.md` |
| Latest native evidence | `artifacts/2026-08-01-native-gate-selection.md` |
| Latest placement evidence | `artifacts/2026-08-01-active-landing-scout.md` |

## Current bounded claim

The controlled GitHub fork closes the prior source-byte identity gate: both `master` and `linux-fieldwork/upstream-main-snapshot` contain exact `proxysolver` blob `5cd51fab89104d30b8b12bff18a49d38d9be0003`, matching the imported unit source.

Against that exact source, the composed candidate preserves success 0, propagates positive exit 7, preserves actual SIGTERM and SIGINT termination, unblocks inherited blocked SIGTERM, preserves stdout/dump bytes and inherited stderr, and leaves no fake solver PID alive. The project-shaped native test independently distinguishes the imported exit-7 defect and passes repeatedly against candidate blob `13aef7109250a21bc7a23af6eaa7b235aef9c92c`.

A candidate branch, exact fork application, exact `coverage.txt` integration patch, real `coverage.py` execution, and consumer regressions remain open.

## Work completed in the latest continuation

- acknowledged the user-created controlled fork and discovered its exact repository identity as `teamleaderleo/mmdebstrap`;
- listed existing branches and confirmed no unit-12 candidate branch exists;
- read `proxysolver` from fork `master` and `linux-fieldwork/upstream-main-snapshot`;
- verified both refs carry exact expected blob `5cd51fab89104d30b8b12bff18a49d38d9be0003`;
- read exact fork `coverage.txt` and recorded blob `be105dd37f44c54b51a6f02ff4358f18c2ce618c`;
- attempted a GitHub compare between fork `master` and the saved snapshot; GitHub reported no common ancestor, classified as branch/import topology rather than a target-file mismatch;
- scouted active, broader-maintainer landing zones for reusable unit-12 assets;
- ranked APT/apt-tests as the protocol owner, Debusine as the strongest active direct consumer, go-debos/debos as the strongest GitHub consumer, and autopkgtest as a secondary integration owner;
- documented why systemd/mkosi has high activity but weak direct fit;
- recorded the recommended protocol/implementation/consumer split in `artifacts/2026-08-01-active-landing-scout.md`;
- made no external contact or fork mutation.

## Placement conclusion

Use a layered route rather than looking for one replacement upstream:

1. **APT/apt-tests** — absorb the general EDSP/external-solver result contract and protocol-level regression.
2. **Controlled mmdebstrap fork** — carry the exact proxysolver implementation patch and native test.
3. **Debusine** — absorb a worker-task regression proving an mmdebstrap solver failure cannot become a successful environment task.
4. **go-debos/debos** — absorb a `MmdebstrapAction` failure-propagation regression and clearer underlying-result diagnostics.
5. **autopkgtest** — optional smoke test at the image/testbed creation boundary.

The exact Python patch should not be copied into APT, Debusine, debos, or autopkgtest unchanged. Those projects should receive tests or native implementation changes matching their ownership boundary.

## Complete packet paths

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
- `upstream-packets/units/12-proxysolver-result-propagation/artifacts/2026-08-01-active-landing-scout.md`

## Distinguishing observations

- `Popen.__exit__()` waits but does not turn child failure into wrapper failure.
- `SystemExit(-15)` and `SystemExit(-2)` produce ordinary statuses 241 and 254.
- exact self-signal replay preserved `-SIGTERM` and `-SIGINT` in packet and native-shaped execution.
- the inherited blocked-SIGTERM control passed because the candidate unblocks before replay.
- solver stderr remained inherited while stdout and dump stayed identical.
- imported baseline failed the native gate at `AssertionError: ('exit-7', 0, 7)`.
- candidate passed the native gate twice, then passed again after restoring it following the baseline negative control.
- fork `master` and saved snapshot have identical exact target-file blobs.
- the fork's exact `coverage.txt` is now available, so a real context-bearing native integration patch can be generated without guessing.
- Debusine has a first-class `MmDebstrap` task and recent task-specific changes.
- debos has a first-class `MmdebstrapAction` and recent merged work fixing silent-success and swallowed-error classes.
- APT owns EDSP and maintains an EDSP/EIPP-focused `apt-tests` repository.

## Gates completed

- historical ordinary and signal patches applied sequentially to imported blob: PASS, no fuzz/offset;
- composed patch generation and full diff review: PASS;
- local candidate compilation: PASS;
- packet five-test matrix: PASS in 14.097s;
- immediate packet rerun: PASS in 14.112s;
- simulated final repository layout: PASS in 13.536s;
- native-shaped candidate direct gate: PASS twice;
- imported baseline negative control: expected FAIL at exact exit-7 discriminator;
- restored candidate after negative control: PASS;
- native shell syntax: PASS;
- cleanup/PID disappearance assertions: PASS;
- exact fork target-file verification on two refs: PASS, blob `5cd51fab...`;
- exact fork `coverage.txt` retrieval: PASS;
- active landing-zone scout: COMPLETE as read-only assessment.

## Red or neutral runs classified

- first packet script attempt: fixture path packaging; 0 product tests ran.
- historical PR #166 malformed patch head: patch packaging, superseded by green heads.
- native baseline status 1 at `('exit-7', 0, 7)`: expected negative control.
- canonical Forgejo clone/raw retrieval failures: environment DNS/cache boundary before repository access.
- `shellcheck` and `shfmt`: unavailable optional tooling.
- fork branch comparison returned “No common ancestor”: branch/import topology; exact target blobs match.

## Cleanup state

All dynamic tests used disposable directories and removed them. Every fake solver PID was confirmed gone. No package install, mount, socket, upstream fork creation, candidate branch creation, public issue, pull request, discussion, comment, email, or other external contact occurred in the latest continuation. Intentional retained state consists of the Linux Fieldwork unit branch and packet files. The pre-existing controlled fork was read only.

## First incomplete step

Generate a native integration patch against the exact fork bytes, then apply both source and native-test patches on a dedicated unit-12 candidate branch and run the focused gates.

## Next safe technical work

Read-only/internal drafting can proceed without contact:

1. inspect exact fork `coverage.py` and the relevant `tests/` conventions;
2. generate a patch adding `tests/proxysolver-result-propagation` and the exact-context `coverage.txt` stanza;
3. inspect Debusine `MmDebstrap` task tests and draft a consumer regression in this workspace;
4. inspect debos `MmdebstrapAction` tests and draft a consumer regression in this workspace;
5. decide whether consumer tests require exact signal identity or only nonzero task failure.

After explicit authorization to mutate the controlled fork:

```text
create branch linux-fieldwork/unit-12-proxysolver-result-propagation
apply patches/0001-proxysolver-propagate-solver-results.patch
apply the generated native integration patch
python3 -m py_compile proxysolver
python3 /path/to/test_proxysolver_result_propagation.py
CMD=./mmdebstrap ./coverage.py proxysolver-result-propagation
```

## Unresolved blockers

- candidate: no dedicated unit-12 branch or candidate head;
- native integration: exact `coverage.py`/test-convention review and generated context-bearing patch;
- execution: focused test has not run through the real fork `coverage.py` harness;
- consumer placement: Debusine and debos regression drafts have not yet been produced;
- compatibility: human review of exact signal replay, POSIX dependency, and stdout-flush failure precedence;
- overlap: full authenticated canonical Forgejo issue/PR search remains pending before any submission;
- authority: external messages/submissions remain unauthorized; controlled-fork branch mutation is held pending explicit instruction.

## Files to read first

1. `HANDOFF.md`
2. `artifacts/2026-08-01-active-landing-scout.md`
3. `artifacts/2026-08-01-native-gate-selection.md`
4. `TESTS.md`
5. `native-tests/proxysolver-result-propagation`
6. `native-tests/coverage.txt.stanza`
7. `patches/0001-proxysolver-propagate-solver-results.patch`
8. `DECISIONS.md`
9. #397 and carriers #133/#134, #165/#166, #201, #207

## External-contact state

`false; none occurred`. Public pages and the user's controlled fork were read only.

## Do not repeat

- do not treat PR #166 as the canonical clean signal carrier; use merged PR #207;
- do not re-propose negative `SystemExit` or default to `128 + signal`;
- do not widen into parent-interruption/process-group ownership without a boundary decision;
- do not classify fixture failures, the baseline negative control, retrieval failures, or no-common-ancestor topology as candidate product failures;
- do not treat high activity alone as technical fit;
- do not transplant the mmdebstrap Python patch unchanged into consumer projects;
- do not contact upstream or candidate projects without explicit authorization.