# Decision log — unit 16

## 2026-08-01 — use PR #310 as the lifecycle and duplicate-state predecessor

**Decision:** Preserve PR #310 head `32dfa36a6feb533bc1126a11ef33979e45b410ec` as the immediate type-hardlink predecessor.

**Reason:** PR #310 finalizes the output archive before returning status 1, preserves earlier retained duplicate targets, and records retention only after later skip decisions.

**Evidence:** Issues #243 and #335; PRs #248 and #310; packet patch `0001-compose-pr310-predecessor-on-transform-carrier.patch`.

**Alternatives considered:**

- PR #248 alone retains lifecycle and duplicate-state defects.
- PR #281 mixes a superseded transform carrier with the duplicate repair.

**Consequences:** Unit 16 begins from the repaired streaming lifecycle and duplicate-name behavior.

**Reopen trigger:** A complete diff or inherited matrix shows behavioral divergence from PR #310.

**Authority effect:** Internal work only; external-contact state unchanged.

---

## 2026-08-01 — restack on unit 15's clean transform/metadata prerequisite

**Decision:** Use packet patch `0000-unit15-transform-metadata-prerequisite.patch`, copied byte-for-byte from unit 15, as the canonical rewrite prerequisite.

**Reason:** The historical PR #68 patch carries the right reviewed behavior but its parser hunk fails zero-fuzz application against exact imported blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`. Unit 15 regenerated the transform/metadata candidate with clean application and five-field transform tuples.

**Evidence:** CI runs `30689716762`, `30690001217`, and `30690165287` reached the historical PR #68 application failure; unit 15 patch blob `38510533dc015182f3e87e9d2f3777eea5b8c93b`; unit 16 commit `70cb20cdc3d27044a4369678fc62ba1ce23f1849`.

**Alternatives considered:**

- Repair the historical PR #68 hunk again inside unit 16, duplicating unit 15 ownership.
- Keep offset/fuzz application, weakening the exact composition contract.

**Consequences:** Patches `0001` and `0002` are generated for `_sed_substitute` and the five-field tuple `(regex, replacement, occurrence, global_after, scopes)`.

**Reopen trigger:** Unit 15 supersedes the retained clean prerequisite with different candidate bytes.

**Authority effect:** Internal work only; external-contact state unchanged.

---

## 2026-08-01 — use final projected identities for type-filter ownership

**Decision:** Record type-excluded targets and retained hard-link targets in their final projected name domain after component stripping and applicable transform scopes.

**Reason:** Extractors resolve hard links against emitted names. The PR #310 predecessor compares input spellings before later rewrites, causing a valid emitted target to be rejected. Final projected identity accepts the valid `base` target and still rejects a genuine removed `base` target.

**Evidence:** `tests/test_tarfilter_type_excluded_final_name_identity.py`; selected patch `0002-use-rewritten-identities-for-type-hardlinks.patch`.

**Alternatives considered:**

- Input-name state preserves the demonstrated false rejection.
- Payload materialization changes type-filter meaning and requires content retention.
- Arbitrary graph buffering widens the streaming model.

**Consequences:** Original member and target spellings remain available for diagnostics while dependency state uses projected final names.

**Reopen trigger:** Transform-scope or inherited compatibility controls show a final-name mismatch caused by the selected projection.

**Authority effect:** Internal work only; external-contact state unchanged.

---

## 2026-08-01 — reject alias projection and keep intrinsic rewrite breaks outside unit 16

**Decision:** Track only the final projected identity of a type-excluded member. Intermediate input and post-strip aliases are excluded from dependency state.

**Reason:** The strip fixture `root/base` plus `prefix/peer -> prefix/root/base` already emits `base` and broken `peer -> root/base` when no type filter is active. Alias projection converts that existing rewrite failure into `hard-link target excluded by type filter`, assigning the failure to an option that did not create the broken reference.

**Evidence:** The direct no-type-filter control in `tests/test_tarfilter_type_excluded_final_name_identity.py`; rejected patch `patches/rejected/0002-alias-projection-overattributes-strip-breaks.patch`; run `30690434953` passed all 442 tests on the alias candidate and therefore proves the candidate's behavior exactly.

**Alternatives considered:**

- Accept any input, strip-stage, or transform-stage alias.
- Reject every final dangling hard link regardless of the operation that created it.

**Consequences:** Intrinsic strip or transform reference failures remain with unit 15's rewrite semantics. Unit 16 rejects only a final hard-link target identity that corresponds to a member removed by the active type filter.

**Reopen trigger:** A direct unfiltered control becomes valid while the type-filtered output alone becomes broken.

**Authority effect:** Internal work only; external-contact state unchanged.

---

## 2026-08-01 — preserve rejected candidate evidence

**Decision:** Retain the alias-projection patch under `patches/rejected/`.

**Reason:** Its green full gate demonstrates implementation viability while the direct control demonstrates policy overreach. Keeping both facts prevents a later worker from recreating an attractive but incorrectly attributed fix.

**Evidence:** Run `30690434953`, job `91344069265`: 3 patch files and 9 hunks validated, 442 tests passed, shell/help gates passed.

**Consequences:** The active `0002` patch remains the final-only candidate. The rejected patch is evidence and stays outside the applied series.

**Reopen trigger:** Upstream explicitly chooses a general final-archive validity policy spanning strip, transform, and type filtering.

**Authority effect:** Internal work only; external-contact state unchanged.

---

## Final disposition

`ACTIVE` on 2026-08-01. The clean prerequisite, repaired predecessor, final-only candidate, focused matrix, inherited matrix, and rejected alias evidence are present. Selected-head execution, immediate rerun, complete-diff review, and packet closeout remain.
