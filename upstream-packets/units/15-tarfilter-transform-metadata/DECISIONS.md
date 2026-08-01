# Decision log

## 2026-08-01 — use PR #68 plus PR #102 as canonical source provenance

**Decision:** Treat PR #68 as the canonical integrated foundation and PR #102 as its numeric-occurrence increment.

**Reason:** PR #68 composes replacement semantics, target scopes, hard-link rewriting, and PAX invalidation while correcting PR #48's stale default symlink expectation. PR #102 adds numeric behavior without reopening those mechanisms.

**Evidence:** PR #68 head `1f8f16bf0841a720bdc1da727000c26a3ab13a09`, merge `e7388243f3436ceda16f9d5be70d5423cc379b9d`; PR #102 head `46f49d04639d6baf43243e5096175866c7e6a58e`, merge `78ba614fa7faf4f4cdff99bab832649c774fe1e7`.

**Rejected alternatives:** PR #48 alone retains the stale symlink expectation; PR #52 is a closed superseded stack; PR #56 lacks link/PAX and numeric composition.

**Reopen trigger:** A later carrier contains unique source behavior absent from PR #68 plus PR #102.

**Authority effect:** Internal selection only.

---

## 2026-08-01 — preserve unit 01 as the regex-dialect owner

**Decision:** Keep GNU basic/extended pattern translation outside unit 15.

**Reason:** Unit 15 owns replacement selection, target ownership, links, and PAX metadata. Unit 01 already owns pattern-language translation and malformed regex compatibility.

**Evidence:** Issue #397 unit definitions and the bounded unit-15 matrix.

**Reopen trigger:** Unit 01 changes the transform representation so deeply that the two units cannot compose without duplicating core parser work.

**Authority effect:** No change.

---

## 2026-08-01 — retain one clean source patch

**Decision:** Keep one regenerated patch from the exact baseline to the composed source rather than releasing the historical patch pair.

**Reason:** The historical Git patches compose with offsets, while GNU patch 2.8 rejects the retained PR #68 parser hunk. The regenerated patch applies with `--fuzz=0`, no offsets, and produces the tested candidate bytes.

**Evidence:** `artifacts/APPLICATION.txt`; patch SHA-256 `4d8cb2f180cb7798a15195c2dcfac164b409f68a18c69d507cfc624d4725703c`; candidate SHA-256 `adb1a8353bcd676a8acdba4318b198539820b890e2a96016b9909d382942e42e`.

**Reopen trigger:** Canonical upstream changes and the clean patch no longer applies.

**Authority effect:** Internal packaging only.

---

## 2026-08-01 — keep the semantic source change integrated

**Decision:** Keep the source change as one semantic patch for now. The controlled fork uses separate commits for source, test, and test registration only to preserve exact identities.

**Reason:** Parsed transform state, occurrence selection, target scopes, link mutation, and PAX invalidation converge in one parser and archive-member loop. Splitting the source immediately would overlap edits and weaken integrated controls.

**Evidence:** `tarfilter` diff `+179/-23`; operation map in `SOURCE_MAP.md`; native and packet matrices in `TESTS.md`.

**Reopen trigger:** Final review demonstrates independently mergeable parser/replacement and link/PAX source commits with minimal overlap and standalone regressions.

**Authority effect:** No change.

---

## 2026-08-01 — preserve the fork's legacy master and branch from the canonical snapshot

**Decision:** Leave `teamleaderleo/mmdebstrap` legacy `master` untouched and base unit 15 on `linux-fieldwork/upstream-main-snapshot`.

**Reason:** The legacy branch is a separate Deepin packaging history ending at `574048f2a720057b75e56622003932f344dc700a`. Git reports no common ancestor with the canonical snapshot. Replacing or force-updating it would erase useful owned history and violate the project's preference for superseding branches over destructive replacement.

**Evidence:** Controlled fork repository metadata; failed common-ancestor comparison; snapshot identity `77ec9be5417ee44c96343d2347145585da1b1f94`; project instructions in `START_HERE.md` and `ADAPTIVE_COORDINATION.md`.

**Rejected alternatives:** Force-update `master`; merge unrelated histories; create a candidate from the packaging branch.

**Consequences:** The fork now has an explicit canonical-source lane while preserving its prior packaging work.

**Reopen trigger:** The repository owner explicitly selects another branch policy after preserving both exact heads.

**Authority effect:** Internal controlled-repository branch work only; no upstream contact.

---

## 2026-08-01 — materialize the candidate and native test in the controlled fork

**Decision:** Use controlled branch `linux-fieldwork/unit-15-tarfilter-transform-metadata` as the exact current candidate.

**Reason:** The packet had source-file evidence but lacked a full code-hosted candidate identity and project-native test location. The controlled branch now contains the exact source bytes, `tests/tarfilter-transform-metadata`, and the matching `coverage.txt` registration.

**Evidence:** Base `77ec9be5417ee44c96343d2347145585da1b1f94`; head `505bf81079a3b76c7d56bffa8097c1b5a494898e`; three commits ahead and zero behind; exact three-file diff recorded in `SOURCE_MAP.md`.

**Consequences:** `NEEDS FORK` and `NEEDS BRANCH` are resolved. The first incomplete work is now runner execution and remaining gates, not source materialization.

**Reopen trigger:** The controlled branch identity changes or current canonical upstream advances before release review.

**Authority effect:** Internal branch creation and commits only; no pull request or upstream comment.

---

## 2026-08-01 — accept direct native execution as a completed focused gate, not as full runner completion

**Decision:** Record the direct `tests/tarfilter-transform-metadata` baseline/candidate run as completed upstream-native focused evidence while keeping `coverage.py`, shellcheck, shfmt, package, and hosted gates open.

**Reason:** The test is located and registered in the project's native surfaces and executes the exact source behavior. The local materialization lacks the complete repository and mirror state required by `coverage.py`. Shellcheck and shfmt are absent in the execution environment.

**Evidence:** `artifacts/FORK_NATIVE_TEST.txt`; baseline status `1` ending at `AssertionError: s/a/b/`; candidate status `0` twice with `tarfilter transform metadata: PASS`; zero matching leftover directories.

**Rejected alternatives:** Mark all upstream-native work incomplete despite direct execution; mark the full upstream runner green without running it.

**Consequences:** State remains `ACTIVE`. The next safe gate is a full controlled-fork checkout, mirror/bootstrap preparation as required, then selected `coverage.py` execution.

**Reopen trigger:** The test fails through the runner, formatting tools reject it, or the complete checkout reveals path or dependency assumptions absent from direct execution.

**Authority effect:** No change.

---

## Delivery decision

**Proposed destination:** Forgejo pull request to `josch/mmdebstrap` from the controlled fork after technical gates and explicit authorization.

**Current authority:** External contact `false`. No upstream issue, pull request, merge request, email, comment, or review was created.

## Final disposition

`ACTIVE` on 2026-08-01. Controlled fork and branch creation, exact-source materialization, native-test addition and registration, direct baseline/candidate execution, syntax checks, cleanup, and rerun are complete. Execution through `coverage.py`, shellcheck, shfmt, relevant package/build gates, hosted CI if applicable, final release-diff review, and authorization remain.
