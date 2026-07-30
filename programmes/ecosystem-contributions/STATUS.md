# Ecosystem Contributions and Upstream Fixes

## In simple words

This programme turns Linux package collections, runtimes, developer tools, foundational libraries, and system projects into a continuing source of reproducible bug reports, tested patches, and retained technical understanding.

## Current direction

- **Investigating:** [LF-35 — package collection candidate harvesting](lanes/LF-35-package-collection-candidate-harvesting/brief.md)
- **Investigating:** [LF-36 — downstream patch retirement and upstream transfer](lanes/LF-36-downstream-patch-retirement/brief.md)
- **Inbox:** LF-37 — cross-distribution build portability
- **Inbox:** LF-38 — runtime and toolchain distribution regressions
- **Inbox:** LF-39 — foundational-library boundary corpus
- **Inbox:** LF-40 — package metadata, provenance, and verification

## Retained rounds

- [`2026-07-31 name-brand actionable scan`](../../research/rounds/2026-07-31-name-brand-actionable-scan/selection.md) — ranked BuildKit, libarchive, util-linux, systemd, and capability-gated work; promoted five bounded investigations; retained duplicate stops.
- [`2026-07-30 ecosystem candidate scan`](../../research/rounds/2026-07-30-ecosystem-candidate-scan/selection.md) — selections, environment gates, live-overlap repair, and active-fix references.
- [`LF-35 round 001`](lanes/LF-35-package-collection-candidate-harvesting/artifacts/round-001.md) — `gomarkdoc` test restoration, Homebrew recurring intake, AAVMF capability queue, and duplicate stops.
- [`LF-36 round 001`](lanes/LF-36-downstream-patch-retirement/artifacts/round-001.md) — canonical fixes and exact triggers for future downstream patch removal.

## First sequence

1. Run the libarchive seekability/bidder matrix in investigation #230.
2. Map the canonical util-linux `lscpu` ownership correction and stable backport boundary in investigation #234.
3. Run the BuildKit multi-platform symlink exporter matrix in investigation #233 when the pinned container environment is available.
4. Run systemd-oomd investigation #140 in a cgroup-v2 VM and capture ManagedOOM Varlink notifications around a user-manager reload.
5. Build investigation #232's direct fsck/udev synchronization fixture before escalating to repeated VM boots.
6. Compare rootful and rootless BuildKit OCI metadata in investigation #229.
7. Keep AAVMF behind aarch64 QEMU capability.
8. Recheck canonical fixes as they land so downstream patches and workarounds can be removed promptly.

## Candidate target classes

- Nixpkgs, Debian, Fedora, Arch, and Linuxbrew/Homebrew packaging;
- CPython, Rust, Go, Node.js, and distro-carried toolchains;
- pip, uv, Cargo, Nix, Meson, CMake, pytest, Ruff, Clippy, and ShellCheck;
- curl, libarchive, compression, URL, Unicode, filesystem, configuration, and terminal libraries;
- systemd, util-linux, Podman, BuildKit, containerd, Mesa, and adjacent Linux user-space projects;
- reproducibility, SBOM, provenance, signing, and package metadata tools.

## Routing rule

A package symptom stays in this programme during intake. Once evidence identifies the owning boundary, route it to the strongest home:

- transaction and maintainer-script behavior → `debian-packages`;
- archives, metadata, paths, and images → `filesystems-images`;
- processes, cleanup, services, and resources → `services-resources`;
- namespaces, mounts, and rootless operation → `rootless-execution`;
- privilege, networking, and policy composition → `security-networking`;
- boot, devices, kernel APIs, and deeper kernel work → `boot-kernel`.

## Portfolio discipline

A large intake queue is useful. Active implementation stays bounded by test and review capacity. Every promoted candidate records exact source identity, environment, commands, baseline behavior, consequence, likely owner, overlap checks, and the smallest credible next change.

Promotion expires when a matching pull request, assignee, claim, or equivalent fix appears. Recheck immediately before creating a branch.

## Authority

Programme mapping grants no upstream-contact authority.
