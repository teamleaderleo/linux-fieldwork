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

**Delivery state:** `Debian BTS patch or follow-up`, or maintainer-selected Salsa delivery, only after authorization.

## 2026-08-01 — accept the deterministic minimal sysroot

**Decision:** Use a created 16-CPU CPU/NUMA tree instead of copying the host's complete live sysfs.

**Reason:** The bounded fixture reproduces the exact allocator diagnostic twice, while the broad copier encountered unreadable power attributes in GitHub's container.

**Negative control:** Allocation sizing can make the stale pointer evade immediate reuse. Keep a losing control and avoid threshold claims.

## 2026-08-01 — current disposition

**Decision:** `HOLD` on candidate actual-binary execution, native package tests, and a minimal stable source delta.

**Evidence already cleared:**

- actual trixie baseline reproduction;
- exact source unpack and quilt result;
- canonical patch zero-fuzz application;
- patched binary-package build;
- cleanup and baseline rerun.

**Clearing condition:** A retained candidate matrix demonstrates valid text/JSON compatibility and clean malformed-input behavior, followed by native tests and a `2.41-5+deb13u1`-style source debdiff.

**Authority effect:** Internal work remains authorized. External contact remains unauthorized.

## Reopen and stop triggers

- Debian publishes an equivalent trixie fix;
- candidate execution changes valid output or still aborts;
- package-native tests require adjacent changes;
- a separate cgroup-mount carrier is supplied;
- external-contact authority changes.
