# Decision log

## 2026-08-01 — keep setup and cleanup in one upstream unit

**Decision:** Submit the setup and cleanup changes together.

**Reason:** Setup creates the action target and transfers cleanup authority through the marker. Cleanup consumes that authority. Either half alone leaves an out-of-root action path.

**Evidence:** Issue #164, PR #179, `SOURCE_MAP.md`, and the mixed-marker regressions.

**Alternatives considered:**

- setup-only containment;
- cleanup-only marker validation;
- separate pull requests for each hook.

**Consequences:**

- one complete lifecycle invariant is reviewed at once;
- the diff touches two small shell files;
- rollback or acceptance applies to one coherent behavior.

**Reopen trigger:** Upstream requests independent review units and accepts a temporary intermediate state with an explicitly bounded risk.

**Authority effect:** Internal composition only; external-contact state remains false.

---

## 2026-08-01 — compose the three local repair increments into one upstream patch

**Decision:** Retain one fresh upstream-path patch in the packet while preserving the original three-patch history in the investigation.

**Reason:** The local series records discoveries: initial containment, terminal source-symlink compatibility, and parent-component reachability. The upstream reviewer benefits from the final source contract without incremental context fuzz or superseded intermediate behavior.

**Evidence:** Mechanical application receipt and fresh-diff hash in `TESTS.md`.

**Alternatives considered:**

- submit the three patches unchanged;
- squash only patches 2 and 3;
- rewrite local investigation history.

**Consequences:**

- public artifact is one 6,707-byte patch;
- local review history remains available;
- upstream commit organization can still change after maintainer feedback.

**Reopen trigger:** Upstream contribution guidance or maintainer preference requires a multi-commit series.

**Authority effect:** Internal patch preparation only.

---

## 2026-08-01 — reject every configured parent component

**Decision:** Refuse any `..` component in a configured file-repository path.

**Reason:** Lexical normalization can create a contained destination while the original URI remains unreachable because pathname traversal must first enter an absent intermediate component.

**Evidence:** `test_file_mirror_automount_parent_component_reachability.py` predecessor differential and `test_file_mirror_automount_source_normalization.py` controls.

**Alternatives considered:**

- normalize every parent component;
- create missing predecessor directories;
- rewrite APT configuration to the normalized path.

**Consequences:**

- deterministic fail-closed behavior;
- a small compatibility restriction for unusual textually normalizable URIs;
- ordinary paths, dot components, repeated separators, and terminal source symlinks remain supported.

**Reopen trigger:** A demonstrated real configuration requires parent components and supplies a safe, reachable compatibility contract.

**Authority effect:** None.

---

## 2026-08-01 — preserve terminal source-symlink URI spelling

**Decision:** Use the canonical host source for the action and the normalized configured URI path for the destination.

**Reason:** APT continues to request the configured path inside the generated root. Mapping both identities to the canonical host path breaks a valid terminal source symlink.

**Evidence:** PR #179 repair review and source-symlink setup/cleanup/rerun regression.

**Alternatives considered:**

- reject all source symlinks;
- rewrite APT configuration;
- create an in-root compatibility symlink.

**Consequences:**

- valid source symlinks remain usable;
- source and destination trust rules stay explicit;
- GNU `realpath -m -s` becomes an explicit dependency.

**Reopen trigger:** Upstream rejects the dependency or defines a different URI canonicalization contract.

**Authority effect:** None.

---

## 2026-08-01 — full marker preflight before cleanup actions

**Decision:** Validate the complete NUL-delimited marker before the first destructive action, then revalidate each entry immediately before acting.

**Reason:** Sequential validation and action can partially clean a root before a later invalid entry is discovered.

**Evidence:** `test_file_mirror_automount_cleanup_preflight.py` in root and fakechroot modes.

**Alternatives considered:**

- validate and act entry by entry;
- trust setup-produced markers;
- delete the marker on validation failure.

**Consequences:**

- static invalid marker state causes zero actions;
- failed cleanup retains diagnostic and rerun state;
- pathname replacement after the final check remains a documented race.

**Reopen trigger:** A transaction-oriented descriptor-relative design is selected.

**Authority effect:** None.

---

## 2026-08-01 — target canonical Forgejo repository, pending fork authorization

**Decision:** Record a Forgejo fork and pull request as the proposed delivery path. Keep `NEEDS FORK` until explicit authorization.

**Reason:** The canonical mmdebstrap repository exposes pull requests and remains the source owner. No controlled fork identity is currently established in the packet.

**Evidence:** Current canonical repository inspection and issue #397 authority rules.

**Alternatives considered:**

- Debian BTS patch;
- Salsa-only merge request;
- mailing-list patch series;
- downstream-only package patch.

**Consequences:**

- public drafts can be reviewed internally;
- no external repository mutation occurs during technical preparation.

**Reopen trigger:** Repository owner selects Debian BTS/Salsa or another delivery route.

**Authority effect:** External contact remains unauthorized; none occurred.

## Final disposition

`ACTIVE` as of 2026-08-01. Current-source reconciliation and patch composition are complete. Packet-exact matrix execution, hosted exact-head CI, and final human review remain before `READY FOR AUTHORIZATION`.
