# Decision log — unit 16

## 2026-08-01 — use PR #310 as the immediate predecessor

**Decision:** Treat PR #310 head `32dfa36a6feb533bc1126a11ef33979e45b410ec` as the canonical lifecycle and duplicate-state predecessor, composed after the PR #68 transform/strip carrier.

**Reason:** PR #310 repairs three defects in the first rejection candidate: archive finalization, retained duplicate targets, and retained-state updates before later skip decisions. Issue #335 explicitly starts from that repaired boundary.

**Evidence:** Issues #243 and #335; PRs #248, #310, and #68; packet `SOURCE_MAP.md`.

**Alternatives considered:**

- PR #248 alone: preserves known lifecycle and duplicate-state defects.
- PR #281: mixes stale transform/PAX carrier work and is superseded by PR #310.

**Consequences:** The packet carries a clean combined predecessor patch targeted after the canonical transform/strip patch. Candidate work begins at final-name identity.

**Reopen trigger:** A complete diff review finds that the packet-local composition diverges behaviorally from PR #310.

**Authority effect:** Internal work only; external-contact state unchanged.

---

## 2026-08-01 — characterize both failure directions before selecting code

**Decision:** Add executable false-rejection and false-acceptance strip fixtures before writing the final-name correction.

**Reason:** A correction that fixes only rejection can still emit dangling hard links, while a correction that fixes only acceptance can still reject valid archives. Both outcomes need one shared invariant.

**Evidence:** Issue #335 fixtures; `tests/test_tarfilter_type_excluded_final_name_identity.py`.

**Alternatives considered:**

- Move the dependency check after strip with no excluded-name projection: insufficient for excluded members because they currently leave the loop before rewriting.
- Compare raw and rewritten strings: creates dual-domain ambiguity.
- Begin with transform collisions: wider than the first bounded discriminator.

**Consequences:** The first selected candidate must turn both characterization outcomes green and then survive transform-scope controls.

**Reopen trigger:** Exact execution contradicts either expected predecessor result.

**Authority effect:** Internal work only; external-contact state unchanged.

---

## 2026-08-01 — use one final emitted-name domain

**Decision:** Select a shared rewrite operation for retained member names, retained hard-link targets, and type-excluded member projection as the candidate direction.

**Reason:** Archive extractors resolve hard links using emitted names. Pre-rewrite input identity causes both observed failure directions. A single final-name domain yields one availability invariant.

**Evidence:** `DEEP_DIVE.md`, issue #335 source boundary, and the prepared two-case test.

**Alternatives considered:**

- silently skip dependent links;
- materialize payloads;
- buffer arbitrary dependency graphs;
- accept a match in either raw or final domain.

**Consequences:** The helper must represent dropped identities, member-name transform scope, hard-link target transform scope, and PAX cleanup ownership. Duplicate and collision controls decide the exact state container.

**Reopen trigger:** GNU tar differential controls show that excluded-member projection follows a different operation than emitted member naming for an in-scope option.

**Authority effect:** Internal work only; external-contact state unchanged.

---

## Final disposition

`ACTIVE` on 2026-08-01. The branch contains executable characterization and a selected correction direction. Exact-head execution, candidate implementation, inherited matrix reruns, and complete-gate evidence remain.
