# LF-35 Result — Package Candidate Harvesting Round 001

Date: 2026-07-30  
Lane: [`LF-35`](../brief.md)

## In simple words

The first harvest found one current-CI package test-restoration candidate, one recurring Homebrew intake source, and one firmware regression with a clear VM gate. It also found two Nixpkgs issues already covered by active fixes, which are retained as package-engineering examples and removed from duplicate implementation.

## Candidate 1 — `gomarkdoc` disabled tests

Issue: `NixOS/nixpkgs#516481`  
Package file: `pkgs/by-name/go/gomarkdoc/package.nix`  
State: **selected for first probe**

### Known boundary

- known-good nixpkgs: `4590696c8693fea477850fe379a01544293ca4e2`;
- known-bad sampled revision: `acd02b8`;
- package version: `1.1.0` throughout the reported window;
- current package expression: `doCheck = false`;
- current explanatory comment: nixpkgs exports `GOFLAGS=-mod=vendor`, while gomarkdoc tests call its command entrypoint and parse those flags with a parser that accepts only `-tags`;
- issue output also reports `../.gomarkdoc-empty.yml` missing.

### First command matrix

Use a local override that sets `doCheck = true`, then run:

```text
A. current package environment unchanged
B. GOFLAGS cleared during checkPhase
C. GOFLAGS filtered to gomarkdoc-supported flags
D. tests run from repository root
E. tests run through current subPackages path
F. known-good nixpkgs revision with the same observations
```

Record:

- exact check command;
- `pwd` during the failing tests;
- effective `GOFLAGS`;
- fixture existence and resolved relative path;
- which test packages fail;
- whether the produced binary differs across variants.

### Owning-boundary outcomes

| Outcome | Likely owner |
|---|---|
| clearing inherited `GOFLAGS` alone restores tests | package expression or a narrowly scoped Go test hook |
| working-directory change alone restores tests | package `checkFlags`/subpackage selection or upstream relative-path assumption |
| both are required | package expression plus upstream test robustness |
| failure appears across unrelated Go packages | shared `buildGoModule` regression |
| test invokes unsupported command behavior intentionally | upstream test or package-level disable with a stronger explanation |

### Promotion signal

Promote a patch when it restores a meaningful test suite without broadly hiding valid Go build flags. Add a passthru or package test if the regression concerned generated output rather than internal test mechanics.

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

The issue includes a QEMU invocation and pinned good and bad nixpkgs revisions. Before a source bisect, turn console output into a deterministic assertion:

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

- selected: `gomarkdoc` test restoration;
- recurring: Homebrew blocked-update trackers;
- capability-gated: AAVMF;
- duplicate stops: pandoc Lua and Darwin libffi;
- next output: executable `gomarkdoc` environment matrix and retained logs.