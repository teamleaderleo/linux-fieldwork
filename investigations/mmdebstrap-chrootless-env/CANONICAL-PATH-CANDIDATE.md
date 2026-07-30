# Canonical chrootless maintainer-script PATH candidate

Date: 2026-07-31

Tracking: issue #107. Investigation: PR #105. Candidate: PR #109.

## TL;DR

The inner maintainer-script `PATH` candidate works as designed, while both chrootless launch paths still find the outer `env` sanitizer through caller-controlled `PATH`. Exact head `b52d003cf56ab12bf232dcb6bb47fe8aa7032a9d` retains a tested `/usr/bin/env` repair patch. All relevant exact-head workflows passed. The production source remains at `REPAIR` until that patch is applied and fake-`env` controls run on one clean current-main candidate.

## Explain like I'm five

The program hires a guard to throw away unsafe environment variables. It currently finds the guard by asking the caller where to look. A caller can put a fake guard first.

The repair writes down the real guard's address: `/usr/bin/env`.

## Why care

The canonical inner `PATH` only takes effect after `env` starts. A fake outer `env` can run first, inspect or change the command, and restore caller-controlled lookup. Protecting `dpkg` while leaving the sanitizer executable exposed leaves a hole in the claimed boundary.

## Confirmed baseline

The apt-managed product probe on PR #105 showed that mmdebstrap appends apt's configured `DPkg::Path` to the caller's existing `PATH`, then passes the combined value through the chrootless dpkg boundary. A harmless command present only in a disposable caller directory executed from `postinst`. The clean control did not resolve it.

- Baseline head: `1506982c47b3faa4a44ceec742d939e5de8b500f`.
- Workflow: `30542979455`, success.
- Artifact: `8759472834`.
- Digest: `sha256:95e179066eee3311a112ccce5b9bb5ff5b8361808415295cab0888b1a2d898a8`.

The first baseline run failed in the shell carrier before mmdebstrap execution and carries no product result.

## Inner PATH candidate

The current source stores apt's configured `DPkg::Path` before mmdebstrap appends it to the caller path for its own host-side tool discovery.

`chrootless_dpkg_environment()` then receives the selected root and that stored path. It:

- requires a defined, non-empty path;
- supplies `PATH=<DPkg::Path>` through `env -i`;
- supplies target-derived `TMPDIR=<target>/tmp`;
- preserves mmdebstrap-owned debconf and locale values, reproducibility controls, QEMU state, and conditional fakeroot state;
- is used by direct `run_essential()` and apt-managed `run_install()`.

Apt itself retains the caller environment and combined host-side path so repository authentication, proxying, and apt helpers keep their existing boundary.

## Outer-wrapper defect

Exact source review found that both chrootless launch paths still resolve the sanitizer through caller-influenced `PATH`:

```perl
ARGV => [
    'env',
    chrootless_dpkg_environment(...),
```

and:

```perl
'-oDir::Bin::dpkg=env',
```

The current source therefore protects inner `dpkg` lookup while leaving the outer sanitizer caller-controlled.

## Why this repair

The retained repair uses one explicit absolute wrapper and validates existence, regular-file type, and executable mode.

This wins the design tiebreaker because it:

- removes caller `PATH` from wrapper selection;
- gives direct and apt-managed paths one authority;
- fails with a named error when the expected wrapper is unavailable;
- avoids owner/writability filtering and its check-then-use ambiguity;
- avoids silently substituting a different inner `PATH` when apt explicitly configures an empty value;
- commits the reviewed source state instead of relying on a later self-modifying workflow.

## Historical precedent

- APT's configured non-empty `DPkg::Path` is the established inner-path authority.
- Merged target-TMPDIR work showed that environment cleaning must preserve program-derived values required by supported modes.
- Issue #130 showed why reusable probes should use guarded disposable copies and leave imported source clean.
- Earlier PR #109 review showed that a workflow promising to mutate the branch later cannot validate the exact source currently under review.

## Retained repair patch

Helper B added:

```text
investigations/mmdebstrap-chrootless-env/0001-use-absolute-env-wrapper.patch
```

The patch introduces `chrootless_env_path()` with `/usr/bin/env` as the explicit authority. It requires the path to exist, be a regular file, and be executable. Both direct `run_essential()` and apt-managed `run_install()` use that absolute path. Non-chrootless apt execution keeps its existing `Dir::Bin::dpkg=env` behavior.

`tests/test_mmdebstrap_chrootless_env_wrapper_patch.py` applies the patch to an exact temporary source copy and requires:

