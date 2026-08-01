# Decision log

## 2026-08-01 — use PR #68 plus PR #102 as canonical source provenance

**Decision:** Treat PR #68 as the canonical integrated foundation and PR #102 as its numeric-occurrence increment.

**Reason:** PR #68 composes replacement semantics, target scopes, hard-link rewriting, and PAX invalidation while correcting PR #48's stale default symlink expectation. PR #102 adds the remaining numeric behavior without reopening those settled mechanisms.

**Evidence:** PR #68 head `1f8f16bf0841a720bdc1da727000c26a3ab13a09`, merge `e7388243f3436ceda16f9d5be70d5423cc379b9d`; PR #102 head `46f49d04639d6baf43243e5096175866c7e6a58e`, merge `78ba614fa7faf4f4cdff99bab832649c774fe1e7`; carrier map in `SOURCE_MAP.md`.

**Alternatives considered:**

- PR #48 alone: stale default symlink scope.
- PR #52: closed unmerged, stale stacked base, superseded by canonical carriers.
- PR #56 alone: lacks target scopes, link/PAX composition, and numeric selectors.

**Consequences:** Historical carriers remain linked for evidence but do not define the release candidate independently.

**Reopen trigger:** A later carrier contains unique source behavior absent from PR #68 plus PR #102.

**Authority effect:** Internal selection only; external contact remains unauthorized.

---

## 2026-08-01 — preserve unit 01 as the regex-dialect owner

**Decision:** Keep GNU basic/extended pattern translation outside unit 15.

**Reason:** Unit 15 has a bounded shared invariant around replacement selection, target ownership, links, and PAX metadata. Unit 01 already owns pattern-language translation and malformed regex compatibility.

**Evidence:** Issue #397 unit definitions; issue #36 carrier history; unit 15 differential matrix deliberately uses patterns inside the shared subset.

**Alternatives considered:**

- Fold unit 01 into unit 15: creates an oversized parser and metadata contribution and duplicates an active near-release unit.

**Consequences:** Unit 15's compatibility statement explicitly preserves the current Python pattern dialect.

**Reopen trigger:** Unit 01 changes the transform representation so deeply that the two patches cannot compose without duplicating core parser work.

**Authority effect:** No change.

---

## 2026-08-01 — regenerate a clean release patch

**Decision:** Retain one regenerated patch from the exact baseline to the composed source rather than shipping the historical two-patch carrier pair.

**Reason:** The historical Git patches compose but use offsets, and GNU patch 2.8 rejects the first parser hunk of PR #68. The regenerated patch applies with `--fuzz=0`, no offsets, and produces the exact tested candidate.

**Evidence:** `artifacts/APPLICATION.txt`; patch SHA-256 `4d8cb2f180cb7798a15195c2dcfac164b409f68a18c69d507cfc624d4725703c`; candidate SHA-256 `adb1a8353bcd676a8acdba4318b198539820b890e2a96016b9909d382942e42e`.

**Alternatives considered:**

- Keep PR #68 and PR #102 patches unchanged: provenance is clear, release application is less robust.
- Manually edit old hunk headers: creates another historical-carrier mutation and still leaves an offset-heavy pair.

**Consequences:** The packet has one clean candidate patch and retains old patch identities only as provenance and predecessor controls.

**Reopen trigger:** A current upstream checkout changes the source enough that the regenerated patch no longer applies cleanly.

**Authority effect:** Internal patch packaging only.

---

## 2026-08-01 — keep one semantic patch pending upstream-native review

**Decision:** Use one patch for the current candidate. Permit a later ordered two-commit series only after upstream-native test conversion and complete-diff review.

**Reason:** Parsed transform state, occurrence selection, target scopes, link mutation, and PAX invalidation converge in one parser and one member loop. An immediate split would overlap source edits and weaken the integrated negative controls.

**Evidence:** One-file diff stat in `artifacts/APPLICATION.txt`; operation ownership in `SOURCE_MAP.md`; integrated matrix in `TESTS.md`.

**Alternatives considered:**

- Parser/replacement commit plus link/PAX commit immediately.
- Separate strip repair from transform repair.

**Consequences:** Review receives one coherent behavior change now; the handoff names the exact discriminator for a later split.

**Reopen trigger:** Current upstream tests demonstrate independently mergeable commits with minimal overlap and clear standalone failures.

**Authority effect:** No change.

---

## 2026-08-01 — destination remains a controlled Forgejo fork and pull request

**Decision:** Proposed delivery is a controlled fork branch and pull request to `josch/mmdebstrap`; record `NEEDS FORK` and `NEEDS BRANCH` until the owner provides them.

**Reason:** The project is hosted on Forgejo and exposes pull requests. No controlled fork identity is currently recorded.

**Evidence:** Current upstream repository and README; `SOURCE_MAP.md`; `artifacts/UPSTREAM_OVERLAP.md`.

**Alternatives considered:**

- Public issue first: unnecessary unless project policy or final review requires it.
- Email or mailing-list patch series: no evidence this is the preferred path.

**Consequences:** Packet drafts remain internal and no public object is created.

**Reopen trigger:** Maintainer contribution guidance or repository-owner instruction selects another route.

**Authority effect:** External contact remains unauthorized; none occurred.

## Final disposition

`ACTIVE` on 2026-08-01. The clean patch and focused matrix are complete. Current-upstream checkout integration, upstream-native tests, complete final diff, controlled fork/branch, and authorization remain.
