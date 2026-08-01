# Decision log

## 2026-08-01 — keep one repaired regex dialect unit

**Decision:** Keep basic/extended translation, repeated-quantifier normalization, Python-group rejection, malformed-interval handling, unmatched-close handling, and PR #220 accepted-neighbor controls in one unit.

**Reason:** They modify the same transform-pattern boundary and require one GNU differential matrix. The accepted-neighbor controls prove the rejection guard remains narrow.

**Evidence:** PRs #151, #216, and #220; `scripts/run_matrix.py`.

**Reopen trigger:** Current upstream test conventions require a smaller source/test split.

**Authority effect:** Internal work only.

---

## 2026-08-01 — adopt unit 15 as the exact prerequisite

**Decision:** Vendor unit 15's regenerated transform metadata/occurrence patch as `patches/0001-transform-metadata-prerequisite.patch`.

**Reason:** Unit 15 proved the historical PR #68 carrier is unsuitable for GNU patch 2.8 and produced a clean zero-fuzz/no-offset replacement. Unit 1 needs its replacement, target-scope, PAX, and numeric-occurrence state.

**Evidence:** Unit-15 branch and handoff; prerequisite patch blob `38510533dc015182f3e87e9d2f3777eea5b8c93b`; result blob `adb330efcc941bf5e646f195c245a3184e42f8e2`.

**Alternatives considered:**

- force the historical PR #68/#102 series;
- omit target/link/occurrence composition;
- fold all unit-15 work invisibly into the regex patch.

**Consequences:** The packet is a transparent two-patch series. Unit 15 remains independently owned.

**Reopen trigger:** Upstream already contains equivalent prerequisite behavior.

**Authority effect:** Internal work only.

---

## 2026-08-01 — regenerate the regex carrier

**Decision:** Replace the historical regex application form with `patches/0002-tarfilter-regex-dialects.patch` generated directly from prerequisite blob `adb330ef...` to candidate blob `ca8e656c...`.

**Reason:** Applying historical core blob `2d7c457...` after the clean prerequisite yielded offsets `+25`, `+19`, then a failed parser hunk. Accepting offsets or manual placement would hide the exact source boundary.

**Evidence:** `artifacts/APPLICATION.txt`; regenerated patch blob `7e7d37a77b0215af033b0c97770c83cce130911a`.

**Alternatives considered:**

- accept the two offsets and repair the failed hunk manually;
- keep four historical patches as the release series;
- merge prerequisite and regex semantics into one opaque patch.

**Consequences:** The current regex patch applies with zero fuzz and zero offsets and includes every retained grammar repair. Historical patches remain evidence only.

**Reopen trigger:** A newer exact upstream source requires another regeneration.

**Authority effect:** Internal work only.

---

## 2026-08-01 — accept the direct matrix as current product evidence

**Decision:** Treat the complete regenerated 57-case matrix as current product evidence for the exact 1.5.7-3 fork source and matching current visible upstream `tarfilter` bytes.

**Reason:** The wrapper verifies base, prerequisite, and candidate blobs before execution. Candidate and GNU tar agree for 41 success cases, two link/occurrence cases, and 11 shared-invalid cases; three POSIX forms preserve the explicit candidate-reject/GNU-accept boundary.

**Evidence:** `artifacts/FULL_MATRIX.txt`, receipt SHA-256 `573cf47dcb947f62910fd3cdd77fe8103a0499b99b2d5d63dc0f081fb60ea8c0`; representative rerun digest `731adb7f...` twice.

**Consequences:** Exact source application and focused behavior are green. Upstream-native execution remains independent and required.

**Reopen trigger:** Candidate bytes move, GNU reference behavior changes, or upstream-native tests expose a product gap.

**Authority effect:** Internal work only.

---

## 2026-08-01 — keep parallel tarfilter units separate during this pass

**Decision:** Reuse unit 15 only. Record units 16 and 18–22 as later composition work.

**Reason:** They contain substantive corrections in distinct source paths. Unit 16 already vendors unit 15; none supersedes regex dialect handling.

**Evidence:** `artifacts/PARALLEL_UNITS.md` and branch comparisons.

**Consequences:** Unit 1 stays reviewable. A later combined branch must compose selected units and review ordinary line overlap.

**Reopen trigger:** The owner selects a combined tarfilter submission branch.

**Authority effect:** Internal work only.

---

## 2026-08-01 — native test and publication boundary

**Decision:** Run focused upstream-native tests through `coverage.py`, then the appropriate broader gate. Keep Salsa publication behind explicit authorization.

**Reason:** The project runner stages local `./tarfilter`. Direct GNU differentials and native orchestration test different risks.

**Consequences:** No send decision yet. A user-controlled GitHub fork exists, while a candidate branch and authorized Salsa MR remain absent.

**Reopen trigger:** Current upstream changes its test or contribution path.

**Authority effect:** External contact remains `false`.

## Current disposition

`ACTIVE` as of 2026-08-01. Exact application and the full direct GNU matrix are green. Upstream-native execution, selected parallel-unit composition, canonical Salsa head/overlap verification, and candidate-branch creation remain.
