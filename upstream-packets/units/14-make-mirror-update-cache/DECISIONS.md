# Decision log

## 2026-07-31 — select PR #286 and PR #324 as canonical components

**Decision:** Treat merged PR #286 as the canonical ownership/once-only finalizer component and merged PR #324 as the canonical cleanup-time signal-retention component. PRs #238, #259, #260, #267, and #305 remain historical construction carriers.

**Reason:** #286 and #324 are the landed exact-head generations with successful hosted CI, complete reviews, and the final retained test set. Earlier carriers contain stale ancestry, intermediate repairs, or superseded routing.

**Evidence:** `SOURCE_MAP.md`; PR #286 CI `30624335126` / 842; PR #324 CI `30630467076` / 916.

**Alternatives considered:**

- use PR #267 as the canonical first repair;
- use PR #305 as the cleanup-signal carrier;
- reconstruct from the original stacked PR #238.

**Consequences:**

- evidence citations use the merged component heads;
- historical carriers are read for unique failure and packaging history only;
- no stale branch becomes an upstream base.

**Reopen trigger:** a missing unique source or regression blob is discovered outside #286/#324.

**Authority effect:** Internal routing only; external-contact state remains false.

---

## 2026-07-31 — compose the two internal patches into one upstream patch

**Decision:** Submit the complete worker lifecycle as one source patch, while retaining the two internal patches as provenance.

**Reason:** Patch 0002 depends on the finalizer introduced by patch 0001 and edits the same source block. Submitting patch 0001 alone would present a known cleanup-time signal gap. One patch lets upstream review the final invariant without accepting an intermediate state.

**Evidence:** `DEEP_DIVE.md`; packet patch `patches/0001-update-cache-worker-lifecycle.patch`; digest `980720d262d0f5d4a568be54851e144652ae6d882a8ad0e8aa228c8ffed2ae42`.

**Alternatives considered:**

- two ordered commits mirroring PR #286 and PR #324;
- submit only the first ownership repair and defer cleanup-time signals;
- broaden the patch to top-level proxy lifecycle.

**Consequences:**

- the proposed upstream diff touches only `make_mirror.sh`;
- the finalizer and cleanup-signal policy are reviewed together;
- the top-level owner work stays in unit 13.

**Reopen trigger:** upstream requests a two-commit review sequence or the collapsed patch cannot apply cleanly while the provenance series does.

**Authority effect:** Draft organization only; external-contact state remains false.

---

## 2026-07-31 — exclude prompt descendant cancellation

**Decision:** Keep issue #263 / PR #264 outside unit 14 and preserve its source-expansion hold.

**Reason:** The accepted worker lifecycle eventually reports cancellation and cleans correctly. Prompt PID-only cancellation of unowned foreground descendants requires process-group or supervisor ownership across ordinary commands and pipelines. The retained research found that larger mechanism disproportionate without measured harmful latency or an accepted dependency contract.

**Evidence:** issue #263 and PR #264 exact head `257d05eb91bc6e5a83e16a38f0c2e255c1792371`.

**Alternatives considered:**

- add `setsid`/group signaling to this patch;
- supervise every worker child and pipeline stage;
- rely on caller process-group isolation.

**Consequences:**

- no new dependency or process-group contract enters this unit;
- this unit claims eventual correct status/cleanup, not prompt descendant termination.

**Reopen trigger:** a real or faithful APT workload demonstrates materially harmful latency, or upstream adopts a supervisor/group contract that lowers the marginal cost.

**Authority effect:** Scope decision only; external-contact state remains false.

---

## 2026-07-31 — pin current upstream base by commit and blob

**Decision:** Use canonical upstream `main` commit `77ec9be5417ee44c96343d2347145585da1b1f94` as the current base and `make_mirror.sh` blob `6c4be092edcf23b56b63a3befe238c099c45f590` as the source identity.

**Reason:** The official repository page identified that `main` head, while the current source view and Debian dgit source identified the exact blob. The blob matches the Linux Fieldwork import used by the retained tests, so no source rebase edit is required.

**Evidence:** `SOURCE_MAP.md` and `TESTS.md`.

**Alternatives considered:**

- use a Debian release tarball as the base;
- use the Linux Fieldwork import without confirming upstream head;
- use a historical component PR base.

**Consequences:**

- the candidate starts from current canonical source;
- full-tree application remains a tooling gate, not a source-drift repair.

**Reopen trigger:** upstream `main` or the `make_mirror.sh` blob changes before candidate branch creation.

**Authority effect:** Public read only; no upstream write or contact occurred.

---

## 2026-07-31 — choose pull request delivery and keep issue draft as fallback

**Decision:** Prepare one upstream pull request; mark the standalone issue draft `NOT NEEDED` unless contribution practice or maintainer feedback requires issue-first discussion.

**Reason:** The defect, fix, bounded compatibility statement, and deterministic regression evidence fit one reviewable source change. A separate issue would duplicate the same material.

**Evidence:** `UPSTREAM_PR.md` and `UPSTREAM_ISSUE.md`.

**Alternatives considered:**

- issue-only report;
- issue followed by pull request;
- patch email.

**Consequences:**

- a controlled Forgejo fork and branch are the next delivery prerequisites;
- no public action occurs before explicit authorization.

**Reopen trigger:** upstream contribution guidance requires another delivery method.

**Authority effect:** External-contact state remains false; no submission is authorized.

## Final disposition

`ACTIVE` on 2026-07-31. The source identity, carrier consolidation, composed patch, compatibility boundary, drafts, and retained evidence are complete. A controlled upstream checkout/branch, full-tree combined-patch application, shell syntax, upstream-native focused gate, and complete one-file diff review remain before `READY FOR AUTHORIZATION`.
