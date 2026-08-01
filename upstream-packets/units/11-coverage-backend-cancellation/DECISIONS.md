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

**Reason:** Group-wide signal delivery and arbitrary descendant quiescence are separate claims. Resistant, deferring, or group-escaping descendants were outside the selected candidate.

## 2026-08-01 — Hold TERM-to-KILL escalation outside unit 11

**Decision:** Add no escalation, grace timeout, survivor scan, or repeated-SIGINT policy.

**Reason:** Issue #341 proved synthetic escalation sufficiency while supplying no real-backend necessity, proportional timeout, or acceptable state-loss evidence.

**Reopen trigger:** a real backend ignores or materially defers TERM, outlives its wrapper after group TERM, or demonstrates an operational repeated-SIGINT requirement.

## 2026-08-01 — Use canonical Forgejo as the proposed destination

**Decision:** Target the canonical `josch/mmdebstrap` Forgejo repository on branch `main`, using a controlled fork and pull request after authorization.

**Reason:** The project homepage, repository, issue tracker, and contributor instructions point there. Debian's Salsa repository remains relevant packaging context.

**Current blocker:** `NEEDS FORK` plus explicit external-contact authorization.

## 2026-08-01 — Rebase before requesting authorization

**Decision:** Keep state `ACTIVE` until the retained patch applies with zero fuzz and the focused matrix runs on current upstream head `77ec9be5417ee44c96343d2347145585da1b1f94`.

**Reason:** Historical Linux Fieldwork receipts establish mechanism behavior, while upstream submission requires an exact current-base candidate and current execution receipt.

## 2026-08-01 — Preserve the QEMU evidence refinement

**Decision:** Treat PR #339 as the preferred QEMU negative-control form when porting tests.

**Reason:** It records handler entry before deliberate survivor release, removing an ordering ambiguity without changing product source.

## 2026-08-01 — No upstream contact

**Decision:** Create no public issue, pull request, review, email, or comment.

**Reason:** Issue #397 authorizes internal work only. External contact requires explicit authorization.