- clean patch application;
- existence, regular-file, and executable checks;
- direct chrootless use of `chrootless_env_path()`;
- apt-managed chrootless use of the same helper;
- retained inner `env -i`, canonical `PATH`, and target `TMPDIR` behavior;
- passing Perl syntax.

A direct application check caught one malformed unified-diff hunk count. The carrier was repaired before exact-head CI.

The repair stays a retained patch until candidate/mutation controls exercise fake `env` in both launch paths. The imported source remains unchanged by this review unit.

## APT path authority

APT documents `DPkg::Path` as the string used for `PATH` when it runs dpkg. Since apt 1.8 its default is:

```text
/usr/sbin:/usr/bin:/sbin:/bin
```

APT also permits an explicitly empty `DPkg::Path`, meaning apt leaves inherited `PATH` unchanged.

- APT NEWS: <https://sources.debian.org/src/apt/3.0.3/debian/NEWS>
- apt.conf(5): <https://manpages.debian.org/unstable/apt/apt.conf.5.en.html>

The current inner-PATH candidate deliberately rejects an empty value in chrootless mode:

```text
cannot determine chrootless maintainer-script PATH
```

This preserves the issue #107 boundary and requires an explicit configured path for host-executed chrootless maintainer scripts.

## Earlier evidence

Exact tested head `cdcf7f04259638596abe02b4d8897541e47e3f02` supplied `/usr/sbin:/usr/bin:/sbin:/bin` to candidate and clean runs. Neither resolved the disposable caller command. A one-line mutation restored `PATH=$ENV{PATH}` and reproduced caller-command execution.

- Workflow: `30544183531`, success.
- Artifact: `8759979312`.
- Digest: `sha256:6eaf2dbd49de64d858ad5825c5cc4ec4e5bf43773705009b623d02d606419ee9`.

That evidence supports the inner PATH direction. It predates the outer-wrapper finding and cannot close it.

## Exact-head validation

At `b52d003cf56ab12bf232dcb6bb47fe8aa7032a9d`:

- Linux Fieldwork CI `30580762410`: success;
- direct chrootless PATH `30580762487`: success;
- apt-managed PATH precedence `30580762416`: success;
- chrootless environment security `30580762484`: success;
- explicit TMPDIR `30580762425`: success;
- TMPDIR deep review `30580762411`: success.

The LF-23 cancellation workflow was correctly skipped as unrelated.

These runs validate the retained patch carrier, current probes, and existing inner candidate. They do not validate product source with `/usr/bin/env` applied.

## Current controls

PR #109 includes:

- tainted and clean apt-managed package transactions;
- a one-line caller-PATH mutation;
- expected-tool lookup for `dpkg`, `ldconfig`, `start-stop-daemon`, and `update-rc.d`;
- explicit non-empty and empty `APT_CONFIG` `DPkg::Path` controls;
- a local-repository `--variant=essential` direct-path probe;
- runtime-parent negative controls;
- source-copy and repository-cleanliness assertions;
- credential/environment, explicit TMPDIR, deep-review, formatter, and repository CI gates;
- the retained absolute-wrapper patch and patch-execution regression.

## Related situations worth checking

This defect class appears whenever a sanitizer or privilege-boundary helper is found through the state it intends to restrict. Follow-up searches should cover:

- bare `env`, `sudo`, `chroot`, shells, and interpreters before environment cleanup;
- `command -v` after caller path augmentation;
- configured helper paths whose empty value falls back to inherited state;
- direct and package-manager-mediated launch paths with different wrapper authority;
- tests that plant a fake inner command while forgetting the outer wrapper.

## Remaining repair gates

1. Apply the retained patch to production candidate source on a clean current-main branch.
2. Add candidate and mutation controls with a fake leading-path `env` for direct and apt-managed paths.
3. Exercise missing, non-regular, and non-executable absolute-wrapper controls.
4. Require a successful direct essential transaction as a distinct gate.
5. Rerun canonical `DPkg::Path`, explicit `APT_CONFIG`, TMPDIR, credential, formatter, parity, and repository gates on one exact head.
6. Review the complete current-main diff independently.

## Disposition

`REPAIR`

The inner PATH design is retained. The outer wrapper remains caller-controlled in current product source. The exact repair patch and regression provide the next bounded implementation unit.

## Authority

Internal Linux Fieldwork candidate only. No Debian bug, email, merge request, or upstream comment is authorized or made.
