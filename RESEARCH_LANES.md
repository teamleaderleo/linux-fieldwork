# Research Lanes

## In simple words

This is the short working index for choosing formal Linux Fieldwork lanes. The full inventory of 34 possibilities lives in [`programmes/registry.yml`](programmes/registry.yml). Ten lanes currently have dedicated directories because their questions and first probes are clear enough to scout.

## Immediate current-CI lanes

1. [LF-02 — chrootless `DPKG_ROOT` containment](programmes/rootless-execution/lanes/LF-02-chrootless-dpkg-root-containment/brief.md)
2. [LF-07 — maintainer-script interruption and idempotency](programmes/debian-packages/lanes/LF-07-maintainer-script-interruption-idempotency/brief.md)
3. [LF-12 — reproducible package variance](programmes/debian-packages/lanes/LF-12-reproducible-package-variance/brief.md)
4. [LF-14 — archive extraction and metadata contracts](programmes/filesystems-images/lanes/LF-14-archive-extraction-metadata-contracts/brief.md)
5. [LF-23 — cancellation, subprocess, and file-descriptor cleanup](programmes/services-resources/lanes/LF-23-cancellation-subprocess-fd-cleanup/brief.md)
6. [LF-11 — merged-`/usr` path assumptions](programmes/debian-packages/lanes/LF-11-merged-usr-path-assumptions/brief.md)

## Capability-check lanes

7. [LF-03 — rootless ownership and idmapped mounts](programmes/rootless-execution/lanes/LF-03-rootless-ownership-idmapped-mounts/brief.md)
8. [LF-15 — OverlayFS copy-up and metadata behavior](programmes/filesystems-images/lanes/LF-15-overlayfs-copy-up-metadata/brief.md)
9. [LF-22 — cgroup v2 delegation and cleanup](programmes/services-resources/lanes/LF-22-cgroup-v2-delegation-cleanup/brief.md)

## VM lane

10. [LF-20 — systemd stop, timeout, and descendant cleanup](programmes/services-resources/lanes/LF-20-systemd-stop-timeout-descendant-cleanup/brief.md)

## Programmes

- [`Rootless execution, namespaces, and mounts`](programmes/rootless-execution/STATUS.md)
- [`Debian packages, transactions, and builds`](programmes/debian-packages/STATUS.md)
- [`Filesystems, archives, and disk images`](programmes/filesystems-images/STATUS.md)
- [`Services, processes, and resources`](programmes/services-resources/STATUS.md)
- [`Security and networking boundaries`](programmes/security-networking/STATUS.md)
- [`Boot, devices, and deeper kernel work`](programmes/boot-kernel/STATUS.md)

## Selection rule

Choose a lane whose formal brief fits the available environment. Begin with source and test mapping. Open an investigation only when the probe has distinguishing outcomes and a meaningful consequence.

Keep registry-level possibilities in the registry until they meet the lane promotion rule. See [`programmes/README.md`](programmes/README.md) and the [2026-07-30 selection record](research/rounds/2026-07-30-linux-landscape/selection.md).