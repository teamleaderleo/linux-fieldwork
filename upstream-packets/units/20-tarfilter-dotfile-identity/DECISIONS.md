# Decision log

## 2026-08-01 — split unit 20 from the combined path-matching carrier

**Decision:** Retain a standalone three-file upstream patch for dotfile matching identity.

**Reason:** PR #33 and the earlier investigation patch combine unit 20 with no-option passthrough, sparse handling, and parent metadata retention. The dotfile defect has an independent source hunk and focused regression.

**Evidence:** Issue #38; PR #33 head `32a92eec0aed327dfad4e1ca0df51f6168b80a48`; `SOURCE_MAP.md`; complete retained patch.

**Consequences:** Unit 18 keeps no-option passthrough. Unit 21 keeps parent metadata retention. Unit 20 changes no path-filter tuple format and no parent-prefix logic.

**Authority effect:** Internal work only; external contact remains unauthorized.

---

## 2026-08-01 — replace character-set stripping with complete leading-token parsing

**Decision:** Consume complete leading `/` and `./` tokens, preserve a real first component, map a remaining lone `.` to archive root, and prepend one `/`.

**Reason:** This wins the direct defect, repeated-prefix controls, parent-component controls, and archive-root controls without entering internal component normalization.

**Alternatives rejected:**

- `lstrip("./")` — aliases names by deleting filename dots and parent components.
- one optional `./` removal followed by slash stripping — leaves repeated prefixes partly unparsed.
- `posixpath.normpath()` — collapses internal `.` and `..` components beyond the unit boundary.
- the first looping candidate without a root case — maps `.`, `./.`, and `/.` to `/.` instead of `/`.

**Evidence:** `DEEP_DIVE.md`; `scripts/test_normalization_mutations.py`; `artifacts/normalization-mutations.json`; GNU tar root-alias receipt.

**Authority effect:** Internal implementation decision only.

---

## 2026-08-01 — narrow the dpkg compatibility claim

**Decision:** Claim native dpkg compatibility for ordinary package members spelled `./path`. Describe repeated and alternating leading-prefix handling as a GNU-tar consumer identity extension.

**Reason:** A real dpkg 1.22.22 differential filters `./.config` and `./config` as expected, while bare `.config` and repeated `././.config` extract to the same pathname but fall outside dpkg's native filter match. GNU tar 1.35 consumes the repeated leading spellings as one pathname.

**Evidence:** `scripts/probe_dpkg_path_filters.py`; `artifacts/dpkg-path-filter-differential.json`; `scripts/probe_tar_path_aliases.py`; `artifacts/gnu-tar-path-aliases.json`.

**Consequences:** Upstream text must avoid saying every tested odd spelling is exactly dpkg behavior.

**Authority effect:** No publication authorization.

---

## 2026-08-01 — preserve archive-root identity

**Decision:** Map `.`, `./`, `./.`, `/.`, `/./`, repeated slashes, and equivalent leading forms to the matching key `/`.

**Reason:** GNU tar treats those directory members as extraction root, and current upstream already maps them to `/`. The first replacement candidate changed that behavior.

**Evidence:** GNU tar probe and the root-alias assertions in `tests/tarfilter-path-dotfiles`.

**Consequences:** Root-marker regression is now a mandatory negative control.

**Authority effect:** Internal implementation repair.

---

## 2026-08-01 — hold internal dot-component normalization as a successor question

**Decision:** Leave `foo/./.config` unchanged in the matching key for unit 20.

**Reason:** GNU tar consumes it as `foo/.config`, but implementing that behavior requires whole-path component policy. `posixpath.normpath()` also collapses `..`, making a broad change unsafe without a dedicated matrix.

**Evidence:** `artifacts/gnu-tar-path-aliases.json`; losing `posixpath.normpath()` mutation.

**Consequences:** Record the residual and a reopen trigger. Do not smuggle whole-path normalization into the dotfile patch.

**Authority effect:** No new public issue or upstream contact.

---

## 2026-08-01 — bind the regression to the checkout executable

**Decision:** Select the executable in this order: explicit `MMTARFILTER`, checkout `./tarfilter`, system `/usr/bin/mmtarfilter`.

**Reason:** The earlier order could execute a host package instead of the candidate copied by `coverage.py`.

**Evidence:** Current `tests/tarfilter-path-dotfiles`; exact workflow passes an explicit candidate path for direct execution.

**Consequences:** A green test now identifies the executable authority unambiguously.

**Authority effect:** Internal evidence correction.

---

## 2026-08-01 — separate text applicability from Git mode preservation

**Decision:** Use `patch --dry-run --fuzz=0` for offset/fuzz detection and `git apply --check` plus `git apply` for the actual candidate. Assert the new test is executable.

**Reason:** GNU `patch` applies text but does not reliably preserve `new file mode 100755`. The upstream unit is a Git-hosted pull request, so Git patch semantics own the actual application.

**Evidence:** `.github/workflows/unit-20-tarfilter-dotfile-identity.yml`.

**Consequences:** Exact execution cannot pass with an unreadable or non-executable registered test.

**Authority effect:** Internal test and packaging decision.

---

## 2026-08-01 — cancel superseded exact-head workflow generations

**Decision:** Add branch-scoped workflow concurrency with `cancel-in-progress: true`.

**Reason:** Multiple semantic and documentation pushes created queued exact-head generations. Superseded heads should not consume the unit's execution lane.

**Evidence:** Workflow run numbers reached 10 before final documentation; earlier generations remained queued.

**Consequences:** Future pushes retain only the newest branch generation within the concurrency group.

**Authority effect:** Internal CI behavior only.

---

## 2026-08-01 — current disposition

**Decision:** `ACTIVE`.

**Reason:** The candidate, broad negative controls, dpkg and GNU tar differentials, exact workflow, complete upstream diff boundary, internal review PR, and residual-risk register exist. The final exact-head workflow has yet to complete and its artifacts have yet to be retained in the packet.

**Advance discriminator:** One exact final head must pass canonical identity checks, current baseline loss, direct candidate, registered `coverage.py` test, patch transport, formatting, cleanup/rerun, cross-context probes, complete-diff review, and overlap recheck.

**Reopen triggers:** Upstream source movement, active equivalent work, exact-run failure, maintainer incompatibility feedback, or evidence that internal dot-segment handling belongs in the same coherent patch.

**Authority effect:** External contact remains unauthorized.
