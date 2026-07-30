# Source Orientation

These primary and project-maintained references informed the 2026-07-30 landscape round.

## Linux kernel interfaces

- Linux kernel documentation: `https://www.kernel.org/doc/html/latest/`
- Cgroup v2: `https://cdn.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html`
- Filesystem idmappings: `https://www.kernel.org/doc/html/next/filesystems/idmappings.html`
- OverlayFS: `https://www.kernel.org/doc/html/latest/filesystems/overlayfs.html`
- `no_new_privs`: `https://www.kernel.org/doc/html/latest/userspace-api/no_new_privs.html`
- Landlock: `https://cdn.kernel.org/doc/html/latest/userspace-api/landlock.html`
- Kernel networking documentation: `https://www.kernel.org/doc/html/latest/networking/`
- Netlink family specifications: `https://cdn.kernel.org/doc/html/latest/netlink/specs/index.html`
- Device mapper: `https://www.kernel.org/doc/html/latest/admin-guide/device-mapper/index.html`
- dm-verity: `https://www.kernel.org/doc/html/latest/admin-guide/device-mapper/verity.html`
- dm-integrity: `https://docs.kernel.org/admin-guide/device-mapper/dm-integrity.html`

## Debian and packaging

- Debian Policy: `https://www.debian.org/doc/debian-policy/`
- Maintainer scripts and installation procedure: `https://www.debian.org/doc/debian-policy/ch-maintainerscripts.html`
- Source packages and reproducibility: `https://www.debian.org/doc/debian-policy/ch-source.html`
- Debian merged-`/usr`: `https://wiki.debian.org/UsrMerge`
- `mmdebstrap` manual: `https://manpages.debian.org/testing/mmdebstrap/mmdebstrap.1.en.html`
- `update-initramfs` manual: `https://manpages.debian.org/trixie/initramfs-tools/update-initramfs.8.en.html`

## Reproducible builds

- Reproducible Builds documentation: `https://reproducible-builds.org/docs/`
- `SOURCE_DATE_EPOCH`: `https://reproducible-builds.org/docs/source-date-epoch/`

## Systemd

- Systemd manual collection: `https://www.freedesktop.org/software/systemd/man/`
- `systemd-tmpfiles`: `https://www.freedesktop.org/software/systemd/man/systemd-tmpfiles.html`
- Namespace resource delegation: `https://www.freedesktop.org/software/systemd/man/257/systemd-nsresourced.service.html`
- Shutdown logic: `https://www.freedesktop.org/software/systemd/man/254/systemd-halt.service.html`
- `systemd-dissect`: `https://www.freedesktop.org/software/systemd/man/252/systemd-dissect.html`

## Local execution reference

The repository already runs focused verification on Ubuntu 24.04, installs selected dependencies with `sudo apt-get`, and retains result artifacts. See [`../../../.github/workflows/mmdebstrap-unwritable-tmpdir.yml`](../../../.github/workflows/mmdebstrap-unwritable-tmpdir.yml).

## Boundary

These references support source orientation and lane design. Exact behavior claims still require imported revisions, commands, observed output, and an explicit evidence boundary.