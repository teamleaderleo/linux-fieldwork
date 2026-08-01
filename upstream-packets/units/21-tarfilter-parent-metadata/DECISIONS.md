# Decision log

## 2026-07-31 — select original-glob bounded ancestry predicate

**Decision:** Store the original path glob beside its compiled matcher. For excluded directories and symlinks, derive the literal prefix from the original glob and retain the member when the current path and prefix are equal or either is a component-bounded ancestor of the other. An empty prefix retains all candidate parents.

**Reason:** Original-glob substitution alone leaves exact includes broken because the existing comparison points the wrong way. Exact-ancestor-only logic loses wildcard descendants such as `/usr/*/tool`. The selected predicate covers both and preserves conservative wildcard behavior.

**Evidence:** `DEEP_DIVE.md` approach history; `artifacts/local-matrix.json`; retained patch 0001.

**Alternatives considered:**

- use original glob with current `name.startswith(prefix)` check — rejected, exact include still fails;
- retain only ancestors of the fixed prefix — rejected, mid-path wildcard parents fail;
- implement a complete glob prefix-viability automaton — deferred due larger compatibility surface.

**Consequences:**

- early wildcards can retain extra directories or symlinks;
- `/usr` and `/usr2` remain distinct through component boundaries;
- ordinary path matching remains unchanged.

**Reopen trigger:** Upstream requires minimal parent retention, current dpkg policy changes, or a focused test finds an unsupported glob edge case.

**Authority effect:** Internal patch and test work remain authorized. External contact remains unauthorized.

---

## 2026-07-31 — keep source and regression in one patch

**Decision:** Retain one patch changing `tarfilter`, adding `tests/tarfilter-parent-metadata`, and registering it in `coverage.txt`.

**Reason:** The test constrains the new tuple data and predicate directly. A source-only patch would lack the boundary and metadata contract; a test-only patch would fail on current source.

**Evidence:** `patches/0001-tarfilter-retain-parent-metadata.patch`.

**Alternatives considered:**

- separate source and test commits — possible later if maintainers request it;
- issue-only report — insufficient because a bounded candidate exists.

**Consequences:**

- one reviewable upstream unit;
- patch remains usable until a controlled fork exists.

**Reopen trigger:** Maintainer contribution guidance requires ordered commits.

**Authority effect:** No change to external-contact state.

---

## 2026-07-31 — retain patch pending controlled fork

**Decision:** Keep state `ACTIVE` and record `NEEDS FORK` instead of inventing an upstream branch identity.

**Reason:** Exact upstream patch application and native gates require a controlled fork or materialized canonical checkout. The current environment can preserve a patch and evidence safely.

**Evidence:** `TESTS.md` unexecuted gates; `SOURCE_MAP.md` identities.

**Alternatives considered:**

- contact upstream or create a public carrier — unauthorized;
- mark ready for authorization — premature while exact-candidate gates remain.

**Consequences:**

- next work is deterministic: apply patch to exact base and run the focused test;
- no external action occurred.

**Reopen trigger:** A controlled fork becomes available or the owner authorizes its creation/use.

**Authority effect:** External authorization remains false.

---

## 2026-08-01 — define the deliberate dpkg compatibility boundary

**Decision:** Keep the selected two-direction predicate with pathname-component boundaries. Treat dpkg's wildcard conservatism as precedent, while deliberately correcting dpkg's exact-ancestor omission and plain-prefix sibling alias.

**Reason:** Current dpkg source stores the raw pattern but compares only `candidate_path` against the fixed prefix with `strncmp()`. The exact source model shows that this drops `/usr` and `/usr/bin` for exact include `/usr/bin/tool`, yet can retain `/usr2` for include `/usr` or `/usr/*`. The unit candidate fixes both while preserving dpkg's conservative behavior for wildcard and leading-wildcard prefixes.

**Evidence:** dpkg `src/main/filters.c` blob `4fc1600a5717726faddc2fb556730f217e7f22a2`; `scripts/compare-dpkg-parent-retention.py`; `artifacts/dpkg-comparison.json` SHA-256 `65fbceebbb1b0dc7fdadcb13662dc039bc976adddb4989ee9dde4ba77281aa3b`.

**Alternatives considered:**

- copy dpkg's one-direction `strncmp()` behavior exactly — rejected because the headline exact-parent defect remains;
- keep plain string prefixes for closer dpkg parity — rejected because `/usr` aliases `/usr2`;
- tighten all wildcard retention through a complete glob automaton — deferred pending maintainer demand.

**Consequences:**

- the PR draft must state that the change follows dpkg's conservative intent instead of claiming exact predicate parity;
- component-boundary controls remain required;
- a compiled dpkg comparison is optional follow-up evidence, not a blocker for the mmdebstrap candidate.

**Reopen trigger:** Upstream explicitly requires exact dpkg predicate parity or supplies a different parent-retention contract.

**Authority effect:** No external contact or publication authorization is added.

## Final disposition

`ACTIVE` as of 2026-08-01. Exact-source behavior, metadata retention, symlink coverage, and the dpkg compatibility decision are recorded. Full canonical checkout application and native mmdebstrap execution remain.
