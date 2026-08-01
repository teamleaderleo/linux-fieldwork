# Decision log

## 2026-07-31 — canonical component carriers

**Decision:** Use merged PR #286 for worker ownership, terminating results, once-only cleanup, and base precedence; use merged PR #324 for first-signal retention through cleanup. Treat PRs #238, #259, #260, #267, and #305 as historical construction carriers.

**Reason:** #286 and #324 are the landed exact-head generations with successful hosted CI and the final retained test set.

**Evidence:** PR #286 CI `30624335126` / 842; PR #324 CI `30630467076` / 916; `SOURCE_MAP.md`.

**Reopen trigger:** unique source or regression evidence is found outside the canonical components.

**Authority effect:** Internal routing only; external contact remains unauthorized.

---

## 2026-07-31 — one composed source correction

**Decision:** Collapse the two internal patches into one final source commit while retaining both provenance patches.

**Reason:** The cleanup-time refinement depends on the finalizer introduced by the first repair and edits the same source block. Sending the first repair alone would publish a known intermediate defect.

**Evidence:** packet patch `patches/0001-update-cache-worker-lifecycle.patch`, SHA-256 `980720d262d0f5d4a568be54851e144652ae6d882a8ad0e8aa228c8ffed2ae42`.

**Alternatives considered:** two source commits; first repair only; broad composition with top-level proxy ownership.

**Consequences:** The source behavior is reviewed as one invariant. The native regression remains a separate second commit.

**Reopen trigger:** upstream requests a split source sequence.

**Authority effect:** Draft organization only.

---

## 2026-07-31 — exclude broader cancellation supervision

**Decision:** Keep issue #263 / PR #264 outside unit 14.

**Reason:** Prompt cancellation of unowned foreground descendants requires broader process-group or supervisor ownership for an unmeasured latency problem. The selected unit fixes false success, wrong-owner cleanup, duplicate cleanup, result replacement, and retained state.

**Reopen trigger:** measured harmful APT cancellation latency or an accepted supervisor/group contract.

**Authority effect:** Scope only.

---

## 2026-08-01 — preserve downstream master

**Decision:** Leave `teamleaderleo/mmdebstrap` `master` at `574048f2a720057b75e56622003932f344dc700a`. Use dedicated Linux Fieldwork branches.

**Reason:** `master` carries independent downstream history. Replacing it would destroy user-owned lineage. Its relevant source blob matched canonical upstream, allowing a guarded staging build while a canonical snapshot was created.

**Evidence:** base blob `6c4be092edcf23b56b63a3befe238c099c45f590`; staging source head `c94132e344f97cee95901623552df6bcde5039bb`.

**Alternatives considered:** force-update `master`; treat downstream ancestry as canonical; create another GitHub repository.

**Consequences:** `master` remains intact. The final candidate uses canonical Forgejo ancestry instead.

**Reopen trigger:** repository owner explicitly repurposes `master` as a pure mirror.

**Authority effect:** Internal controlled-repository work only.

---

## 2026-08-01 — canonical Forgejo history is the candidate base

**Decision:** Mirror current Forgejo `main` to `linux-fieldwork/upstream-main-snapshot` and build the candidate directly on it.

**Reason:** This removes the staging repository ancestry caveat while preserving the exact public upstream commit graph.

**Evidence:** canonical snapshot `77ec9be5417ee44c96343d2347145585da1b1f94`; canonical sync receipt; source commit `b2a9a09b36fd13f22a024ebf8522ac58543eac28`.

**Consequences:** The final branch is directly comparable to canonical upstream: two commits ahead, zero behind.

**Reopen trigger:** canonical `main` advances or `make_mirror.sh` changes before submission.

**Authority effect:** Read-only canonical clone and controlled-fork writes only.

---

## 2026-08-01 — require exact-candidate dynamic proof

**Decision:** Adapt the retained Linux Fieldwork matrices to consume the already-patched candidate source and run candidate-facing cases on the exact candidate blob.

**Reason:** Component CI proved the provenance series; the collapsed candidate required a direct identity gate.

**Evidence:** canonical sync receipt; ten cases passed in 3.459 seconds on source blob `7d92a29a05ade7f5da397a1a9d03e601092f9465`.

**Consequences:** Ownership, INT/QUIT/TERM, cleanup-time signals, precedence, state removal, and rerun are tied to the final source commit.

**Reopen trigger:** source commit changes or the adapter is shown to select a different mechanism.

**Authority effect:** Internal hosted testing only.

---

## 2026-08-01 — include a project-native regression

**Decision:** Add `tests/make-mirror-update-cache-worker-lifecycle` and register it in `coverage.txt` as the second candidate commit.

**Reason:** The upstream unit needs a maintained project-side discriminator. The focused test can run without APT, root, QEMU, network, or a complete mirror cache.

**Evidence:** native test receipt; candidate head `76728bbb8e084b54261713ba80762cd6f6ada79a`; direct output `make_mirror update_cache worker lifecycle: PASS`.

**Executed gates:** `sh -n`, shellcheck, upstream shfmt options, direct execution, and `git diff --check`.

**Consequences:** The final candidate contains two commits and three paths. A complete mirror generation remains outside the focused gate.

**Reopen trigger:** upstream requests a different regression location or the full harness contradicts direct execution.

**Authority effect:** Internal candidate work only.

---

## 2026-08-01 — canonical delivery remains authorization-bound

**Decision:** Keep GitHub as controlled staging/evidence. Create a Forgejo-compatible fork/branch or use an accepted patch route only after explicit authorization.

**Reason:** A GitHub branch cannot itself become a cross-host Forgejo pull request. The exact candidate is preserved and ready to transfer without further source work.

**Evidence:** `UPSTREAM_PR.md`; candidate head `76728bbb...`.

**Alternatives considered:** open a public Forgejo fork/PR now; submit a public issue; email the patch.

**Consequences:** No upstream-visible write occurs in this pass.

**Reopen trigger:** explicit authorization or project contribution guidance selecting another route.

**Authority effect:** External contact remains false; none occurred.

## Final disposition

`ACTIVE` on 2026-08-01. Source implementation, canonical rebase, zero-fuzz application, exact-candidate dynamic matrix, project-native regression, cleanup/rerun, complete diff review, and final draft are complete. The classified live overlap receipt is the first incomplete technical routing gate. A clean receipt would leave only explicit authorization and canonical delivery setup.
