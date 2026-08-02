# Ecosystem Contributions and Upstream Fixes

## In simple words

This programme turns Linux package collections, runtimes, developer tools, foundational libraries, and system projects into a continuing source of reproducible bug reports, tested patches, and retained technical understanding.

## Current direction

- **Investigating:** [LF-35 — package collection candidate harvesting](lanes/LF-35-package-collection-candidate-harvesting/brief.md)
- **Investigating:** [LF-36 — downstream patch retirement and upstream transfer](lanes/LF-36-downstream-patch-retirement/brief.md)
- **Inbox:** LF-37 — cross-distribution build portability
- **Inbox:** LF-38 — runtime and toolchain distribution regressions
- **Investigating:** [LF-39 — foundational-library boundary corpus](lanes/LF-39-foundational-library-boundary-corpus/brief.md)
- **Inbox:** LF-40 — package metadata, provenance, and verification

## Retained rounds

- [`2026-07-30 ecosystem candidate scan`](../../research/rounds/2026-07-30-ecosystem-candidate-scan/selection.md) — selections, environment gates, live-overlap repair, and active-fix references.
- [`LF-35 round 001`](lanes/LF-35-package-collection-candidate-harvesting/artifacts/round-001.md) — `gomarkdoc` test restoration, Homebrew recurring intake, AAVMF capability queue, and duplicate stops.
- [`LF-36 round 001`](lanes/LF-36-downstream-patch-retirement/artifacts/round-001.md) — canonical fixes and exact triggers for future downstream patch removal.
- [`LF-39 glibc fnmatch investigation`](../../investigations/glibc-fnmatch-extmatch-complexity/README.md) — ambiguous extended alternatives produce Fibonacci-like rejection-time growth on Debian glibc 2.41.

## First sequence

1. Continue LF-39 with canonical-current-source confirmation, repeated-state instrumentation, and bounded algorithm review for glibc `FNM_EXTMATCH` rejection complexity.
2. Run the `gomarkdoc` test-restoration matrix in investigation #136: inherited `GOFLAGS`, working directory, subpackage selection, and pinned nixpkgs revisions.
3. Select a leaf from the Homebrew unsolved-formula tracker with current logs and no active equivalent work.
4. Run systemd-oomd investigation #140 in a cgroup-v2 VM and capture ManagedOOM Varlink notifications around a user-manager reload.
5. Keep AAVMF behind aarch64 QEMU capability.
6. Retain libarchive PPMd short reads as an active-fix reference through upstream PR 3340.
7. Recheck canonical fixes as they land so downstream patches and workarounds can be removed promptly.

## Candidate target classes

- Nixpkgs, Debian, Fedora, Arch, and Linuxbrew/Homebrew packaging;
- glibc, musl, CPython, Rust, Go, Node.js, and distro-carried toolchains;
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

Fresh speculative work is allowed when it has a bounded discriminator, local or otherwise available execution, cleanup, a durable record, and a stop rule. Hosted CI availability is evidence context, not a prerequisite for source reading, local testing, review, hypothesis generation, or opening an investigation.

Promotion expires when a matching pull request, assignee, claim, or equivalent fix appears. Recheck immediately before creating an external carrier.

## Authority

Programme mapping grants no upstream-contact authority.
