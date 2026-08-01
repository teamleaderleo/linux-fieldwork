# Decisions

## 2026-08-01 — Keep unit 09 bounded to one test dependency

**Decision:** add `bsdutils` only to the generated-root include set in `tests/dev-ptmx`.

**Reason:** the recovered transcript identifies the first unavailable operation as inner-root `script(1)`. The provider and missing selection are exact. Runtime code and broader package-test harness behavior lie outside this owner.

**Supersedes:** provisional hypotheses in early issue `#53` comments involving adduser, mount hardening, mirror state, package-universe drift, and namespace behavior.

## 2026-08-01 — Preserve PR #89 as validated internal evidence

**Decision:** retain merged PR `#89` head `9db9f4d9ae423a5c0dbd2255c05decf14fbe9d66` and CI run `30539827917` as the original static validation.

**Reason:** PR `#86` carried diverged history and was explicitly superseded. PR `#89` rebuilt the candidate on current Linux Fieldwork main and received an accepting exact-head review.

## 2026-08-01 — Produce an upstream-rooted patch

**Decision:** retain `patches/0001-tests-include-bsdutils-for-dev-ptmx.patch` with path `tests/dev-ptmx`.

**Reason:** the earlier internal patch targets the Linux Fieldwork import prefix and is unsuitable as a direct upstream carrier.

## 2026-08-01 — Use the user GitHub fork as a downstream implementation carrier

**Decision:** create `teamleaderleo/mmdebstrap:linux-fieldwork/unit-09-dev-ptmx-bsdutils` from `master` head `574048f2a720057b75e56622003932f344dc700a` and commit the one-line source correction at `43082a6bc959e2d7cefae48f52e045cc90869287`.

**Evidence:** baseline blob `ca1cde040f945fe871f904ef6a56e040b6a5c9ea`; candidate blob `fa93b4b845ff4927a72f258364bd920e8c7dc573`; compare is one commit, one file, one insertion, one deletion.

**Boundary:** this fork follows `deepin-community/mmdebstrap` and Debian `1.5.7-3` packaging history. It is a valid package-execution carrier and does not establish canonical Forgejo ancestry.

## 2026-08-01 — Treat GitHub mirror freshness as unresolved

**Decision:** no accessible GitHub repository may stand in for canonical Forgejo `main`.

**Evidence:** the newest inspected GitHub fork, `RubisetCie/mmdebstrap`, has unrelated local commits after the same Deepin base and still carries baseline blob `ca1cde...`. No GitHub repository contains advertised canonical commit `77ec9be5417ee44c96343d2347145585da1b1f94`.

**Consequence:** mailing-list, Debian-series, and Forgejo-history overlap review remains mandatory before external delivery.

## 2026-08-01 — Accept exact packet static validation

**Decision:** accept Linux Fieldwork run `30690010699` at packet head `a4303b4bf3c02fb4acfc16337e53b68b08626862` as the exact packet regression result.

**Evidence:** patch validation, Python compilation, complete repository unit suite, shell syntax, and command-help checks passed. The regression requires exact baseline/candidate Git blobs, zero fuzz/offset, one changed line, and unchanged customize hooks.

## 2026-08-01 — Accept current-sid dynamic confirmation and rerun

**Decision:** treat runs `30690241513` and `30690452822` as positive current-sid execution and rerun evidence for the candidate.

**Evidence:** both disposable sid containers ran installed `mmdebstrap 1.5.7-3` with `bsdutils 1:2.42.2-2`. Root and unshare `dev-ptmx` cases passed in both runs, both inner `script` hooks printed `foobar`, copied logs contained no missing-command signature, `/tmp/test.c` and `/tmp/log` were removed, and mmdebstrap removed each temporary root.

**Wrapper interpretation:** autopkgtest returned status `2` because the unrelated `hint-testsuite-triggers` entry was skipped. The selected `testsuite` result was `PASS` in both artifacts.

**Preferred receipt:** run `30690452822`, artifact `8815724078`, digest `sha256:897189064d42e06367ab652f590eb5827388dce8d883c042f079e49a7662273e`, because the unit patch applied as an independent fifth zero-fuzz/zero-offset carrier.

## 2026-08-01 — Close the full-cache execution carrier

**Decision:** close internal draft PR `#403` as superseded.

**Reason:** it produced the needed current-sid double pass but spent most of its execution budget building the complete package-test mirror. Its red controls and positive artifacts are retained in the packet.

## 2026-08-01 — Retain direct PR #407 as optional cleaner confirmation

**Decision:** leave draft PR `#407` queued as an internal refinement, not a prerequisite for ownership or dynamic confirmation.

**Purpose:** seed sid `InRelease`, use the public Debian mirror directly, run only `coverage.py --exitfirst --mode=root --variant=apt dev-ptmx`, and record explicit residual mount/file/process checks with a zero-status wrapper.

## 2026-08-01 — Move unit 09 to HOLD on canonical-source access

**Decision:** unit state becomes `HOLD`.

**Single blocker:** exact canonical Forgejo `main` bytes and history are unavailable in this execution environment.

**Discriminator:** fetch advertised head `77ec9be5417ee44c96343d2347145585da1b1f94` or a fresher verified head, inspect `tests/dev-ptmx` and mailing-list-carried overlap, then apply the packet patch with zero fuzz and zero offset.

- Equivalent correction already present: retire the external submission.
- Dependency still absent and patch applies cleanly: prepare the canonical fork branch and move to `READY FOR AUTHORIZATION`.
- Test intent changed: reopen the ownership analysis.

## 2026-08-01 — Preserve final delivery on canonical Forgejo

**Decision:** the GitHub downstream branch is staging and evidence only. Intended final delivery remains a fork of `josch/mmdebstrap` and a pull request against canonical `main`.

**Authority:** external creation, comment, issue, pull request, email, or other contact requires explicit authorization. No mmdebstrap or Debian upstream contact occurred.
