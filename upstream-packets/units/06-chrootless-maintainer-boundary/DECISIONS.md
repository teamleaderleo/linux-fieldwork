# Decisions

## 2026-08-01 — Keep one upstream unit with four ordered patches

Decision: retain environment refusal/scrubbing, target TMPDIR, configured `DPkg::Path`, and absolute `/usr/bin/env` in one submission unit.

Reason: all four govern the same maintainer-script launch boundary and overlap one helper plus two call sites. Each incomplete intermediate state has a demonstrated losing fixture. Four commits preserve review clarity while the complete series preserves correctness.

Reopen trigger: current upstream has adopted one or more components in a way that leaves a clean independent subset.

## 2026-08-01 — Derive target TMPDIR inside the boundary helper

Decision: use `$root/tmp`, reject symlink/non-directory, create when absent, and enforce 01777.

Reason: copying arbitrary caller TMPDIR violates containment; relying only on distant `run_setup()` ordering leaves the local invariant implicit. The helper owns the environment it emits.

Supersedes: the narrow PR #73 allowlist-only framing.

## 2026-08-01 — Use apt's configured non-empty `DPkg::Path`

Decision: save `DPkg::Path` before mmdebstrap extends its own host-side PATH and fail closed when the configured value is undefined or empty.

Reason: inheriting caller PATH recreates the confirmed executable-authority defect. Component filtering introduces ambiguous policy and check/use races.

Compatibility note: this deliberately diverges from apt's empty-path inheritance behavior at the chrootless package-script boundary.

## 2026-08-01 — Use validated `/usr/bin/env`

Decision: validate existence, regular-file type, and executability, then invoke `/usr/bin/env` directly in direct and apt-managed paths.

Reason: bare `env` lets caller PATH select the program before sanitization begins.

Platform boundary: Debian/Linux. Reopen for a supported platform where `/usr/bin/env` is absent or has a different contract.

## 2026-08-01 — Preserve only mmdebstrap-owned locale/debconf state

Decision: describe and test the explicit forced noninteractive debconf controls and C.UTF-8 locale variables, rather than claiming arbitrary caller locale or `DEBCONF_*` preservation.

Reason: carrier review established that mmdebstrap owns these values before dpkg launch. Broad caller-state claims exceed the evidence and weaken the scrub.

## 2026-08-01 — Retain patches instead of modifying imported source

Decision: keep upstream product work below `patches/` and leave `upstream/mmdebstrap/mmdebstrap` unchanged on the unit branch.

Reason: the packet must rebase onto exact canonical current upstream. The imported source is evidence and a historical composition base, not the final destination branch.

## 2026-08-01 — Hold current-master claims until exact identity is fetched

Decision: record released/imported `6fde999741f4fe1e7bf38079acf29432ef87a35e` and mark current Salsa `master` unresolved.

Reason: the project page and released source were accessible; branch API/raw master and direct clone were unavailable in this execution environment. Guessing that master equals the released tag would corrupt the rebase record.

## 2026-08-01 — External-contact state remains closed

Decision: no Salsa issue/MR, Debian BTS message, email, comment, review, or other upstream contact.

Reason: issue #397 authorizes internal work only until explicit authorization.