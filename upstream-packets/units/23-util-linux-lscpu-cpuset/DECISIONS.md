# Decision log

## 2026-08-01 — canonical carriers define the unit scope

**Decision:** Treat unit 23 as the util-linux `ul_path_cpuparse()` caller-visible cpuset ownership defect retained by PR #387, rather than a new cgroup-mount ownership implementation.

**Reason:** PR #387, issue #234, PR #239, util-linux issues #3641/#4401, and commits `4581ede...`/`3cd5f1d...` all concern a freed cpuset pointer left non-NULL after parse failure. None contains an owning-cgroup-mount mechanism.

**Evidence:** `SOURCE_MAP.md`; Linux Fieldwork PR #387 merge `4a2196a705c06f5604879f655d465a4ac6fcb198`; upstream commit `4581ede384f22983d6155768635ce43cb5304cb0`.

**Alternatives considered:**

- start a broad new cgroup-mount investigation from the stale issue title;
- split a new unit without a linked source defect or reproducer.

**Consequences:**

- this packet follows exact carrier evidence;
- a genuinely separate cgroup-mount defect requires new carriers and an issue #397 boundary correction.

**Reopen trigger:** issue #397 links an exact source owner, failure, and carrier for the cgroup-mount wording.

**Authority effect:** internal scope only; external-contact state unchanged.

---

## 2026-08-01 — retire a new util-linux upstream implementation

**Decision:** Send no competing util-linux source patch.

**Reason:** canonical commit `4581ede...` is already present in current master and stable/v2.40, v2.41, and v2.42 source. The original reporter confirmed the correction.

**Evidence:** current source heads and blobs in `SOURCE_MAP.md`; util-linux issue #3641 confirmation; issue #4401 maintainer statement.

**Alternatives considered:**

- re-submit the same patch upstream;
- change final `lscpu` cleanup;
- expand malformed CPU-list acceptance.

**Consequences:**

- upstream implementation work is retired;
- remaining work is package adoption only.

**Reopen trigger:** a maintained util-linux branch loses the correction or a distinct source defect appears.

**Authority effect:** no upstream contact is useful or authorized.

---

## 2026-08-01 — select Debian trixie as the remaining plausible destination

**Decision:** Focus subsequent technical work on Debian trixie stable `util-linux 2.41-5`.

**Reason:** trixie still publishes `2.41-5`; upstream `v2.41` lacks `*set = NULL`; the published Debian `2.41-5` quilt series contains no match for `cpuset`, `lib/path.c`, or `4581ede`. Debian testing and unstable carry newer fixed upstream releases.

**Evidence:** Debian package and sources URLs in `SOURCE_MAP.md`; upstream `v2.41` blob `42a33ffc53752ba5e00aed2396ca9a4fc876c1ef`.

**Alternatives considered:**

- retire the unit because testing/unstable moved forward;
- target current util-linux stable branches;
- target an unspecified 2.40 downstream without an exact package identity.

**Consequences:**

- the unit has a concrete downstream package target;
- the package conclusion remains an inference until exact source unpack and build verification.

**Reopen trigger:** trixie publishes a fixed package, exact source unpack reveals an equivalent correction, or another maintained affected package receives a stronger exact identity.

**Authority effect:** package inspection and local builds remain authorized; Debian contact remains unauthorized.

---

## 2026-08-01 — retain canonical authorship and one-patch composition

**Decision:** Reuse the canonical upstream patch unchanged as the sole source patch.

**Reason:** the one-file free-then-NULL correction is complete, reporter-confirmed, stable-backported, and passes the retained exact-fixture matrix.

**Evidence:** `patches/0001-clear-cpuset-output-after-error.patch`; `artifacts/2026-08-01-focused-regression.txt`.

**Alternatives considered:**

- rewrite patch metadata;
- create a Debian-specific source implementation;
- pad or alter the minimal fixture to force zero hunk offset.

**Consequences:**

- original authorship and commit identity remain intact;
- Debian-specific changes are limited to package metadata and series integration;
- fixture hunk offset remains acceptable with zero fuzz and exact-byte precheck.

**Reopen trigger:** the patch conflicts with Debian's effective source or package tests reveal a required adjacent change.

**Authority effect:** retained patch testing only; no send authorization.

---

## 2026-08-01 — hold on package-level execution

**Decision:** Set unit state to `HOLD`.

**Reason:** exact Debian `2.41-5` source unpack, effective-source verification, canonical patch application, package build/test, issue #4401 fixture execution, ordinary-output controls, and clean rerun remain unexecuted.

**Evidence:** `TESTS.md` unexecuted gates and `HANDOFF.md` first incomplete step.

**Alternatives considered:**

- mark `READY FOR AUTHORIZATION` from source archaeology alone;
- mark `RETIRED` because upstream is fixed;
- create a public Debian report before package verification.

**Consequences:**

- the next worker has one bounded technical lane;
- no external authorization decision is requested yet.

**Reopen trigger:** a complete package-level receipt demonstrates baseline/candidate distinction and compatibility, or exact package inspection disproves the inferred gap.

**Authority effect:** external contact remains unauthorized.

## Final disposition

`HOLD` — 2026-08-01. The canonical source fix and current upstream adoption are settled. Debian trixie stable `util-linux 2.41-5` is the remaining plausible destination, pending exact package-level execution.
