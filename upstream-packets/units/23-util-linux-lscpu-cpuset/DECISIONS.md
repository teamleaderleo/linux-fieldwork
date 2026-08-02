# Decision log

## 2026-08-01 — correct the unit boundary to the canonical carriers

**Decision:** Treat unit 23 as cpuset output ownership after parse failure. Preserve the cgroup-mount phrase only as a mismatch requiring separate carriers.

**Reason:** PR #387, issue #234, PR #239, util-linux issues #3641/#4401, and commits `4581ede...`/`3cd5f1d...` all identify `ul_path_cpuparse()` and contain no mount-selection change.

**Consequence:** This packet does not invent a second defect.

## 2026-08-01 — retire a new upstream util-linux implementation

**Decision:** Reuse canonical commit `4581ede384f22983d6155768635ce43cb5304cb0` with original authorship.

**Reason:** Upstream master and maintained stable branches already own the correction, and the original reporter confirmed it.

**Rejected alternatives:** final-cleanup suppression, parser-policy expansion, replacement allocation, and a competing source fix.

## 2026-08-01 — select Debian trixie as the remaining package lane

**Decision:** Focus package work on trixie `util-linux 2.41-5`.

**Reason:** Testing and unstable advanced to fixed releases. Exact trixie source and the installed binary remain affected. No current util-linux proposed-update displaces the lane.

**Delivery state:** Debian BTS patch or follow-up, or maintainer-selected Salsa delivery, only after explicit authorization.

## 2026-08-01 — accept the deterministic minimal sysroot

**Decision:** Use a created 16-CPU CPU/NUMA tree instead of copying the host's complete live sysfs.

**Reason:** The bounded fixture reproduces the exact allocator diagnostic twice, while the broad copier encountered unreadable power attributes in GitHub's container.

**Negative control:** Allocation sizing can make the stale pointer evade immediate reuse. Keep a losing control and avoid threshold claims.

## 2026-08-02 — candidate actual-binary execution clears

**Decision:** Mark candidate actual-binary execution and valid-output compatibility as complete.

**Evidence:** Linux Fieldwork workflow run `30692256031`, job `91348929951`, completed successfully at requested head `7a82f99ceac6801536c78ba1c2d261bd6f0f3dc8`.

The exact matrix demonstrated:

- baseline valid text/JSON: status 0;
- baseline malformed text/JSON: status 134 with the duplicate-free diagnostic;
- candidate valid text/JSON: status 0;
- candidate malformed text/JSON: status 0;
- baseline and candidate valid text bytes: identical;
- baseline and candidate valid JSON bytes: identical.

Artifact `8817069887` has digest `sha256:2b544b399e779bbf577ade1e99249436879fa928b639c5026f116044b461ac25`.

**Consequence:** Candidate execution is no longer a hold reason.

## 2026-08-02 — retain the controlled-fork native regression

**Decision:** Keep the controlled util-linux fork regression as internal test evidence, not as a new upstream implementation proposal.

**Evidence:** `teamleaderleo/util-linux` workflow run `30691835019`, job `91347815601`, passed autogen, focused configure/build, and `tests/ts/lscpu/cpuset-parse-failure` at head `95ebc67e521195741040ffebb58756b259fb69b2`.

**Reason:** Upstream source ownership is already settled. The useful remaining upstream-shaped contribution is regression coverage and downstream package adoption.

## 2026-08-02 — classify the sampled qemu red as infrastructure

**Decision:** Do not treat the sampled armv7 qemu red as source evidence.

**Evidence:** Job `91347815797` reached and passed source build/test work, then failed pulling `multiarch/qemu-user-static` because Docker Hub returned HTTP 429 unauthenticated pull-rate limiting.

**Boundary:** Other red qemu jobs require their own log-level confirmation before receiving the same classification.

## 2026-08-02 — continue HOLD for package composition

**Decision:** Keep unit state `HOLD`.

**Current hold reasons:**

- the relevant complete native util-linux `lscpu` suite has not been retained on the patched Debian tree;
- a Debian stable-update quilt/changelog source delta has not been composed;
- a source package and source debdiff against `2.41-5` have not been retained;
- the exact actual-binary matrix has not been rerun from that final source-package composition.

**Clearing condition:** Produce a minimal stable-update source delta, run the relevant native/package tests, build source and binary packages, retain the source debdiff, and rerun the exact matrix cleanly.

**Authority effect:** Internal work remains authorized. External contact remains unauthorized.

## Reopen and stop triggers

- Debian publishes an equivalent trixie fix;
- the final package composition changes valid output or still aborts;
- package-native tests identify an adjacent required correction;
- a separate cgroup-mount carrier is supplied;
- external-contact authority changes.
