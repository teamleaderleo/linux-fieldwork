# Decision log

## 2026-08-01 — select numeric-key removal

**Decision:** Remove only PAX `uid` and `gid` after a validated nonzero ID shift.

**Reason:** Those two retained strings directly contradict the shifted `TarInfo` fields. Removing them lets Python choose the correct ordinary or PAX representation from the new values while preserving unrelated metadata.

**Evidence:** Issue #37; PR #78 exact head `8d6443626e4338b180ec0533969bfe4d32b20d52`; CI run `30538012863`; fresh packet probe recorded in `TESTS.md`.

**Alternatives considered:**

- assign new string keys directly — rejected because it adds numeric PAX keys to ordinary members;
- clear every PAX key — rejected because it can discard unrelated metadata;
- leave representation repair to a broader metadata unit — rejected because this defect is a complete two-line numeric ownership correction with its own detector.

**Consequences:**

- large shifted IDs regenerate as PAX strings;
- ordinary shifted IDs remain representable in base tar headers;
- unrelated PAX data remains;
- source change stays bounded to one option path.

**Reopen trigger:** Python tarfile semantics change, native tests expose a representation contract conflict, or unit 15 provides a stronger equivalent integrated correction.

**Authority effect:** Internal implementation and test preparation only. External-contact authority remains false.

---

## 2026-08-01 — keep unit 19 independent from adjacent tarfilter units

**Decision:** Preserve unit 19 as one small source-plus-native-test PR.

**Reason:** Numeric PAX ownership has a distinct invariant and exact source owner. Path normalization, no-option passthrough, transform/link metadata, hard-link dependency, and type-flag behavior each have separate units and compatibility matrices.

**Evidence:** Issue #397 unit boundaries; `upstream-packets/INDEX.md`; current source review in `SOURCE_MAP.md`.

**Alternatives considered:**

- combine with unit 15 — deferred because unit 15 owns broader path/link/PAX semantics and would delay this bounded correction;
- combine with unit 18 — rejected because byte-preserving no-option passthrough changes entry behavior, while this patch acts only for active nonzero id shifting.

**Consequences:**

- proposed upstream diff contains `tarfilter` and `tests/tarfilter-idshift` only;
- overlap must be checked again if unit 15 materializes first.

**Reopen trigger:** current upstream review shows the same lines must change as part of a coherent accepted metadata refactor.

**Authority effect:** None.

---

## 2026-08-01 — canonical carrier and packaging

**Decision:** Treat PR #78 as the canonical prior candidate, retain a clean upstream-root patch in this packet, and supersede its earlier malformed patch revisions.

**Reason:** PR #78 final head passed exact-source regression and independent review. Its original patch path targeted the Linux Fieldwork import, so upstream preparation needs a path-clean patch and native test edit.

**Evidence:** PR #78 head `8d6443626e4338b180ec0533969bfe4d32b20d52`, merge `4df9ff80f01a0aef255e2c9011034d23e340cebe`, review acceptance, run `30538012863`.

**Alternatives considered:**

- reuse an early PR #78 patch revision — rejected because semantic execution never began;
- edit the imported source on the packet branch — rejected because the unit branch should retain evidence and upstream-ready material without changing the shared import.

**Consequences:**

- `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch` is the retained source hunk;
- final materialization adds the native test before readiness.

**Reopen trigger:** a current upstream checkout changes surrounding lines or offers a preferred source helper.

**Authority effect:** None.

---

## 2026-08-01 — extend the existing native id-shift test

**Decision:** Add the PAX-large regression to upstream `tests/tarfilter-idshift`, retain the draft as `patches/0002-tests-cover-pax-idshift.patch`, and publish source plus test as one eventual upstream commit.

**Reason:** The existing native test already owns PAX xattr preservation, zero-shift byte identity, ordinary numeric shifting, extraction-based ownership checks, and inverse shifting. A large numeric member belongs beside those controls. A second test file would duplicate setup and weaken the visible ownership of the option contract.

**Evidence:** Imported test blob `6956e76aca153147d3a8a6668196d913ebc8a49e`; `0002` SHA-256 `ce5442b10be51b900a86947f25046ff39392fd2e9e9a776e982eabe79a177edc`; detector baseline status `1` with `large ownership was not shifted`; detector candidate status `0`; complete receipts in `TESTS.md`.

**Alternatives considered:**

- add a separate Python test — rejected for the upstream candidate because the native shell test already owns this behavior and uses the project's tarfilter selection path;
- replace the existing ordinary test — rejected because ordinary base-header behavior remains a valuable control;
- assert byte identity after the large-ID round trip — deferred because PAX record layout may change while logical ownership, unrelated metadata, and payload stay correct. The existing ordinary archive continues to assert byte identity.

**Consequences:**

- retained packet preparation consists of ordered patches `0001` then `0002`;
- intended upstream fence is exactly `tarfilter` and `tests/tarfilter-idshift`;
- exact current-head application and full native execution remain required;
- the regression has an executable losing path and cannot pass every implementation.

**Reopen trigger:** current upstream changes the native test owner, a full exact-head run exposes portability trouble, or maintainers prefer a separate fixture/helper.

**Authority effect:** Internal test preparation only. External-contact authority remains false.

---

## 2026-08-01 — delivery destination

**Decision:** Target the canonical mmdebstrap Forgejo/Gitea repository with a fork-and-pull-request workflow.

**Reason:** The source repository hosts its issue and pull-request interface and remains the authoritative source line. No controlled fork identity has been verified.

**Evidence:** canonical repository inspection recorded in `SOURCE_MAP.md`.

**Alternatives considered:**

- Debian BTS patch — possible downstream path, but current unit is an upstream source correction and no Debian-specific delta is required;
- email-only patch — no project requirement established;
- Linux Fieldwork PR as completion — rejected because internal merge status does not complete issue #397.

**Consequences:**

- packet records `NEEDS FORK` and `NEEDS BRANCH`;
- no public action occurs before explicit unit-specific authorization.

**Reopen trigger:** maintainer contribution instructions require another channel, or a maintained downstream branch is the only missing destination.

**Authority effect:** Destination selected; external-contact authority remains false.

## Final disposition

`ACTIVE` on 2026-08-01. Source correction, prior exact-source evidence, current-source persistence, overlap refresh, packet source patch, native test-owner selection, native test draft, and independent detector validation are complete. Current-upstream branch materialization, exact application, complete native test execution, and exact-head gates remain.
