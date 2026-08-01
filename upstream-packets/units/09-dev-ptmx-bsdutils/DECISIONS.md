# Decisions

## 2026-08-01 — Keep unit 09 bounded to one test dependency

**Decision:** add `bsdutils` only to the generated-root include set in `tests/dev-ptmx`.

**Reason:** the recovered transcript identifies the first unavailable operation as inner-root `script(1)`. The provider and missing selection are exact. Runtime code and broader package-test harness behavior lie outside this owner.

**Supersedes:** provisional hypotheses in early issue `#53` comments involving adduser, mount hardening, mirror state, package-universe drift, and namespace behavior.

## 2026-08-01 — Preserve PR #89 as validated internal evidence

**Decision:** treat merged PR `#89` head `9db9f4d9ae423a5c0dbd2255c05decf14fbe9d66` and CI run `30539827917` as the canonical existing static validation.

**Reason:** PR `#86` carried the same five files with diverged 23-commit history and was explicitly superseded. PR `#89` rebuilt the candidate on current main and received an accepting exact-head review.

## 2026-08-01 — Produce an upstream-rooted patch in the unit packet

**Decision:** retain `patches/0001-tests-include-bsdutils-for-dev-ptmx.patch` with path `tests/dev-ptmx`.

**Reason:** the earlier internal patch targets `upstream/mmdebstrap/tests/dev-ptmx`, which is correct for Linux Fieldwork regression but unsuitable as a direct upstream patch.

## 2026-08-01 — Require exact current-head application before authorization

**Decision:** keep state `ACTIVE` until the patch applies with zero fuzz and zero offset to upstream head `77ec9be5417ee44c96343d2347145585da1b1f94`, or a fresher verified head.

**Reason:** this environment could read the official repository page but DNS resolution prevented a canonical clone or raw-file fetch. The local imported source still matches the known defect, yet direct current-head byte evidence remains preferable before external delivery.

## 2026-08-01 — Keep current-sid named execution as an open gate

**Decision:** run `dev-ptmx --mode=root --variant=apt` through the disposable sid carrier and repeat after cleanup before moving to `READY FOR AUTHORIZATION`.

**Reason:** historical ownership is proven and the static candidate is green. Dynamic execution confirms the current package universe and catches drift in the test fixture or harness.

## 2026-08-01 — Use a Forgejo fork and pull request

**Decision:** intended delivery is a fork of `josch/mmdebstrap` and a pull request against `main`.

**Current prerequisite:** `NEEDS FORK`.

**Authority:** external creation, comment, issue, pull request, email, or other contact requires explicit authorization.
