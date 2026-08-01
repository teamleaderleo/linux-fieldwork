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

**Reopen trigger:** Current upstream rewrites `TypeFilterAction` or changes the public meaning of `REGTYPE`.

**Authority effect:** Internal work only; external contact remains unauthorized.

---

## 2026-08-01 — select semantic class expansion

**Decision:** Map `REGTYPE` and `0` to both `tarfile.REGTYPE` and `tarfile.AREGTYPE`.

**Reason:** Python and GNU tar classify both bytes as regular-file flags, while the documented selector names the regular-file class. Expanding stored selector bytes preserves the existing raw-equality decision loop and limits the code change to one line.

**Evidence:** Source blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`; historical focused regression; candidate head `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7`; CI run `30537313944`; PR #77 review; Python 3.13.5 and GNU tar 1.35 probes.

**Alternatives considered:**

- Special-case `member.isfile()` in the decision loop.
- Add a separate public `AREGTYPE` selector.

**Consequences:**

- Both accepted regular encodings obey the existing selector.
- Other member classes remain byte-specific and unchanged.

**Reopen trigger:** Current upstream adopts a class-based selector representation or demonstrates a compatibility reason to separate the two standard regular encodings.

**Authority effect:** Internal candidate selection only.

---

## 2026-08-01 — correct canonical upstream identity

**Decision:** Treat `https://gitlab.mister-muffin.de/josch/mmdebstrap` `main` as canonical implementation upstream. Retain Debian Salsa/package identities as packaging context.

**Reason:** Current project source, README, commit history, and `tarfilter` are hosted by `josch/mmdebstrap`. Exact inspected head is `77ec9be5417ee44c96343d2347145585da1b1f94`.

**Evidence:** Current upstream project/source inspection; unit 15's independently recorded base/source identity; Debian package import metadata.

**Alternatives considered:**

- Continue treating Debian Salsa as the canonical implementation destination.
- Leave the destination unresolved.

**Consequences:**

- Rebase and native testing target Forgejo `main`.
- A later public contribution requires a controlled fork/delivery decision for that host.

**Reopen trigger:** The project publishes a different canonical contribution repository or maintainer direction.

**Authority effect:** Destination research only; external contact remains unauthorized.

---

## 2026-08-01 — correct state from HOLD to ACTIVE

**Decision:** Replace `HOLD` with `ACTIVE`.

**Reason:** Exact current upstream is identified, the defect remains present there, and adjacent tarfilter units own separate code paths. Materializing a complete checkout, integrating the native regression, and running tests are ordinary technical work.

**Evidence:** Upstream `main@77ec9be5417ee44c96343d2347145585da1b1f94`; current selector mapping; unit 01, 15, and 16 source ownership; user direction to continue until ready for review.

**Alternatives considered:**

- Preserve `HOLD` for unavailable Git transport in this runtime.
- Mark `READY FOR AUTHORIZATION` from historical exact-head evidence alone.

**Consequences:**

- Continue investigation and native-test work.
- Move to `READY FOR AUTHORIZATION` only when technical verification and complete-diff review are complete.
- Reserve `HOLD` for a real dependency that stops available progress.

**Reopen trigger:** A genuine blocker emerges that cannot be resolved through continued internal work and has one named external discriminator.

**Authority effect:** External contact remains unauthorized.

---

## 2026-08-01 — use one upstream-native shell test

**Decision:** Retain `native/tests/tarfilter-regular-type-class` plus `native/coverage.txt.fragment` as the proposed upstream regression.

**Reason:** mmdebstrap's current test framework owns one shell file under `tests/` per `Test:` stanza in `coverage.txt`. `coverage.py` materializes the test, runs shellcheck/shfmt, and dispatches it through project runners. The shell test is mirror-free, unprivileged, cleanup-complete, and directly exercises the product executable.

**Evidence:** `upstream/mmdebstrap/tests/tarfilter-idshift`; `coverage.txt`; `coverage.py`; `run_null.sh`; packet native test; local faithful-model baseline/candidate characterization.

**Alternatives considered:**

- Submit only the Python unittest retained in Linux Fieldwork.
- Add a new Python test framework upstream.
- Fold the regression into `tarfilter-idshift`.

**Consequences:**

- The proposed upstream diff follows existing project ownership.
- The final upstream test file must be executable even though `run_null.sh` invokes generated `shared/test.sh` via `sh -x`.
- Shellcheck/shfmt and full-runner acceptance remain required.

**Reopen trigger:** Current upstream changes its test registry/runner or maintainers request a different test owner.

**Authority effect:** Internal packet design only.

---

## 2026-08-01 — open internal draft PR #410

**Decision:** Use a Linux Fieldwork draft PR to obtain exact-head CI for the native assets and exact-source gate.

**Reason:** The normal Fieldwork workflow runs unit tests only on pull-request heads. Internal draft PR #410 does not contact mmdebstrap upstream and provides the hosted execution surface required by project instructions.

**Evidence:** PR #410; `tests/test_unit22_tarfilter_native_packet.py`; queued `Linux Fieldwork CI` run `30694010739` on head `f0b8c162d49488c35f6aed8b3204048946d801e4` before this decision-log refresh.

**Alternatives considered:**

- Treat local faithful-model execution as sufficient.
- Wait indefinitely for Git transport to become available.
- Contact upstream for CI.

**Consequences:**

- Hosted exact-source evidence can be obtained without crossing the external-contact boundary.
- A queued run remains no result; the exact final head and logs must be reviewed.

**Reopen trigger:** The workflow cannot execute packet tests or a different internal test surface is required.

**Authority effect:** Internal Linux Fieldwork PR only; no upstream contact.

## Final disposition

`ACTIVE` — 2026-08-01. Current upstream, selected mechanism, native test form, cross-consumer semantics, and bounded overlap are established. Hosted exact-source completion and complete-upstream native gates remain.
