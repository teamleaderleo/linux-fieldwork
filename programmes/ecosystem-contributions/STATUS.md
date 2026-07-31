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

- [`2026-07-31 fork-enabled execution`](../../research/rounds/2026-07-31-fork-enabled-execution/selection.md) — libarchive, DuckDB, and Deno fork probes; one bounded product candidate; one standards-driven rescope; persisted-index evidence queue.
- [`2026-07-30 ecosystem candidate scan`](../../research/rounds/2026-07-30-ecosystem-candidate-scan/selection.md) — selections, environment gates, live-overlap repair, and active-fix references.
- [`LF-35 round 001`](lanes/LF-35-package-collection-candidate-harvesting/artifacts/round-001.md) — `gomarkdoc` test restoration, Homebrew recurring intake, AAVMF capability queue, and duplicate stops.
- [`LF-36 round 001`](lanes/LF-36-downstream-patch-retirement/artifacts/round-001.md) — canonical fixes and exact triggers for future downstream patch removal.

## First sequence

1. Classify the non-seekable 7-Zip transport matrix in investigation #230 and fork PR `teamleaderleo/libarchive#1`.
2. Validate the DuckDB input-immutability candidate in investigation #254 and fork PR `teamleaderleo/duckdb#9`.
3. Validate the secondary-ART release boundary in investigation #256 and fork PR `teamleaderleo/duckdb#10`, then add current-head evidence.
4. Use fork PR `teamleaderleo/deno#2` to separate connection racing from post-connect response stalls; rescope #253 from the observed result.
5. Probe Deno stdin cancellation after a final overlap refresh of public issue 30652.
6. Continue rechecking canonical fixes so duplicate candidates stop promptly.

## Candidate target classes

- Nixpkgs, Debian, Fedora, Arch, and Linuxbrew/Homebrew packaging;
- CPython, Rust, Go, Node.js, Deno, and distro-carried toolchains;
- pip, uv, Cargo, Nix, Meson, CMake, pytest, Ruff, Clippy, and ShellCheck;
- curl, libarchive, compression, URL, Unicode, filesystem, configuration, and terminal libraries;
- DuckDB and adjacent embedded database/storage systems;
- systemd, util-linux, Podman, BuildKit, containerd, Mesa, and adjacent Linux user-space projects;
- reproducibility, SBOM, provenance, signing, and package metadata tools.

## Routing rule

A package symptom stays in this programme during intake. Once evidence identifies the owning boundary, route it to the strongest home:

- transaction and maintainer-script behavior → `debian-packages`;
- archives, metadata, paths, databases, and images → `filesystems-images`;
- processes, cleanup, services, cancellation, and resources → `services-resources`;
- namespaces, mounts, and rootless operation → `rootless-execution`;
- privilege, networking, and policy composition → `security-networking`;
- boot, devices, kernel APIs, and deeper kernel work → `boot-kernel`.

## Portfolio discipline

A large intake queue is useful. Active implementation stays bounded by test and review capacity. Every promoted candidate records exact source identity, environment, commands, baseline behavior, consequence, likely owner, overlap checks, and the smallest credible next change.

Forks are internal laboratories, not upstream destinations. Promotion expires when a matching pull request, assignee, claim, or equivalent fix appears. Recheck immediately before creating a branch and again before any publication decision.

## Authority

Programme mapping and fork work grant no upstream-contact authority.
