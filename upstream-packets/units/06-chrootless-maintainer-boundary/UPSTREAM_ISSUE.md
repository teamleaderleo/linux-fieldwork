# Draft upstream issue — chrootless maintainer-script environment and executable authority

Status: draft only; external contact unauthorized.

## Summary

In chrootless mode, package maintainer scripts execute as host processes. The current released source passes the caller environment and executable search path into those scripts through direct and apt-managed dpkg launches.

A purpose-built package demonstrated that fake credential variables and host-session socket paths reached `postinst`, and the script connected to a fake inherited agent socket. Caller-controlled leading PATH entries also selected harmless fake commands.

## Proposed boundary

A complete correction would:

- reject commonly credential-bearing environment names and credential-bearing proxy/index URLs at chrootless launch, with names-only diagnostics and a dedicated explicit override;
- retain apt's environment for repository/proxy compatibility;
- run direct and apt-managed chrootless dpkg through a small explicit environment;
- derive and validate `TMPDIR=<target>/tmp`, creating it with mode 01777 when absent and rejecting symlink/non-directory targets;
- use apt's configured non-empty `DPkg::Path` as maintainer-script PATH;
- invoke the sanitizer through validated `/usr/bin/env`;
- preserve mmdebstrap-owned noninteractive debconf, C.UTF-8 locale, reproducibility, QEMU, and conditional fakeroot state;
- document that chrootless package scripts remain host-executing code.

## Distinguishing controls

- ambient baseline exposes fake credential/session values and fake socket access;
- removing target TMPDIR assignment reproduces host `/tmp` creation;
- copying caller PATH into the small environment executes a fake inner dpkg/helper;
- using bare `env` executes a fake outer sanitizer;
- candidate direct and apt-managed paths bypass both fake layers and preserve expected package state;
- symlink/non-directory target temporary paths fail closed;
- cleanup and immediate rerun succeed.

## Compatibility notes

Apt keeps its existing environment. The explicit package-script environment preserves values mmdebstrap sets itself. An explicitly empty apt `DPkg::Path` fails before maintainer-script execution because inheriting caller PATH recreates the defect.

This correction provides defense in depth. It does not sandbox package scripts or remove same-user host access.

## Requested discussion

Please advise whether this boundary and the fail-closed empty-`DPkg::Path` behavior fit the project's intended chrootless contract. A four-commit patch series and transaction fixtures are available after current-master rebase and authorization.