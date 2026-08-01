# Decisions — unit 05

## 2026-08-01 — preserve event-order result precedence

Decision:

```text
captured host failure
> completed guest or protocol failure
> first cleanup-time signal
> first cleanup failure
> success
```

Reason: host and completed guest outcomes become authoritative before ordinary cleanup signals and cleanup failures.

Reopen trigger: upstream changes guest-result publication so it remains provisional when host cleanup begins.

## 2026-08-01 — expand the canonical candidate to five ordered commits

Decision: the controlled candidate is the five-commit head `6efe6945f9f89cff57fe84086ede7bda747c3879`, rather than the historical four-commit head `457095c6f89655ab12b7055307f519e71bb0dbca`.

Reason: complete-diff adjacent-context review found two deterministic handler-entry windows in the four-commit source:

- TERM followed by INT before explicit-handler trap replacement returned 130 instead of retaining 143;
- completed guest failure 1 followed by TERM before ordinary-cleanup recorder installation returned 143 instead of 1.

Patch 5 closes both windows and preserves all previous controls.

Reopen trigger: canonical-upstream source alignment proves a smaller mechanism closes the same windows with equal or stronger evidence.

## 2026-08-01 — disable overlapping signals in the trap action

Decision: use trap actions that run `trap "" INT TERM` before entering explicit or recorder handlers.

Reason: disabling overlap inside the handler body leaves at least one shell command before the transition. A deterministic widened fixture proved that a second signal can enter there and replace first-signal ownership.

Rejected: another top-of-function assignment or delayed trap transition.

## 2026-08-01 — mark ordinary cleanup with the status-capture command

Decision:

```sh
rv=$? cleanup_phase=exit
```

Reason: an assignment-only shell command can capture the incoming result and expose ordinary-cleanup phase without an intervening command. A signal selected immediately afterward can be routed back into the ordinary-cleanup recorder path.

Reopen trigger: target shell portability review rejects this POSIX assignment-only use or current upstream supports a clearer source-aligned transition with the same control.

## 2026-08-01 — retain early cleanup signals and return to ordinary cleanup

Decision: when `cleanup_signal()` sees `cleanup_phase=exit`, record the first signal and return instead of beginning explicit-signal finalization.

Reason: this preserves completed host/guest ownership, allows ordinary cleanup to continue, and lets later recorder traps retain first-writer semantics.

## 2026-08-01 — keep five review boundaries

Decision: retain five logical patches in the packet.

Reason: each patch has a distinct losing control. Patch 5 is a complete-diff repair class—handler transition atomicity—rather than a prose-only cleanup.

A canonical rebase may restack commits when source context requires it, but the five mechanisms and controls must remain reviewable.

## 2026-08-01 — classify local harness interruptions as fixture failures

Decision: discard two preliminary harness results before the authoritative run.

Reasons:

1. the first harness waited for a cleanup barrier before sending the signal that enters cleanup;
2. the second expected ordinary baseline EXIT cleanup to re-enter, while re-entry belongs to the explicit-signal baseline path.

Product code remained unchanged. The corrected matrix passed 58/58.

## 2026-08-01 — retain PR #290 as fixture history only

Decision: PR #290 contributes fixture lessons, not a product patch.

Reason: its exact-boundary extraction repair was adopted by later canonical tests; its product state was superseded.

## 2026-08-01 — use disposition HOLD

Decision: set the unit to `HOLD` with two named authoritative blockers:

1. current canonical Salsa base/overlap reconciliation;
2. current upstream-native QEMU-classified execution on the exact rebased candidate.

Reason: the controlled candidate and reduced evidence are technically complete enough to identify the next decision, but issue #397 forbids `READY FOR AUTHORIZATION` until canonical-upstream identity, overlap, and native tests are recorded.

This HOLD assigns no task to the user. Resume through repository or hosted execution when those capabilities are available.

## 2026-08-01 — preserve external-contact boundary

Decision: create no upstream issue, merge request, comment, review, email, or mailing-list post.

Reason: issue #397 authorizes internal technical work only. No explicit unit-05 publication authorization exists.

Reopen trigger: repository owner explicitly authorizes a named external action and destination.
