# Decisions

## D1 — Use PR #195 as the sole source carrier

**Decision:** Extract merged PR #195, while retaining PR #172 and PR #192 as mechanism evidence.

**Reason:** The focused patches overlap in cleanup and trap code. PR #195 contains the reviewed composition, HUP behavior, cleanup precedence, root-parent policy, post-publication behavior, reruns, and trailing-slash repair.

## D2 — Submit one patch

**Decision:** Package the behavior as one upstream patch and one pull request.

**Reason:** Publication ownership and signal/cleanup ownership share the same lifecycle. Splitting them recreates an ambiguous conflict resolution and weakens the combined failure/signal guarantees.

## D3 — Regenerate hunk coordinates

**Decision:** Replace sliced-tail hunk coordinates with complete-file coordinates and omit stale internal blob index metadata.

**Reason:** The retained patch began at `@@ -1...` for code at full-source line 318 and therefore depended on an offset. The upstream-ready gate explicitly requires no fuzz and no offsets.

## D4 — Keep root-parent refusal

**Decision:** Preserve PR #195's refusal of a destination whose resolved parent is `/`.

**Reason:** This is the final composed contract and supersedes PR #192's earlier compatibility choice. Changing it requires a new compatibility decision and test matrix.

## D5 — Keep post-publication residue diagnostic

**Decision:** Warn and retain unexpected residue after successful rename.

**Reason:** Recursive deletion after the commit point could destroy unknown state. Publication truth remains successful, with residue available for diagnosis.

## D6 — Keep signal forwarding outside this unit

**Decision:** Preserve terminating wrapper semantics after foreground return without adding child PID ownership, forwarding, or escalation.

**Reason:** Forwarding changes pipeline and process topology and requires real-child evidence. The bounded candidate fixes false continuation and status while stating promptness limits.

## D7 — Remain ACTIVE

**Decision:** Stop at `ACTIVE` in this pass.

**Reason:** The packet has a coherent patch, drafts, and reduced matrix, while the regenerated patch still needs exact-source zero-offset application and upstream-native static gates before authorization readiness.
