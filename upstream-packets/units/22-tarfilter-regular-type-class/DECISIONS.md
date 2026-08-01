# Decision log

## 2026-08-01 — preserve unit 22 as a separate source correction

**Decision:** Keep the regular-file type-class correction separate from units 15 and 16.

**Reason:** Unit 22 changes selector parsing in `TypeFilterAction`; unit 15 owns transform/path/PAX metadata semantics, and unit 16 owns post-selection hard-link dependency handling. The invariants and regressions are distinct.

**Evidence:** Issue #397 unit 22; issue #76; PR #77; `SOURCE_MAP.md`; retained patch; current unit 01, 15, and 16 packets.

**Alternatives considered:**

- Fold into unit 16 because both mention type exclusion.
- Fold all tarfilter fixes into one broad series.

**Consequences:**

- One source line plus one archive-level regression remain independently reviewable.
- Adjacent patches still belong in a later complete-gate composition run, while their completion order creates no technical block for unit 22.

**Reopen trigger:** A current upstream change rewrites `TypeFilterAction` so thoroughly that the unit cannot apply or be reviewed independently.

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

## 2026-08-01 — correct canonical upstream identity

**Decision:** Treat `https://gitlab.mister-muffin.de/josch/mmdebstrap` `main` as canonical upstream. Retain Debian Salsa/package identities as packaging context.

**Reason:** Current project source, README, commit history, and `tarfilter` are hosted by the `josch/mmdebstrap` Forgejo project. Exact current head is `77ec9be5417ee44c96343d2347145585da1b1f94`.

**Evidence:** Current upstream project and `tarfilter` inspection; unit 15's independently recorded exact upstream base and source identity; Debian package import metadata.

**Alternatives considered:**

- Continue treating Debian Salsa `master` as the canonical implementation destination.
- Leave the destination unresolved.

**Consequences:**

- Rebase and native testing target Forgejo `main`.
- Any later public contribution requires a controlled fork/delivery decision for that host.

**Reopen trigger:** The project publishes a different canonical contribution repository or maintainer direction.

**Authority effect:** Destination research only; external contact remains unauthorized.

---

## 2026-08-01 — correct state from HOLD to ACTIVE

**Decision:** Replace `HOLD` with `ACTIVE`.

**Reason:** Exact current upstream is identified, the defect remains present there, and adjacent tarfilter units own separate code paths. Materializing the checkout, integrating the native regression, and running tests are ordinary technical work. They call for continued execution.

**Evidence:** Upstream `main@77ec9be5417ee44c96343d2347145585da1b1f94`; current `tarfilter` selector mapping; unit 01, 15, and 16 source ownership; user direction to continue technical work until the packet is ready for review.

**Alternatives considered:**

- Preserve `HOLD` for unavailable Git transport in this runtime.
- Mark `READY FOR AUTHORIZATION` from the historical exact-head receipt alone.

**Consequences:**

- Continue investigation and native-test work.
- Move to `READY FOR AUTHORIZATION` only when technical verification and complete-diff review are complete.
- Reserve `HOLD` for a real external or technical dependency that stops progress after available investigation is exhausted.

**Reopen trigger:** A genuine blocker emerges that cannot be resolved through continued internal work and has one named external discriminator.

**Authority effect:** External contact remains unauthorized.

## Final disposition

`ACTIVE` — 2026-08-01. Current upstream and independent source ownership are established. Native-test integration, exact-checkout execution, cleanup/rerun, and complete-diff review remain.
