# Decisions — unit 11

## 2026-08-01 — Select the group-delivery candidate

**Decision:** Retain PR #313's product mechanism: create a dedicated session/process group for each selected backend, send TERM to that group on parent-only SIGINT, wait the wrapper, diagnose, and exit 130.

**Reason:** It is the smallest candidate that fixes both status ownership and cancellation delivery for the tested responsive topologies.

**Supersedes:** immediate-child-only termination as a complete candidate.

## 2026-08-01 — Keep status 130 and group delivery in one upstream unit

**Decision:** Present the final source hunk as one patch instead of an ordered status-only patch followed by a group patch.

**Reason:** Upstream users observe one cancellation contract. Splitting would temporarily preserve a known survivor defect and complicate review without reducing the final source delta.

**Historical control retained:** PR #204 remains the status-only comparator in tests and explanation.

## 2026-08-01 — Keep the claim narrow

**Decision:** Claim complete settlement only for the executed TERM-responsive null, QEMU-wrapper, and passwordless-sudo models.

**Reason:** Group-wide signal delivery and arbitrary descendant quiescence are separate claims. Resistant, deferring, or group-escaping descendants remain outside the selected candidate.

## 2026-08-01 — Hold TERM-to-KILL escalation outside unit 11

**Decision:** Add no escalation, grace timeout, survivor scan, or repeated-SIGINT policy.

**Reason:** Issue #341 proved synthetic escalation sufficiency while supplying no real-backend necessity, proportional timeout, or acceptable state-loss evidence.

**Reopen trigger:** a real backend ignores or materially defers TERM, outlives its wrapper after group TERM, or demonstrates an operational repeated-SIGINT requirement.

## 2026-08-01 — Use canonical Forgejo as the proposed destination

**Decision:** Target the canonical `josch/mmdebstrap` Forgejo repository on branch `main`, using a controlled fork and pull request after authorization.

**Reason:** The project homepage, repository, issue tracker, and contributor instructions point there. Debian's Salsa repository remains relevant packaging context.

## 2026-08-01 — Require exact current-base execution

**Decision:** Require zero-fuzz packet-patch application and focused null/QEMU/sudo execution on canonical upstream commit `77ec9be5417ee44c96343d2347145585da1b1f94` before authorization readiness.

**Result:** Completed by workflow run `30689911760`. Canonical source identity, patch application, compilation, 6-control packet matrix, and 14-control refined topology matrix all passed twice.

## 2026-08-01 — Preserve the QEMU evidence refinement

**Decision:** Use PR #339 exact head `8253ab2ef6fed22b34fc5f5d6d20cda75c25e2c7` as the final topology carrier.

**Reason:** Its QEMU losing controls record Python SIGINT-handler entry before deliberate survivor release, removing the remaining ordering ambiguity without changing product source.

**Executed result:** refined QEMU test blob `0c2a050faf8e98320fc0c4fe4634d46bdf7f0dfa` passed in both complete canonical topology runs.

## 2026-08-01 — Treat broad system runs as limits, not blockers

**Decision:** Real QEMU/debvm, prepared-mirror coverage, non-Linux execution, and maintainer CI remain explicit evidence limits.

**Reason:** The selected source claim concerns parent-only SIGINT delivery and responsive processes inside one caller-owned group. Exact canonical wrapper controls distinguish that mechanism directly. Broader operations add environment coverage while leaving the source discriminator unchanged.

## 2026-08-01 — Promote to READY FOR AUTHORIZATION

**Decision:** Set unit 11 to `READY FOR AUTHORIZATION` after run `30689911760`.

**Basis:**

- canonical commit `77ec9be...` cloned and verified;
- canonical/imported `coverage.py` blob equality proven;
- packet patch applied with `--fuzz=0` and compiled twice;
- six packet controls passed twice;
- fourteen refined null/QEMU-wrapper/passwordless-sudo controls passed twice with no skips;
- cleanup and immediate rerun completed;
- polished upstream drafts and exact identities are present.

**Remaining decision:** authorize `SEND` with a controlled fork, or place the unit on `HOLD`.

## 2026-08-01 — No upstream contact

**Decision:** Create no public issue, pull request, review, email, or comment.

**Reason:** Issue #397 authorizes internal work only. External contact requires explicit authorization.

**Result:** no upstream contact occurred. Read-only cloning for exact source verification created no upstream interaction record.
