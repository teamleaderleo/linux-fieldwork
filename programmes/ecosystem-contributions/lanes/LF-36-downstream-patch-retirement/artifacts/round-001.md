# LF-36 Result — Downstream Patch Retirement Round 001

Date: 2026-07-30  
Lane: [`LF-36`](../brief.md)

## In simple words

This round identified active upstream and package fixes that should become future patch-retirement checkpoints. The goal is to prevent a distribution or owned tree from carrying a local delta after the supported upstream release already contains an equivalent correction.

## Retirement workflow

For each downstream patch or workaround:

1. identify the exact downstream file, commit, and reason;
2. find the upstream issue and canonical fix;
3. compare behavior, tests, and supported versions;
4. determine the first upstream release or revision containing the fix;
5. rebuild the downstream package without the patch against that revision;
6. run the original regression test plus package integration tests;
7. remove, refresh, split, or retain the patch with a written reason.

A title or similar-looking diff is insufficient. Equivalence requires the same consequence and supported configuration.

## Reference A — Nixpkgs pandoc Lua feature contract

Issue: `NixOS/nixpkgs#540900`  
Active fix: `NixOS/nixpkgs#540913`

### Mechanism

The static top-level pandoc build silently lost Lua support after an Apple SDK update because Cabal automatic flags could disable themselves. The active package fix pins default-on `lua` and `server` features, turning future silent loss into a hard build failure.

### Retirement use

Search downstream package trees for:

- local pandoc feature-forcing patches;
- wrappers rejecting `-lua` builds;
- build-time Lua capability probes added after the regression;
- pins to an older Apple SDK or pandoc package revision.

When the package fix lands and reaches the supported channel, rebuild without each local workaround and assert:

```sh
pandoc --version
pandoc --lua-filter <minimal-filter.lua> <input>
```

Retain integration tests even after patch removal.

## Reference B — Nixpkgs Darwin libffi workaround

Issue: `NixOS/nixpkgs#541367`  
Active fix: `NixOS/nixpkgs#541990`

### Mechanism

macOS 27 rejects the trampoline dylib generated with invalid chained fixups. The active packaging fix disables the affected trampoline path.

### Retirement use

Track:

- upstream libffi support for the stricter loader;
- the first release with corrected trampoline dylib generation;
- downstream patches or configuration that disable closures/trampolines more broadly than the Nixpkgs fix;
- packages pinning an older libffi or SDK.

Removal gate:

- upstream binary loads under macOS 27;
- closure/trampoline functionality passes a focused test;
- dependent packages no longer require the downstream disablement.

## Reference C — libarchive standalone AppleDouble preservation

Issue: `libarchive/libarchive#3310`  
Active fix: `libarchive/libarchive#3334`

### Mechanism

The tar reader treated every final path component beginning with `._` as AppleDouble metadata and consumed it without confirming that a matching ordinary file followed. The active fix checks the following tar header and preserves unmatched entries.

### Retirement use

Search distribution and application trees for:

- patches changing `process_mac_extensions` defaults;
- filters that rename or protect standalone `._` entries;
- downstream tar extraction workarounds;
- test exclusions involving AppleDouble files.

Removal gate:

- supported libarchive includes the upstream fix;
- valid AppleDouble pairs still combine correctly;
- adjacent standalone entries and end-of-archive cases remain visible;
- downstream consumers no longer need the workaround.

## Reference D — CPython zip repack/live-reader guard

Issue: `python/cpython#154842`  
Active fix: `python/cpython#154843`

### Mechanism

`ZipFile.repack()` moves member bytes while an existing reader stores an absolute position. The active fix rejects repacking while a reading handle is open.

### Retirement use

Watch downstream copies of the new 3.16 zipfile behavior and applications that added their own synchronization or reader tracking. Remove redundant guards only when the runtime version and behavior are explicit.

## Patch inventory searches

Use these searches in downstream packaging and owned repositories:

```text
patch filenames containing upstream issue numbers
comments containing TODO remove after <version>
feature-force flags added after a platform transition
packages with doCheck=false plus an upstream test fix
version pins referencing a crash or build regression
local cherry-picks whose upstream commit now appears in a release
```

For distro repositories, compare:

```text
debian/patches/
Fedora spec Patch and Source entries
Nixpkgs patches and postPatch blocks
Homebrew patch/do blocks and formula revisions
Arch prepare() patches
```

## First retirement queue

| Component | Current state | Recheck trigger |
|---|---|---|
| pandoc Lua feature workaround | active package PR | PR lands and reaches selected nixpkgs channel |
| Darwin libffi trampoline workaround | active package PR | upstream libffi release supports macOS 27 loader |
| libarchive AppleDouble workarounds | active upstream PR | PR merges and a release is packaged |
| CPython zip repack guards | active upstream PR for 3.16 | PR merges and downstream runtime version includes it |
| pip latest-marker local fixes | active pip PR #14178 | release containing fix reaches package collection |

## Result

No local patch was removed in this reconnaissance round because the selected canonical fixes remain active upstream or in package review. The retained queue now names exact recheck triggers and regression tests, allowing removal work to begin as soon as those fixes land.