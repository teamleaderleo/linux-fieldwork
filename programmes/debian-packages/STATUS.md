# Debian Packages, Transactions, and Builds

## In simple words

This programme studies package installation as a recoverable state machine: maintainer scripts, dpkg and apt transitions, configuration preservation, triggers, filesystem layout, reproducibility, and foreign architectures.

## Current direction

- **Mapped:** [LF-07 — maintainer-script interruption and idempotency](lanes/LF-07-maintainer-script-interruption-idempotency/brief.md)
- **Mapped:** [LF-11 — merged-`/usr` path assumptions](lanes/LF-11-merged-usr-path-assumptions/brief.md)
- **Mapped:** [LF-12 — reproducible package variance](lanes/LF-12-reproducible-package-variance/brief.md)
- **Inbox:** LF-08 — apt and dpkg transaction recovery
- **Inbox:** LF-09 — conffile and local-change preservation
- **Inbox:** LF-10 — triggers, ordering, and deferred work
- **Inbox:** LF-13 — foreign architecture and binfmt boundaries

## First sequence

Start LF-07 and LF-12 independently. Use LF-11 where bootstrap hooks or package scripts expose path-sensitive behavior. Keep transaction-wide LF-08 behind the smaller maintainer-script probe until the fixture design is proven.

## Candidate targets

`dpkg`, `apt`, `debhelper`, selected Debian packages, `reprotest`, `diffoscope`, `initramfs-tools`, `mmdebstrap`.

## Authority

Programme mapping grants no upstream-contact authority.