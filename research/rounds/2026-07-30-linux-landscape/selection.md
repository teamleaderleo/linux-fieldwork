# First Lane Selection

## In simple words

Ten lanes received formal directories because their questions and first probes are clear enough to scout. The other 24 remain visible in the programme registry until source reading, environment access, or related work justifies deeper mapping.

## Immediate current-CI lanes

- [LF-02 — chrootless `DPKG_ROOT` containment](../../../programmes/rootless-execution/lanes/LF-02-chrootless-dpkg-root-containment/brief.md)
- [LF-07 — maintainer-script interruption and idempotency](../../../programmes/debian-packages/lanes/LF-07-maintainer-script-interruption-idempotency/brief.md)
- [LF-11 — merged-`/usr` path assumptions](../../../programmes/debian-packages/lanes/LF-11-merged-usr-path-assumptions/brief.md)
- [LF-12 — reproducible package variance](../../../programmes/debian-packages/lanes/LF-12-reproducible-package-variance/brief.md)
- [LF-14 — archive extraction and metadata contracts](../../../programmes/filesystems-images/lanes/LF-14-archive-extraction-metadata-contracts/brief.md)
- [LF-23 — cancellation, subprocess, and file-descriptor cleanup](../../../programmes/services-resources/lanes/LF-23-cancellation-subprocess-fd-cleanup/brief.md)

## Capability-check lanes

- [LF-03 — rootless ownership and idmapped mounts](../../../programmes/rootless-execution/lanes/LF-03-rootless-ownership-idmapped-mounts/brief.md)
- [LF-15 — OverlayFS copy-up and metadata behavior](../../../programmes/filesystems-images/lanes/LF-15-overlayfs-copy-up-metadata/brief.md)
- [LF-22 — cgroup v2 delegation and cleanup](../../../programmes/services-resources/lanes/LF-22-cgroup-v2-delegation-cleanup/brief.md)

## VM lane

- [LF-20 — systemd stop, timeout, and descendant cleanup](../../../programmes/services-resources/lanes/LF-20-systemd-stop-timeout-descendant-cleanup/brief.md)

## Selection logic

The mapped set combines:

- direct use of the existing `mmdebstrap` import;
- package lifecycle and reproducibility work that fits disposable roots;
- reusable archive and cancellation fixtures;
- three capability-dependent Linux interfaces;
- one high-value VM lane for service ownership.

A good active mix is one package lane, one rootless or filesystem lane, and one process-lifecycle lane. Open an investigation only after the formal brief survives source reading and the first probe has distinguishing outcomes.