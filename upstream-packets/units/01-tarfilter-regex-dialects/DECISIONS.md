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

## 2026-08-01 — retain PR #220 as proof-only evidence

**Decision:** Add PR #220's accepted-neighbor regression to the unit evidence and final test plan, without adding a product-source commit.

**Reason:** The active-`(?` rejection needs positive controls proving that escaped literal parentheses and bracket-expression content remain accepted. PR #220 changes two proof files, zero product-source files, inherits the full regex matrix, and passed exact-head plus current-main execution.

**Evidence:** PR #220 head `bb0a79dec47958c6b865d4b382a44baff17ab736`; merge `ed49c01a85e9d363626db5d2973a33b67209e13b`; CI `30582215292` / 634; `tests/test_tarfilter_transform_regex_python_group_controls.py` blob `5a7bbac729caf71be6033f71d792dfde0d5f653a`.

**Alternatives considered:**

- omit the controls because the product fix is already green;
- create a fifth source patch;
- broaden the guard test into general POSIX bracket support.

**Consequences:**

- final upstream regression should include the three accepted-neighbor cases;
- candidate source remains the four-patch product state;
- the compatibility claim remains bounded.

**Reopen trigger:** Current upstream already contains an equivalent regression or its test conventions require the cases in another native test.

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

## 2026-08-01 — record Debian 1.5.7-3 as package-source corroboration

**Decision:** Treat current Debian archive source `1.5.7-3` as useful source-generation evidence while keeping exact Salsa `master` as the canonical gate.

**Reason:** Debian Sources lists `1.5.7-3` in sid/forky and a 11,453-byte `tarfilter`. Salsa publishes tag `debian/1.5.7-3` at abbreviated commit `6fde9997`. A package-version mirror commit described as updating to `1.5.7-3` carries the same `tarfilter` Git blob as the Linux Fieldwork import. The runtime could not obtain a direct Debian archive file digest or exact current Salsa tree.

**Evidence:** `README.md`, `SOURCE_MAP.md`, and `TESTS.md`; Debian package source page; Debian Sources; Salsa tags; mirror commit `574048f2a720057b75e56622003932f344dc700a`.

**Alternatives considered:**

- promote the package snapshot to canonical base;
- ignore package-source freshness entirely;
- rerun only against the old imported blob.

**Consequences:**

- the packet can state that the retained source aligns with the current Debian package generation;
- the unit remains `ACTIVE` until exact Salsa `master` and its `tarfilter` blob are recorded;
- package evidence cannot authorize fuzz, offsets, or a release-ready claim.

**Reopen trigger:** Direct canonical access reveals a newer or different `tarfilter`, or a direct archive digest disproves the package-generation correspondence.

**Authority effect:** Internal work only; external contact remains unauthorized.

---

## 2026-08-01 — select the native test path

**Decision:** Use the project's `coverage.py`/`coverage.sh` runner for the upstream-native gate after the current-source candidate exists.

**Reason:** The published `1.5.7-3` README documents full and individual execution, and `coverage.py` stages local `./tarfilter` as `shared/tarfilter`. This provides a direct path for testing the rebased source file under project-owned orchestration.

**Evidence:** Debian Sources `README.md` and `coverage.py`; `TESTS.md`.

**Alternatives considered:**

- treat Linux Fieldwork unittests as the only gate;
- invent an upstream command before reading the current tree;
- test only the installed `/usr/bin/mmtarfilter`.

**Consequences:**

- the next worker must inspect current `coverage.txt` and `tests/` to select exact transform-related names;
- the candidate must be present as `./tarfilter` so the runner avoids the installed fallback;
- focused Linux Fieldwork differentials and upstream-native tests both remain required.

**Reopen trigger:** Current Salsa changes its runner or provides a dedicated tarfilter test entrypoint.

**Authority effect:** Internal work only.

---

## 2026-08-01 — decline to repeat the old-base test matrix

**Decision:** Stop after pinning the current evidence and rebase manifest instead of reapplying the retained patches to imported blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`.

**Reason:** Existing exact-head receipts already cover that retained composition. Issue #397 requires current canonical-upstream evidence. The runtime could not transfer the exact Salsa tree or Debian source archive into the shell environment.

**Evidence:** `TESTS.md` records DNS failures for Git and archive download; issue #212 and PR #220 record green exact-head receipts.

**Alternatives considered:**

- rerun the old matrix solely to create a fresh timestamp;
- use the package-version mirror as canonical base;
- infer Salsa `master` from the release tag.

**Consequences:**

- no fresh execution result is claimed;
- the first incomplete step remains exact canonical checkout and patch application;
- evidence stays useful to the next worker.

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

`ACTIVE` as of 2026-08-01. Exact current canonical base and blob, clean current-source application/regeneration, current-source focused and native tests, exact live Salsa overlap search, and complete-diff review remain.
