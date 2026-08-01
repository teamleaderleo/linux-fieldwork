# Decisions — unit 11

## 2026-08-01 — Select the group-delivery candidate

**Decision:** Start each selected backend in a dedicated session/process group, send TERM to that group on parent-only SIGINT, wait for the wrapper, diagnose, and exit 130.

**Reason:** This is the smallest candidate that fixes both status ownership and cancellation delivery for the tested responsive topologies.

**Supersedes:** immediate-child-only termination as a complete candidate.

## 2026-08-01 — Keep status 130 and group delivery in one source unit

**Decision:** Present one source hunk rather than a status-only patch followed by a group patch.

**Reason:** The observable contract is one cancellation behavior. Splitting would temporarily preserve a known survivor defect without reducing the final source delta.

**Historical control:** PR #204 remains the status-only comparator.

## 2026-08-01 — Keep the claim narrow

**Decision:** Claim settlement only for executed TERM-responsive null, QEMU-wrapper, and passwordless-sudo models that remain in the owned group.

**Reason:** Group-wide signal delivery and arbitrary descendant quiescence are separate claims.

## 2026-08-01 — Hold escalation outside the unit

**Decision:** Add no TERM-to-KILL escalation, grace timeout, survivor scan, or repeated-SIGINT policy.

**Reason:** Issue #341 proved synthetic escalation sufficiency without real-backend necessity, a proportional timeout, or acceptable state-loss evidence.

**Reopen trigger:** a real backend ignores or materially defers TERM, outlives its wrapper, or demonstrates an operational repeated-SIGINT requirement.

## 2026-08-01 — Use canonical Forgejo as the destination

**Decision:** Target `josch/mmdebstrap` Forgejo `main`. Treat Salsa as Debian packaging context.

**Delivery method:** controlled fork and pull request after explicit authorization.

## 2026-08-01 — Require exact current-base execution

**Decision:** Require zero-fuzz patch application and focused null/QEMU/sudo execution on canonical commit `77ec9be5417ee44c96343d2347145585da1b1f94`.

**Result:** run `30689911760` passed canonical source identity, patch application, compilation, 6/6 twice, and 14/14 twice.

## 2026-08-01 — Preserve the QEMU evidence refinement

**Decision:** Use PR #339 head `8253ab2ef6fed22b34fc5f5d6d20cda75c25e2c7` as the final QEMU topology carrier.

**Reason:** It records Python SIGINT-handler entry before deliberate survivor release, removing the remaining causal-order ambiguity.

## 2026-08-01 — Materialize the exact clean target source

**Decision:** Create the controlled branch `linux-fieldwork/unit-11-coverage-backend-cancellation` from exact canonical base `77ec9be...`.

**Result:** clean head `431614b3af58ba4f70791aa1d42cf5b71c965dd2`, candidate blob `9e31f21cf37228257b5e0705d9ecb13b7a66e40f`, `coverage.py` only, 8 additions and 3 deletions.

**Review surface:** `teamleaderleo/mmdebstrap#4`.

## 2026-08-01 — Require controlled target-head equivalence and execution

**Decision:** Prove that the clean target source equals the zero-fuzz packet-patch result and rerun focused controls on the controlled target repository.

**Result:** run `30706007117` passed:

- exact identity and byte equivalence;
- candidate compilation;
- 6/6 twice;
- 14/14 twice, no skips;
- actual sudo controls;
- cleanup and immediate rerun.

**Artifacts:** `8820336271` and `8820337503` with retained SHA-256 digests.

## 2026-08-01 — Use a bounded project-native ordinary source slice

**Decision:** Run native `coverage.sh help man version` twice rather than treating the full prepared-mirror 283-entry matrix as the default closeout gate.

**Reason:** The source change belongs to the outer signal-ownership boundary. The bounded slice exercises the real source checks, `coverage.py`, `run_null.sh`, and command-interface scenarios without package/mirror side effects. The full matrix adds environment breadth without a sharper parent-only signal discriminator.

**Result:** run `30706633832`, job `91386769087`, passed 3/3 twice.

**Baseline exception:** exact canonical `tarfilter` blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` has a pre-existing Black failure. The gate isolates only that blob and retains real Black 26.5.1 enforcement for all other checked Python source.

**Artifact:** `8820528312`, SHA-256 `13986015aebc37cd3624f5114baa2a599f3c3dccb01e838b367287b2585b8f55`.

**Reopen trigger:** eligible review or maintainer policy requires the full prepared-mirror matrix.

## 2026-08-01 — Keep the clean contribution source-only

**Decision:** Do not add a default recursive target-native regression. Keep `coverage.py` as the sole changed file and retain the exact deterministic external reproducer in the packet.

**Reason:** Every non-dot target `tests/` entry is a `coverage.txt`-indexed shell-template package scenario. Testing the outer coverage orchestrator from inside the same harness would require a recursive miniature coverage tree substantially larger than the source correction.

**Reopen triggers:** eligible review requires a native regression, upstream policy requires one, or a smaller stable self-test surface is identified.

## 2026-08-01 — Transfer runner evidence and keep the clean branch uncontaminated

**Decision:** Close internal runner PRs #2 and #3 without merge after transferring exact receipts.

**Reason:** Execution workflows do not belong in the public-shaped source diff.

**Result:** clean branch remains one file. Runner branches and runs remain exact evidence.

## 2026-08-01 — Treat broad execution as visible limits

**Decision:** Keep real QEMU/debvm package execution, full prepared-mirror coverage, direct `/dev/tty`, non-Linux execution, and public maintainer CI as explicit evidence limits.

**Reason:** These do not contradict the selected responsive-topology result. Independent review may still require one before authorization.

## 2026-08-01 — Promote the clean diff to independent review

**Decision:** Mark `teamleaderleo/mmdebstrap#4` ready for independent review after complete same-account self-review found no bounded-claim defect.

**Remaining gate:** eligible non-author complete-diff acceptance. Same-account review is not sufficient.

## 2026-08-01 — Maintain READY FOR AUTHORIZATION under issue #397

**Decision:** Keep unit 11 at `READY FOR AUTHORIZATION`.

**Basis:** canonical and controlled source identities, focused target execution, ordinary source execution, cleanup/rerun, source-only decision, clean diff, drafts, and receipts are complete.

**Pre-publication requirements:** independent acceptance, refreshed overlap/policy checks, and explicit authority.

## 2026-08-01 — No canonical-upstream contact

**Decision:** Create no canonical-upstream issue, pull request, review, email, or comment.

**Result:** controlled-fork branches and internal PRs only. No public upstream interaction occurred.
