# Decision log

## 2026-08-01 — preserve unit 22 as a separate source correction

**Decision:** Keep the regular-file type-class correction separate from units 15 and 16.

**Reason:** Unit 22 changes selector parsing in `TypeFilterAction`; unit 15 owns transform/path/PAX metadata semantics, and unit 16 owns post-selection hard-link dependency handling. The invariants and regressions are distinct even when source-line ordering requires later composition review.

**Evidence:** Issue #397 unit 22; issue #76; PR #77; `SOURCE_MAP.md`; retained patch.

**Alternatives considered:**

- Fold into unit 16 because both mention type exclusion.
- Fold all tarfilter fixes into one broad series.

**Consequences:**

- One source line plus one archive-level regression remain independently reviewable.
- Final ordering still waits for active tarfilter candidate heads.

**Reopen trigger:** A final adjacent candidate rewrites `TypeFilterAction` so thoroughly that the unit cannot apply or be reviewed independently.

**Authority effect:** Internal work only; external contact remains unauthorized.

---

## 2026-08-01 — select semantic class expansion

**Decision:** Map `REGTYPE` and `0` to both `tarfile.REGTYPE` and `tarfile.AREGTYPE`.

**Reason:** Python's own regular-file predicate accepts both encodings, while the documented selector names the regular-file class. Expanding the stored selector bytes preserves the existing raw-equality decision loop and limits the code change to one line.

**Evidence:** Imported source blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`; focused regression; exact candidate head `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7`; CI run `30537313944`; accepted review on PR #77.

**Alternatives considered:**

- Special-case `member.isfile()` in the decision loop.
- Add a separate public `AREGTYPE` selector.

**Consequences:**

- Both accepted regular encodings obey the existing selector.
- Other member classes remain byte-specific and unchanged.

**Reopen trigger:** Current upstream changes the selector representation or adopts a class-based decision model that makes the retained one-line patch obsolete.

**Authority effect:** Internal candidate selection only.

---

## 2026-08-01 — hold before upstream extraction

**Decision:** Set unit 22 to `HOLD`.

**Reason:** The exact current Salsa `master` identity and native test placement remain unresolved in this runtime, and issue #397 directs this unit to land after active tarfilter series settle their order.

**Evidence:** `git clone` failed with `Could not resolve host: salsa.debian.org`; active adjacent units 01, 15, and 16 remain composition dependencies; `TESTS.md` lists unexecuted current-upstream gates.

**Alternatives considered:**

- Mark ready based solely on the imported 1.5.7-3 candidate and Linux Fieldwork CI.
- Create a controlled Salsa fork immediately.

**Consequences:**

- The validated patch and regression are retained without overstating current-upstream readiness.
- No external resource is created.

**Reopen trigger:** Fetch an exact current Salsa `master`, identify final adjacent tarfilter heads/order, apply the patch, place the native regression, and run focused plus relevant broader gates.

**Authority effect:** External contact remains unauthorized.

## Final disposition

`HOLD` — 2026-08-01. Evidence: retained exact-head candidate and CI are complete for the imported source; current-upstream rebase/native testing and final tarfilter ordering remain the named blocker.
