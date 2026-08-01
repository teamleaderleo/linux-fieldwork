# Decisions — unit 05

## 2026-08-01 — adopt event-order result precedence

Decision: retain the canonical order:

```text
captured host failure
> completed guest or protocol failure
> first cleanup-time signal
> first cleanup failure
> success
```

Reason: the host result is captured before cleanup, and the guest result is completed before `debvm-run` returns. A later cleanup signal reports cancellation after success while preserving an earlier authoritative failure.

Supersedes: the intermediate patch-3 policy `host > cleanup-time signal > guest > cleanup > success`.

Reopen trigger: upstream changes guest-result publication so the guest result remains provisional when host cleanup begins.

## 2026-08-01 — retain four ordered patches

Decision: package the candidate as four patches in the canonical review order.

Reason: each patch closes one distinct negative control, and each intermediate composition explains the next correction. A squashed patch would erase useful review and regression boundaries.

Reopen trigger: current upstream source diverges enough that the sequence becomes artificial or conflict-heavy. In that case, produce source-aligned commits preserving the same four logical steps or document a justified smaller composition.

## 2026-08-01 — retain PR #290 as fixture history only

Decision: record PR #290 in the source map without importing a fifth product patch.

Reason: its useful exact-boundary fixture repair was adopted by the later canonical #282 head. Its remaining generated-string assertion used an ambiguous substring and the branch was superseded.

Reopen trigger: a rebased upstream test harness recreates the omitted-recorder or function-alias defect.

## 2026-08-01 — treat equal published file size as a clue

Decision: record that Debian Sources lists version `1.5.7-3` `run_qemu.sh` at 2,029 bytes, matching the imported source size, while withholding a byte-identity claim.

Reason: file size alone cannot establish content identity.

Reopen trigger: live raw source becomes available; replace this observation with exact Git blob and SHA-256 comparison.

## 2026-08-01 — keep the unit ACTIVE

Decision: use disposition `ACTIVE`.

Reason: the internal composition, patch extraction, and local application receipt are complete. Current Salsa `master` identity, live application, upstream-native tests, and current-carrier search remain incomplete.

Transition to `READY FOR AUTHORIZATION` when:

- the exact live upstream base is recorded;
- the candidate applies or is rebased cleanly;
- focused and ordinary upstream gates pass on the exact candidate;
- current equivalent upstream work has been checked;
- the packet drafts match the final source delta;
- the branch survives cleanup and rerun.

## 2026-08-01 — preserve external-contact boundary

Decision: make no upstream contact and create no public upstream branch, issue, merge request, comment, review, email, or mailing-list post.

Reason: issue #397 authorizes internal technical work only. The user repeated the same boundary for this pass.

Reopen trigger: explicit authorization from the repository owner naming the permitted contact or publication action.

## 2026-08-01 — controlled fork remains unresolved

Decision: record `NEEDS FORK` and avoid creating one during this extraction pass.

Reason: this pass could complete the packet and local patch checks without a fork. Fork creation should serve a concrete rebase/test or publication need.

Reopen trigger: a runtime with canonical Salsa access is available and a controlled fork is required for internal candidate execution or explicitly authorized publication.
