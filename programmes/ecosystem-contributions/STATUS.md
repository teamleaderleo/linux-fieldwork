# Ecosystem Contributions and Upstream Fixes

## In simple words

This programme turns Linux package collections, runtimes, developer tools, foundational libraries, and system projects into a continuing source of reproducible bug reports, tested patches, and retained technical understanding.

## Current direction

- **Mapped:** [LF-35 — package collection candidate harvesting](lanes/LF-35-package-collection-candidate-harvesting/brief.md)
- **Mapped:** [LF-36 — downstream patch retirement and upstream transfer](lanes/LF-36-downstream-patch-retirement/brief.md)
- **Inbox:** LF-37 — cross-distribution build portability
- **Inbox:** LF-38 — runtime and toolchain distribution regressions
- **Inbox:** LF-39 — foundational-library boundary corpus
- **Inbox:** LF-40 — package metadata, provenance, and verification

## First sequence

Run LF-35 continuously as the intake lane. Promote candidates into existing Linux Fieldwork programmes when their owning boundary is already clear. Use LF-36 for downstream patches that may be obsolete, incomplete, or suitable for upstream transfer. Keep LF-37 through LF-40 in the registry until a specific repository, revision, fixture, and first distinguishing probe exist.

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

## Authority

Programme mapping grants no upstream-contact authority.