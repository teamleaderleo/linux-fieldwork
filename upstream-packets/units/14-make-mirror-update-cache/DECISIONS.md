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

**Decision:** Use canonical upstream `main` commit `77ec9be5417ee44c96343d2347145585da1b1f94` as the initial base and `make_mirror.sh` blob `6c4be092edcf23b56b63a3befe238c099c45f590` as the source identity.

**Reason:** The official repository page identified that `main` head, while the current source view and Debian dgit source identified the exact blob. The blob matches the Linux Fieldwork import used by the retained tests, so no source rebase edit is required.

**Evidence:** `SOURCE_MAP.md` and `TESTS.md`.

**Alternatives considered:**

- use a Debian release tarball as the base;
- use the Linux Fieldwork import without confirming upstream head;
- use a historical component PR base.

**Consequences:**

- the candidate starts from a confirmed canonical source identity;
- a hosted canonical clone can refresh the exact head while retaining the blob discriminator.

**Reopen trigger:** canonical `main` or the `make_mirror.sh` blob changes before final candidate creation.

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

- a canonical Forgejo-compatible branch or accepted patch route remains the delivery prerequisite;
- no public action occurs before explicit authorization.

**Reopen trigger:** upstream contribution guidance requires another delivery method.

**Authority effect:** External-contact state remains false; no submission is authorized.

---

## 2026-08-01 — preserve downstream master and use dedicated controlled branches

**Decision:** Leave `teamleaderleo/mmdebstrap` `master` unchanged. Use dedicated Linux Fieldwork branches for the patch carrier, canonical upstream snapshot, and source candidate.

**Reason:** The GitHub repository has independent downstream history through commit `574048f2a720057b75e56622003932f344dc700a`. Replacing `master` would erase that lineage. Its `make_mirror.sh` blob is nevertheless byte-identical to the confirmed canonical source, so it was safe for the first guarded source construction while a canonical-history snapshot job was prepared.

**Evidence:** controlled base blob `6c4be092edcf23b56b63a3befe238c099c45f590`; carrier branch `linux-fieldwork/unit-14-make-mirror-update-cache`; first source candidate `c94132e344f97cee95901623552df6bcde5039bb`.

**Alternatives considered:**

- force-update `master` to canonical upstream;
- treat downstream repository ancestry as canonical;
- create a separate GitHub repository.

**Consequences:**

- user-owned downstream history remains intact;
- staging and evidence are isolated under explicit branch names;
- final candidate ancestry must come from a canonical Forgejo clone, not from downstream `master`.

**Reopen trigger:** the repository owner explicitly chooses to repurpose `master` as a pure upstream mirror.

**Authority effect:** Internal controlled-repository work only; external-contact state remains false.

---

## 2026-08-01 — require an exact-candidate dynamic receipt

**Decision:** Adapt the retained Linux Fieldwork lifecycle modules to consume the already-patched source candidate and execute candidate-facing cases on the exact candidate blob.

**Reason:** Component CI proved the two provenance patches, while the collapsed source commit needed its own dynamic identity gate. Reusing the tested model logic avoids a second behavioral implementation while excluding predecessor-only cases and obsolete intermediate-source assertions.

**Evidence:** controlled receipt `linux-fieldwork/unit-14-candidate-matrix-receipt.md`; source head `c94132e344f97cee95901623552df6bcde5039bb`; blob `7d92a29a05ade7f5da397a1a9d03e601092f9465`; ten tests passed in 3.464 seconds.

**Alternatives considered:**

- rely only on component PR #286/#324 CI;
- copy the five test modules into the controlled fork;
- run a complete network mirror build as the first candidate gate.

**Consequences:**

- the collapsed candidate has direct worker-ownership, signal, precedence, cleanup, and rerun evidence;
- a project-native regression and selected native entry point remain distinct review/package questions;
- the full mirror build remains optional until the focused native gate is selected.

**Reopen trigger:** candidate source changes, adapter review finds a semantic mismatch, or a native regression contradicts the retained matrix.

**Authority effect:** Internal hosted testing only; no canonical-upstream contact occurred.

## Final disposition

`ACTIVE` on 2026-08-01. The composed source candidate and exact-candidate ten-case lifecycle matrix are complete. The current canonical-history sync job, project-native regression decision, smallest upstream-native gate, final overlap review, canonical delivery route, and explicit authorization remain before `READY FOR AUTHORIZATION`.
