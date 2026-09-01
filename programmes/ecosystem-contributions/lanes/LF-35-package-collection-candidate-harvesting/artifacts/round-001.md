# LF-35 Result — Package Candidate Harvesting Round 001

Date: 2026-07-30  
Disposition refresh: 2026-08-05  
Lane: [`LF-35`](../brief.md)

## In simple words

The first harvest found one package test-restoration candidate, one recurring Homebrew intake source, and one firmware regression with a clear VM gate. It also found two Nixpkgs issues already covered by active fixes, which are retained as package-engineering examples and removed from duplicate implementation.

The gomarkdoc candidate completed investigation and owner review. The user submitted [gomarkdoc: restore checks on Go 1.26](https://redirect.github.com/NixOS/nixpkgs/pull/549377). Issue #136 now owns current-head CI and maintainer-review monitoring.

## Candidate 1 — `gomarkdoc` disabled tests

Issue: [Nixpkgs gomarkdoc regression](https://redirect.github.com/NixOS/nixpkgs/issues/516481)  
Submitted pull request: [gomarkdoc: restore checks on Go 1.26](https://redirect.github.com/NixOS/nixpkgs/pull/549377)  
Package file: `pkgs/by-name/go/gomarkdoc/package.nix`  
State: **submitted**

### Original boundary

- known-good Nixpkgs: `4590696c8693fea477850fe379a01544293ca4e2`;
- known-bad sampled revision: `acd02b8`;
- package version: `1.1.0` throughout the reported window;
- package expression: `doCheck = false`;
- explanatory comment blamed `GOFLAGS=-mod=vendor` reaching gomarkdoc's application parser;
- issue output also reported `../.gomarkdoc-empty.yml` missing.

### Executed matrix result

The matrix varied the inherited flags, supported-tag filtering, missing fixture, package selection, working directory, Go generation, and pinned Nixpkgs revisions.

It established:

- removing `-mod=vendor` wasn't sufficient;
- creating `.gomarkdoc-empty.yml` wasn't sufficient;
- the missing config path printed a diagnostic but didn't return the failing error;
- Go 1.26 changed one generated Markdown line;
- updating that expected line restored the package-selected `cmd/gomarkdoc` tests;
- broader root, formatter, and `lang` package discovery exposed additional old standard-library prose goldens and wasn't selected for this repair.

### Submitted design

The submitted source:

- keeps the current Go 1.26 builder;
- retains `subPackages = [ "cmd/gomarkdoc" ]`;
- updates one expected Markdown line with `substituteInPlace --replace-fail`;
- removes `doCheck = false`;
- doesn't create the missing fixture or rewrite `GOFLAGS`;
- doesn't change the package version, source, vendor hash, linker flags, selected command, or installed executable.

Submitted branch: `teamleaderleo/nixpkgs:contrib/gomarkdoc-go126-checks`  
Submitted base: `356468b500e85491b610431c87a284ca1f41b7bc`  
Submitted head: `060a1f8b8af68af858be896715c5dfc540522235`

Prior Linux and Darwin execution applies to the identical final package-file blob. Exact-current-head execution remains pending. The earlier Go 1.25/fixture/flag-filter candidate is superseded.

## Candidate 2 — Homebrew blocked updates

Tracker: `Homebrew/homebrew-core#139929`  
State: **recurring intake**

Selection filter for each formula:

1. update remains blocked in the tracker;
2. current build/test logs exist;
3. no active equivalent pull request;
4. source build fits an available macOS or Linuxbrew environment;
5. failure has a likely formula, dependency, build-system, or upstream owner;
6. one focused test can demonstrate success.

Preferred first leaves:

- packages with Linux-only or macOS-only build failures;
- packages where upstream supports the new version but formula flags lag;
- failures caused by an obsolete patch;
- leaf packages in the OpenSSL 4 migration tracker.

## Candidate 3 — AAVMF firmware regression

Issue: `NixOS/nixpkgs#485220`  
State: **capability queue**

The issue includes a QEMU invocation and pinned good and bad Nixpkgs revisions. Before a source bisect, turn console output into a deterministic assertion:

```text
good: reaches PXE/network boot attempt
bad: stops after UEFI firmware banner
```

Then vary one component at a time:

- OVMF/AAVMF package revision;
- edk2 flags and firmware variant;
- cross toolchain;
- QEMU version and machine options;
- pflash variable image handling.

## Duplicate stops retained

### Pandoc Lua feature loss

- Issue: `NixOS/nixpkgs#540900`
- Active PR: `NixOS/nixpkgs#540913`

Reference lesson: automatic default-on build features can silently turn off after an SDK change. Pin the feature and test the installed binary so future loss becomes a build failure.

### Darwin libffi crash

- Issue: `NixOS/nixpkgs#541367`
- Active PR: `NixOS/nixpkgs#541990`

Reference lesson: isolate a platform-loader behavior change, identify the exact generated binary feature, and apply a bounded packaging workaround while upstream compatibility evolves.

## Next harvest queries

```text
Nixpkgs open issues containing checkPhase, doCheck, works/fails revisions, Hydra mismatch
Homebrew #139929 unresolved leaves
Homebrew #278366 OpenSSL 4 leaf packages
Debian packages with reproducibility failures or disabled autopkgtests
Fedora FTBFS issues with a current mock/Koschei result
```

## Result

- submitted: `gomarkdoc` command-test restoration;
- recurring: Homebrew blocked-update trackers;
- capability-gated: AAVMF;
- duplicate stops: pandoc Lua and Darwin libffi;
- next gomarkdoc action: monitor current-head CI and maintainer review in #136;
- no additional automated upstream interaction.
