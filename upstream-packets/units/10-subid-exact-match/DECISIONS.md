# Decision log

## 2026-08-01 — keep the unit bounded to Debian package-test account detection

**Decision:** Unit 10 changes only the two subordinate-ID presence conditions in `debian/tests/testsuite`.

**Reason:** The false positive occurs before mmdebstrap coverage executes and is owned by Debian’s package-test setup. Runtime numeric UID/GID support, package dependencies, mirror readiness, signals, capability handling, and broad sid orchestration have separate owners and evidence.

**Evidence:** Issue #80, merged PR #92, merged proof PR #291, `SOURCE_MAP.md`, and the current source refresh.

**Alternatives considered:**

- compose with upstream runtime numeric-ID support;
- compose with issue #53’s broad package-test harness;
- include range validation or allocation policy.

**Consequences:**

- one small upstream review unit;
- adjacent failures remain discoverable after this setup correction;
- integration evidence can reuse broader harness work without importing its patches.

**Reopen trigger:** current source moves account setup into another owner or the exact package-test user identity becomes numeric.

**Authority effect:** Internal work only; external-contact state unchanged.

---

## 2026-08-01 — select field parsing plus fixed exact comparison

**Decision:** Use `cut -s -d: -f1 FILE | grep -Fxq -- "$AUTOPKGTEST_NORMAL_USER"` for both subuid and subgid.

**Reason:** This separates record parsing from identity comparison and closes the observed substring, regex, malformed-row, and leading-option cases.

**Evidence:** PR #92 repair history, PR #291 test matrix, `DEEP_DIVE.md`, and the exact imported-source gate in `TESTS.md`.

**Alternatives considered:**

- whole-record grep;
- anchored regular expression;
- `cut` without `-s`;
- an awk-only predicate.

**Consequences:**

- valid exact rows remain unchanged;
- delimiter-free rows cease to count as assignments;
- the append policy and later package-test flow remain unchanged.

**Reopen trigger:** Debian documents a record grammar that `cut -s -d: -f1` cannot represent or current source already provides an equivalent helper.

**Authority effect:** Internal candidate selected; external-contact state unchanged.

---

## 2026-08-01 — retain one commit and one proposed merge request

**Decision:** Keep subuid and subgid corrections in one commit and one proposed Salsa merge request.

**Reason:** They are adjacent implementations of one invariant, use one test matrix, and must remain symmetrical.

**Evidence:** Candidate patch and exact two-line diff fence.

**Alternatives considered:**

- separate commits for subuid and subgid;
- a preparatory helper commit;
- a larger package-test cleanup series.

**Consequences:**

- compact review surface;
- no unrelated cleanup;
- one revert restores prior behavior if required.

**Reopen trigger:** current-base source separates the operations into distinct files or maintainers request a shared helper.

**Authority effect:** No external action authorized.

---

## 2026-08-01 — treat PR #291 as canonical proof and retire intermediate carriers

**Decision:** PR #291 is the durable proof carrier. PRs #215, #218, #225, and #252 are historical/superseded.

**Reason:** PR #291 repairs the malformed hunk found by zero-fuzz enforcement and combines full shell syntax, leading-hyphen behavior, strict line-count/diff fencing, and the complete account matrix on one exact head.

**Evidence:** PR #252 run `30598944690` / 797 and PR #291 run `30624718470` / 845.

**Alternatives considered:**

- cite the earliest green proof only;
- preserve all carriers as equivalent;
- discard the failed zero-fuzz run.

**Consequences:**

- the failed carrier remains useful evidence for patch-packaging ownership;
- future workers start from one canonical proof head;
- stale branch states do not redefine the candidate.

**Reopen trigger:** a newer exact-head proof supersedes PR #291 with broader relevant coverage.

**Authority effect:** Internal evidence routing only.

---

## 2026-08-01 — admit exact source bytes before applying the packet patch

**Decision:** Treat the full imported testsuite as admissible test input only after its Git blob matches `9f4eda87430da38b08a23a50a51e53b22cf7414b`.

**Reason:** A reconstructed excerpt proves the local predicate but cannot detect drift elsewhere in the file or a copy error. Full-file Git identity makes the application and shell-syntax result attributable to the exact recorded Debian 1.5.7-3 source.

**Evidence:** `artifacts/2026-08-01-exact-imported-source-gate.md` and `TESTS.md`.

**Alternatives considered:**

- retain the earlier nine-line synthetic smoke as the strongest current gate;
- trust copied source without checking its blob;
- wait for live Salsa DNS before running any stronger local gate.

**Consequences:**

- the packet now has exact baseline and candidate file blobs;
- Git whitespace checking, mail-patch application, full shell syntax, and the behavior matrix share one admitted source;
- live Salsa drift remains a clearly separate gate.

**Reopen trigger:** the live Salsa file blob differs, the packet patch changes, or the recorded imported source identity is corrected.

**Authority effect:** Internal read/test work only; no external action.

---

## 2026-08-01 — keep the unit ACTIVE pending live current-base and package integration gates

**Decision:** State remains `ACTIVE`.

**Reason:** The exact imported-source gate is green, but direct live Salsa head/blob verification and focused package/user-namespace execution remain.

**Evidence:** `README.md`, `TESTS.md`, the exact-source artifact, and `HANDOFF.md`.

**Alternatives considered:**

- `READY FOR AUTHORIZATION` based on exact imported-source proof;
- `HOLD` on missing network access;
- `RETIRED` due runtime numeric-ID work.

**Consequences:**

- the technical queue has one executable next step;
- no authorization request is premature;
- runtime numeric-ID work stays adjacent;
- the exact imported-source result need not be repeated unless source or patch identity changes.

**Reopen trigger:** completion of the live current-base and focused integration gates, or discovery of equivalent active upstream work.

**Authority effect:** External contact remains false; none occurred.

## Final disposition

`ACTIVE` on 2026-08-01. The exact candidate is proven on the recorded Debian 1.5.7-3 source and is ready for live Salsa identity/application and focused Debian package/user-namespace testing. External contact remains unauthorized.
