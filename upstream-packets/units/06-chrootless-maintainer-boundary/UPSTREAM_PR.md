# Draft upstream merge request — harden chrootless maintainer-script boundary

Status: draft only; external contact unauthorized. Rewrite exact base/head and results after current-upstream execution.

## Summary

This series made the chrootless dpkg/maintainer-script launch boundary explicit for both direct Essential installation and apt-managed package installation.

It:

1. rejected credential-like launch environments with names-only diagnostics and a dedicated override;
2. kept apt's environment while running dpkg and package scripts through `env -i` with mmdebstrap-owned state;
3. derived and validated `<target>/tmp` for package temporary files;
4. used apt's configured non-empty `DPkg::Path` for maintainer-script command lookup;
5. invoked the sanitizer through validated `/usr/bin/env`;
6. documented the remaining host-execution boundary.

## Why

Chrootless maintainer scripts previously inherited caller credentials, session endpoints, socket paths, and caller-prefixed executable lookup. Clearing the environment alone also caused ordinary temporary-file helpers to fall back to host `/tmp`. Canonicalizing only the inner PATH still left the outer `env` executable selected through caller PATH.

The four commits close those linked intermediate defects while preserving apt repository and proxy behavior.

## Commit organization

1. `sanitize chrootless maintainer environment`
2. `use target-contained package temporary directory`
3. `use configured dpkg path for maintainer scripts`
4. `use absolute chrootless environment wrapper`

## Behavior

- unsafe variable names and credential-bearing proxy/index URLs cause a launch error that prints names only;
- `--skip=check/chrootless/environment` bypasses launch refusal while dpkg remains scrubbed;
- apt retains its ambient environment;
- package scripts receive target `TMPDIR`, configured PATH, mmdebstrap's noninteractive debconf and C.UTF-8 locale values, reproducibility controls, QEMU state, and fakeroot state when active;
- target `tmp` symlink/non-directory cases fail closed and an absent directory is created with mode 01777;
- an empty configured `DPkg::Path` fails before package-script execution;
- direct and apt-managed paths use the same helper contract and validated `/usr/bin/env`.

## Validation

Replace this section with exact current candidate results before any submission.

Required gates:

- zero-fuzz ordered application to exact current master;
- Perl syntax and project formatting;
- credential/session names-only rejection and value redaction;
- apt-only proxy/auth preservation;
- direct and apt-managed environment receipts;
- target-TMPDIR mutation and cleanup/rerun;
- fake outer env mutation;
- fake inner dpkg/helper mutation;
- explicit empty `DPkg::Path` refusal;
- `tests/chrootless` and `tests/chrootless-fakeroot`;
- non-chrootless control;
- source restoration and cleanup.

## Explicit non-goals

This series does not disable or replace dpkg's system configuration files. Dpkg may still read `/etc/dpkg/dpkg.cfg.d/*` and `/etc/dpkg/dpkg.cfg`; command-bearing `pre-invoke`, `post-invoke`, and `status-logger` settings therefore remain active. Linux Fieldwork has a separate reproducer for that boundary. A complete correction appears to require either a dpkg configuration-selection interface or a separately reviewed fail-closed mmdebstrap policy.

This series also does not change APT's shutdown/sleep inhibitor policy. That path has its own exact APT controls and compatibility decision.

## Limits

Chrootless package scripts still execute on the host and can access same-user host resources through other paths. Variable-name detection cannot cover every secret representation. The absolute wrapper path currently targets Debian/Linux `/usr/bin/env`. System dpkg configuration and host setup-hook authority remain outside this patch series.