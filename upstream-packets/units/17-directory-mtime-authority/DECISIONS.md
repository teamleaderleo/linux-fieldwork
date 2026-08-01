# Decision log

## 2026-08-01 — retain byte-identical root/chrootless tar output as the product contract

**Decision:** Keep the existing byte-comparison contract and pursue a product correction.

**Reason:** The project documents bit-for-bit reproducibility with `SOURCE_DATE_EPOCH`, and the chrootless test compares four archive pairs directly.

**Evidence:** issue #380, PR #383, imported `README.md`, and current `tests/chrootless` source review.

**Alternatives considered:** comparison-only directory normalization.

**Consequences:** A test-only mask requires an explicit contract change and remains outside the leading route.

**Reopen trigger:** current upstream changes the documented reproducibility contract or test intent.

**Authority effect:** Internal decision only; external contact remains unauthorized.

---

## 2026-08-01 — select directory-only normalization as the policy class

**Decision:** Preserve older non-directory member mtimes and converge real directory mtimes only.

**Reason:** Full normalization converged bytes while destroying the deliberately old package-file mtime. Directory-only normalization converged bytes and preserved it.

**Evidence:** PR #383 policy matrix and run-999 real package anchor.

**Alternatives considered:** current clamp, full normalization, comparison-only normalization.

**Consequences:** Any implementation must prove real-directory identity and metadata preservation across links, devices, xattrs, ACLs, capabilities, sparse source files, cleanup, and rerun.

**Reopen trigger:** a current upstream mechanism converges directories without live-tree mutation and passes the full metadata matrix.

**Authority effect:** No external authorization.

---

## 2026-08-01 — reject path identity as mutation authority

**Decision:** Treat path-based `lstat` followed by path-based timestamp mutation as disqualified.

**Reason:** A replacement can redirect mutation to a symlink target or change a regular file after the directory check.

**Evidence:** PR #384 review and issue #380 update.

**Alternatives considered:** path mutation with no-follow options and failure-closed fallbacks.

**Consequences:** PR #384 stays rejected. PR #395 remains a carrier for product scope and evidence, not a selected authority-safe implementation.

**Reopen trigger:** an atomic pathname API proves identity and mutation under the required platform matrix.

**Authority effect:** No external authorization.

---

## 2026-08-01 — descriptor identity alone does not settle operation ownership

**Decision:** Keep PR #389 on hold despite its mechanically green descriptor controls.

**Reason:** An opened inode can move outside the temporary root and still receive handle-based timestamp mutation. Current-membership checking narrows this case and retains a final move-out race.

**Evidence:** issue #392 and PR #394.

**Alternatives considered:** open-time authority, best-effort current membership, archive-header-only rewriting.

**Consequences:** No sid run or product promotion until the archive-boundary process discriminator runs.

**Reopen trigger:** repeated runtime evidence establishes a quiescent completed tree, or a no-tree-mutation implementation clears archive compatibility.

**Authority effect:** Internal tests remain authorized; external contact remains unauthorized.

---

## 2026-08-01 — create a packet-local archive-boundary process probe

**Decision:** Add an evidence-only Linux `/proc` probe and focused controls before writing a source instrumentation patch.

**Reason:** Issue #392 requires exact live/zombie ancestry, process-group/session/cgroup identity, and temporary-root access evidence at two phases. The probe can be reviewed and tested independently while the live candidate identity is reconciled.

**Evidence:** `scripts/archive_boundary_process_probe.py`, `scripts/test_archive_boundary_process_probe.py`, and `TESTS.md`.

**Alternatives considered:** infer quiescence from source order; immediately modify imported source; add another descriptor-membership check.

**Consequences:** The next source change is a disposable instrumentation patch pinned to the exact live carrier. The probe result cannot itself select a product implementation until real root/chrootless receipts exist.

**Reopen trigger:** source review shows the required data cannot be captured from a synchronous boundary child or `/proc` visibility is insufficient.

**Authority effect:** Internal synthetic and disposable runtime evidence only. No upstream contact.

---

## 2026-08-01 — current candidate identity uses the live ref

**Decision:** Record PR #395 live head `74c996394819c3a717d55193d84336c2e06b3b7c` as current and retain `e700839034a3b1ce3f3ddbfed5cf6d43a4c6987c` as an earlier body-stated generation.

**Reason:** Connector metadata and PR prose disagree. Executions and reviews must pin the live ref.

**Evidence:** PR #395 metadata refreshed during this pass.

**Alternatives considered:** inherit the PR body’s older head as current.

**Consequences:** Complete live-head diff review precedes instrumentation or candidate testing.

**Reopen trigger:** PR #395 advances again or the body is updated with a newer exact head and receipts.

**Authority effect:** No external authorization.

## Final disposition

`HOLD` as of 2026-08-01. The exact blocker is archive-boundary operation authority. The next discriminator is repeated root/chrootless process evidence immediately after setup and immediately before tar. External contact remains unauthorized and none occurred.
