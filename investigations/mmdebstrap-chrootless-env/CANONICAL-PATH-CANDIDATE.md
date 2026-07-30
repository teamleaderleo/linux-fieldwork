# Canonical chrootless maintainer-script PATH candidate

Date: 2026-07-30

Tracking: issue #107. Investigation: PR #105. Candidate: PR #109.

## Confirmed baseline

The apt-managed product probe on PR #105 showed that mmdebstrap appends apt's configured `DPkg::Path` to the caller's existing `PATH`, then passes the combined value through the clean chrootless dpkg boundary. A harmless command present only in a disposable caller directory executed from `postinst`. The clean control did not resolve it.

- Baseline head: `1506982c47b3faa4a44ceec742d939e5de8b500f`.
- Workflow: `30542979455`, success.
- Artifact: `8759472834`.
- Digest: `sha256:95e179066eee3311a112ccce5b9bb5ff5b8361808415295cab0888b1a2d898a8`.

The first baseline run failed in the shell carrier before mmdebstrap execution and is not product evidence.

## Candidate design

The candidate stores apt's configured `DPkg::Path` before mmdebstrap appends it to the caller path for its own host-side tool discovery.

`chrootless_dpkg_environment()` then receives the selected root and that stored path. It:

- requires a defined, non-empty path;
- supplies `PATH=<DPkg::Path>` through `env -i`;
- continues to supply target-derived `TMPDIR=<target>/tmp`;
- preserves the existing mmdebstrap-owned debconf and locale values, reproducibility controls, QEMU state, and conditional fakeroot state;
- is used by both direct `run_essential()` and apt-managed `run_install()`.

Apt itself retains the caller environment and combined host-side path so repository authentication, proxying, and apt helpers are not changed by this candidate.

## APT precedent and deliberate incompatibility

APT documents `DPkg::Path` as the string used for the `PATH` environment variable when it runs dpkg. Since apt 1.8 its default is:

```text
/usr/sbin:/usr/bin:/sbin:/bin
```

APT also permits an explicitly empty `DPkg::Path`, meaning that apt does not change the inherited `PATH`.

- APT NEWS: <https://sources.debian.org/src/apt/3.0.3/debian/NEWS>
- apt.conf(5): <https://manpages.debian.org/unstable/apt/apt.conf.5.en.html>

The candidate does **not** reproduce the empty-value behavior in chrootless mode. It fails closed with:

```text
cannot determine chrootless maintainer-script PATH
```

That is a deliberate hardening and reproducibility choice. Falling back to the inherited path would recreate issue #107. Silently substituting a hard-coded path would ignore an administrator's explicit apt configuration. The candidate therefore requires the incompatibility to be documented and tested rather than hidden.

## Apt-managed candidate evidence

Exact tested head: `cdcf7f04259638596abe02b4d8897541e47e3f02`.

The candidate and clean runs both supplied:

```text
/usr/sbin:/usr/bin:/sbin:/bin
```

Neither resolved the disposable caller command. A one-line mutation restored `PATH=$ENV{PATH}` and reproduced caller-command execution. The fixture also required `dpkg`, `ldconfig`, `start-stop-daemon`, and `update-rc.d` to resolve from absolute system paths.

- Workflow: `30544183531`, success.
- Artifact: `8759979312`.
- Digest: `sha256:6eaf2dbd49de64d858ad5825c5cc4ec4e5bf43773705009b623d02d606419ee9`.

The same head passed:

- Linux Fieldwork CI `30544183512`;
- chrootless credential/environment security `30544183499`;
- explicit TMPDIR runtime verification `30544183498`;
- TMPDIR deep review and Perl::Critic `30544183493`.

## Review corrections

1. The first source-transform workflow used indentation-sensitive multiline strings and failed before modifying the source. Exact escaped markers replaced that carrier.
2. Existing TMPDIR unit tests encoded the helper's former one-argument signature and result line. They now assert root plus canonical path, target TMPDIR, empty-path refusal, and both call sites.
3. The candidate test retains a mutation control rather than treating a green candidate transaction alone as proof.
4. Peer review found that the first PATH harness accepted arbitrary non-root runtime parents and chmodded the imported source in place. Both apt-managed and direct probes now use an explicit disposable-parent allowlist, execute preserved runtime copies, and assert source mode and repository cleanliness. Issue #130 tracks the equivalent defects in merged harnesses.
5. The first direct essential-package transaction reached `run_essential()` and proved that the candidate bypassed the caller `dpkg` wrapper, but current sid later failed on known package chrootless limitations. The revised probe records path reach and package outcome separately and runs the caller-PATH mutation despite the shared later failure.

## Exact-head controls now present

The self-contained PR #109 head includes:

- tainted and clean apt-managed package transactions;
- a one-line caller-PATH mutation;
- expected-tool lookup for `dpkg`, `ldconfig`, `start-stop-daemon`, and `update-rc.d`;
- an explicit `APT_CONFIG` with empty `DPkg::Path`, which must fail closed before the fixture package is installed;
- a real `--variant=essential` direct-path probe with a caller `dpkg` wrapper and mutation;
- runtime-parent negative controls;
- source-copy and repository-cleanliness assertions;
- the existing credential/environment, explicit TMPDIR, deep-review, formatter, and repository CI gates.

These controls are listed here as present, not as passed, until the exact-head workflows complete.

## Anti-patterns avoided

- Do not filter path components by owner or writability at startup. That creates policy ambiguity and check-then-use windows.
- Do not keep the caller prefix merely because apt needs its environment. Apt and dpkg are separate execution boundaries.
- Do not silently hard-code a fallback for an explicitly empty apt setting.
- Do not describe canonical PATH as isolation. Maintainer scripts still execute on the host.
- Do not claim parity from selected log lines. Use the imported root-versus-chrootless and fakeroot comparisons before merge.
- Do not let an evidence harness recursively delete beneath an arbitrary parent or mutate imported source merely to execute it.

## Remaining merge gates

1. Complete the exact-head apt-managed, empty-path, and direct `run_essential()` workflows.
2. Run the imported root-versus-chrootless comparison on representative variants.
3. Run the imported chrootless-fakeroot comparison.
4. Exercise foreign-architecture/QEMU behavior if available.
5. Verify non-chrootless modes remain unchanged.
6. Review the final exact head independently.

## Authority

Internal Linux Fieldwork candidate only. No Debian bug, email, merge request, or upstream comment is authorized or made.
