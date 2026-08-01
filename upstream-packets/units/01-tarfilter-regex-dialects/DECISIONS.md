# Decision log

## 2026-08-01 — retain one regex dialect unit

**Decision:** Keep the core dialect translator and the Python-group, malformed-interval, unmatched-close, and repeated-quantifier repairs in one upstream review unit.

**Reason:** They modify one transform-pattern parser boundary, overlap source context, and share one GNU differential matrix. Sending the core without the repairs would preserve known success/error divergence.

**Evidence:** Issue #212; PRs #151, #202, and #216; `DEEP_DIVE.md`.

**Alternatives considered:**

- split each grammar repair into a separate merge request;
- send only the core translator and document the known gaps;
- expand this unit into complete POSIX/GNU regex compatibility.

**Consequences:**

- the current-source diff must contain the complete repaired parser state;
- broader locale/classes/flags/replacement work remains separate;
- review remains bounded to one language-boundary change.

**Reopen trigger:** Current canonical-source review reveals independently mergeable files or a maintainer contribution rule requiring a smaller sequence.

**Authority effect:** Internal work only; external contact remains unauthorized.

---

## 2026-08-01 — treat target scopes and occurrences as prerequisites pending current-source review

**Decision:** Preserve PR #68 and PR #102 patches in the ordered rebase manifest, while withholding a final one-MR versus ordered-series decision until current canonical source is inspected.

**Reason:** The retained regex tests apply those patches first and prove composition across target fields and numeric occurrence state. Unit 15 owns broader transform/PAX semantics, so current upstream may already contain, supersede, or require separation of those prerequisite behaviors.

**Evidence:** `SOURCE_MAP.md`; PRs #68, #102, and #151; focused test setup.

**Alternatives considered:**

- declare all four patches one final merge request now;
- drop the prerequisites and claim only parser-unit tests;
- move the entire regex unit into unit 15.

**Consequences:**

- the next worker must inspect exact current source before generating a final patch;
- fuzz or offsets cannot be used to force the old stack;
- the final candidate may be one current-source commit or an ordered series, with the regex translator and repairs remaining together.

**Reopen trigger:** Exact current Salsa `master` establishes which prerequisite behavior is present and which source lines remain.

**Authority effect:** Internal work only; external contact remains unauthorized.

---

## 2026-08-01 — decline to repeat the old-base test matrix

**Decision:** Stop after pinning the rebase manifest instead of reapplying the retained patches to imported blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`.

**Reason:** Existing exact-head receipts already cover that retained composition. Issue #397 requires current canonical-upstream evidence. The runtime could not retrieve exact Salsa `master`, and a mirror with the same old blob cannot substitute for the canonical base.

**Evidence:** `TESTS.md` records the failed checkout command and retrieval boundary; issue #212 records the existing green exact-head receipt.

**Alternatives considered:**

- rerun the old matrix solely to create a fresh timestamp;
- use the noncanonical mirror as the rebase base;
- infer the canonical base from a packaged release snapshot.

**Consequences:**

- no fresh execution result is claimed;
- the first incomplete step remains exact canonical checkout and patch application;
- evidence stays honest and directly useful to the next worker.

**Reopen trigger:** A runtime can fetch the canonical Salsa repository and exact `master` commit.

**Authority effect:** No change; internal work only.

---

## 2026-08-01 — destination and publication boundary

**Decision:** Record `GitLab/Salsa fork and merge request` as the intended delivery method, with `NEEDS FORK`, `NEEDS BRANCH`, and explicit authorization gates.

**Reason:** Issue #212 names the canonical mmdebstrap Salsa project. Issue #397 authorizes internal preparation and forbids new public contact without a deliberate unit-specific authorization.

**Evidence:** Issue #397 authority section; issue #212 destination and authority sections; `README.md`.

**Alternatives considered:**

- Debian BTS patch;
- mailing-list patch series;
- direct maintainer email;
- public Salsa issue before a merge request.

**Consequences:**

- no fork, branch, issue, merge request, comment, review, or email may be created yet;
- the packet drafts remain internal;
- authorization should occur only after the technical gate is complete.

**Reopen trigger:** Current contribution instructions identify another required delivery path, or the repository owner explicitly selects one.

**Authority effect:** External contact remains `false`.

## Current disposition

`ACTIVE` as of 2026-08-01. Exact current canonical base, clean current-source application/regeneration, upstream-native tests, fresh overlap search, and complete-diff review remain.
