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

## 2026-08-01 — Use the user GitHub fork as a downstream implementation carrier

**Decision:** create `teamleaderleo/mmdebstrap:linux-fieldwork/unit-09-dev-ptmx-bsdutils` from `master` head `574048f2a720057b75e56622003932f344dc700a` and commit the one-line source correction at `43082a6bc959e2d7cefae48f52e045cc90869287`.

**Evidence:** the base `tests/dev-ptmx` blob equals the Linux Fieldwork import blob `ca1cde040f945fe871f904ef6a56e040b6a5c9ea`. The candidate blob is `fa93b4b845ff4927a72f258364bd920e8c7dc573`. GitHub compare reports one commit, one file, one insertion, and one deletion.

**Boundary:** the repository head matches `deepin-community/mmdebstrap` and carries downstream `1.5.7-3` packaging history. It is a valid Debian-package execution carrier, not proof of canonical upstream freshness.

## 2026-08-01 — Treat missing mailing-list and canonical-main patches as a rebase risk

**Decision:** keep the canonical overlap gate open even though the downstream candidate is exact and minimal.

**Reason:** the controlled GitHub fork has Deepin downstream ancestry, while canonical mmdebstrap uses Forgejo `main`. Equivalent fixes, later test edits, or mailing-list-carried patches may exist outside the GitHub history. Final delivery must rebase or reapply against verified canonical bytes.

## 2026-08-01 — Add a packet-specific exact-blob regression

**Decision:** commit `tests/test_upstream_packet_unit_09_dev_ptmx_bsdutils.py` and execute it through draft internal PR `#402`.

**Reason:** the test independently reproduces both exact Git blob identities, applies the upstream-rooted packet patch to a fresh tree, rejects fuzz and offset, requires one changed line, and preserves every customize hook. This connects the durable packet to the controlled fork commit without relying on network checkout.

## 2026-08-01 — Require canonical current-head application before authorization

**Decision:** keep state `ACTIVE` until the patch applies with zero fuzz and zero offset to canonical head `77ec9be5417ee44c96343d2347145585da1b1f94`, or a fresher verified head, after overlap review.

**Reason:** this environment can read the official repository page but DNS resolution prevents canonical clone or raw-file fetch. The downstream carrier proves the candidate against Debian `1.5.7-3`; direct canonical byte evidence remains required for an upstream pull request.

## 2026-08-01 — Keep current-sid named execution as an open gate

**Decision:** run `dev-ptmx --mode=root --variant=apt` through the unit-08 disposable sid carrier and repeat after cleanup before moving to `READY FOR AUTHORIZATION`.

**Reason:** historical ownership is proven and the static candidate is green. Debian sid still carries `mmdebstrap 1.5.7-3`, making the controlled carrier relevant to current package execution. Dynamic execution confirms the current package universe and catches harness drift.

## 2026-08-01 — Preserve final delivery on canonical Forgejo

**Decision:** the GitHub downstream branch is staging and evidence only. Intended final delivery remains a fork of `josch/mmdebstrap` and a pull request against canonical `main`.

**Authority:** external creation, comment, issue, pull request, email, or other contact requires explicit authorization. Draft Linux Fieldwork PR `#402` is internal coordination and CI only.
