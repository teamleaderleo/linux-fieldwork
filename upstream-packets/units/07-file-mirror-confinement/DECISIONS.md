# Decision log

## 2026-08-01 — keep setup and cleanup in one upstream unit

**Decision:** Keep the setup and cleanup changes together.

**Reason:** Setup creates the action target and transfers cleanup authority through the marker. Cleanup consumes that authority. Either half alone leaves an out-of-root action path.

**Evidence:** Issue #164, PR #179, `SOURCE_MAP.md`, and the mixed-marker regressions.

**Alternatives considered:** setup-only containment; cleanup-only validation; independent submissions.

**Consequences:** One complete lifecycle promise is reviewed at once. The source diff remains two shell files.

**Reopen trigger:** A maintainer requests independent units and accepts a documented intermediate state.

**Authority effect:** Internal work only.

---

## 2026-08-01 — compose three local increments into one upstream patch

**Decision:** Retain one fresh upstream-path patch while preserving the original three-patch investigation history.

**Reason:** The local series records discoveries. The final reviewer benefits from the completed source contract without incremental fuzz or superseded intermediate behavior.

**Evidence:** `TESTS.md` composition receipt and packet-patch SHA-256.

**Alternatives considered:** send all three patches; squash only later repairs; rewrite investigation history.

**Consequences:** The public artifact can be one patch or one logical commit. Local discovery history remains available.

**Reopen trigger:** Contribution guidance or maintainer preference requires a multi-commit series.

**Authority effect:** Internal preparation only.

---

## 2026-08-01 — reject every configured parent component

**Decision:** Refuse any `..` component in a configured file-repository path.

**Reason:** Lexical normalization can create a contained destination while the original URI remains unreachable because pathname traversal first enters an absent intermediate component.

**Evidence:** Parent-component predecessor differential and source-normalization controls.

**Alternatives considered:** normalize every parent component; create missing predecessor directories; rewrite APT configuration.

**Consequences:** Deterministic fail-closed behavior. Ordinary paths, dot components, repeated separators, and terminal source symlinks remain supported.

**Reopen trigger:** A real configuration requires parent components and supplies a safe reachable contract.

**Authority effect:** None.

---

## 2026-08-01 — preserve terminal source-symlink URI spelling

**Decision:** Use the canonical host source for the action and the normalized configured URI path for the destination.

**Reason:** APT continues to request the configured path inside the generated root. Mapping both identities to the canonical source breaks a valid terminal source symlink.

**Evidence:** PR #179 repair review and the source-symlink matrix case.

**Alternatives considered:** reject all source symlinks; rewrite APT configuration; create an in-root compatibility symlink.

**Consequences:** Valid source symlinks remain usable. GNU `realpath -m -s` is an explicit dependency.

**Reopen trigger:** Upstream defines a different URI canonicalization contract or rejects the dependency.

**Authority effect:** None.

---

## 2026-08-01 — preflight the complete marker before cleanup actions

**Decision:** Validate the complete NUL-delimited marker before the first destructive action, then revalidate each entry immediately before acting.

**Reason:** Sequential validation and action can partially clean a root before a later invalid entry is discovered.

**Evidence:** Root and fakechroot preflight/correction/rerun matrix cases.

**Alternatives considered:** validate and act entry by entry; trust setup-produced markers; delete the marker on validation failure.

**Consequences:** Static invalid marker state causes zero actions. Failed cleanup retains diagnostic and rerun state. The check/action pathname race remains documented.

**Reopen trigger:** A descriptor-relative transaction design is selected.

**Authority effect:** None.

---

## 2026-08-01 — use the GitHub fork as a controlled test carrier

**Decision:** Use `teamleaderleo/mmdebstrap` as the controlled implementation carrier for internal validation. Keep the canonical Forgejo repository as the intended upstream destination.

**Reason:** The repository owner created the fork and authorized trying the update against it. Its `master` hook blobs exactly match the packet baseline, allowing a clean candidate branch without source adaptation.

**Evidence:**

- fork base `574048f2a720057b75e56622003932f344dc700a`;
- candidate branch `linux-fieldwork/unit-07-file-mirror-confinement`;
- candidate head `8b8dce6910badeda1e72e28f471fa220a22eea7d`;
- complete comparison: two changed hook files, two commits ahead, zero behind;
- exact candidate hashes and 10-check matrix in `TESTS.md`.

**Alternatives considered:** wait for a canonical Forgejo fork; keep only a patch file; open a GitHub pull request against the downstream mirror.

**Consequences:**

- the candidate now has a concrete controlled branch and exact head;
- internal testing can target committed source bytes;
- the GitHub mirror remains a test carrier, not an upstream submission destination;
- no pull request was created.

**Reopen trigger:** The canonical repository is mirrored into a writable controlled fork or the owner explicitly selects the GitHub mirror as a downstream contribution destination.

**Authority effect:** Branch creation and source commits in the controlled fork were authorized by the user. Upstream contact and pull-request creation remain unauthorized.

## Final disposition

`ACTIVE` as of 2026-08-01. The controlled fork candidate and reusable exact-byte matrix are complete. Hosted exact-head CI, canonical-tree application, final overlap review, and an explicit send decision remain before `READY FOR AUTHORIZATION`.
