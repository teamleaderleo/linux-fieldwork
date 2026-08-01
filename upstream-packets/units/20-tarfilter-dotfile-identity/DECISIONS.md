# Decision log

## 2026-08-01 — split unit 20 from the combined path-matching carrier

**Decision:** Retain a standalone three-file patch for dotfile matching.

**Reason:** PR #33 and the earlier investigation patch combine unit 20 with no-option passthrough, sparse handling, and parent metadata retention. The dotfile defect has an independent source hunk and focused regression.

**Evidence:** Issue #38; PR #33 head `32a92eec0aed327dfad4e1ca0df51f6168b80a48`; `SOURCE_MAP.md`; complete retained patch.

**Consequences:** Unit 18 keeps no-option passthrough. Unit 21 keeps parent metadata retention. Unit 20 changes no tuple format and no parent-prefix logic.

**Authority effect:** Internal work only; external contact remains unauthorized.

---

## 2026-08-01 — parse complete prefixes instead of normalizing components

**Decision:** Consume leading `/` and `./` tokens in a loop.

**Reason:** This preserves `.config`, `..name`, `...name`, and `../config` while retaining intended archive-prefix handling. It also handles alternating spellings such as `/./.config`.

**Alternatives rejected:**

- `lstrip("./")` — aliases names by deleting filename dots and parent components.
- `posixpath.normpath()` — collapses path components beyond the intended matching-key conversion.
- the earlier `while startswith("./"); lstrip("/")` order — leaves alternating `/./` prefixes partly unnormalized.

**Evidence:** Baseline exit 1; candidate and clean rerun exit 0; `DEEP_DIVE.md`; `artifacts/`.

**Authority effect:** Internal implementation decision only.

---

## 2026-08-01 — use upstream test ownership

**Decision:** Add `tests/tarfilter-path-dotfiles` and register it in `coverage.txt`.

**Reason:** A source-only patch would leave the regression outside the project's runner. The shell test follows existing `tests/tarfilter-idshift` command selection and uses Python to construct exact archive names.

**Evidence:** Retained patch; candidate receipt; clean rerun receipt.

**Authority effect:** No external publication authorized.

---

## 2026-08-01 — current disposition

**Decision:** `ACTIVE`.

**Reason:** The focused patch, negative control, candidate pass, clean rerun, complete diff review, upstream draft, and overlap search exist. A complete current-upstream checkout and registered `coverage.py` invocation remain unexecuted, and a controlled upstream fork is absent.

**Reopen trigger for disposition:** A passing `CMD=./mmdebstrap ./coverage.py tarfilter-path-dotfiles` run on upstream main `77ec9be5417ee44c96343d2347145585da1b1f94`, followed by exact fork/branch identity and final diff review, can advance the unit toward `READY FOR AUTHORIZATION`.

**Authority effect:** External contact remains unauthorized.
