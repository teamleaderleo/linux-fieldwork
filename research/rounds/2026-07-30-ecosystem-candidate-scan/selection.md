# Ecosystem Candidate Scan — Selection Record

Date: 2026-07-30  
Programme: [`ecosystem-contributions`](../../../programmes/ecosystem-contributions/STATUS.md)  
Fieldwork parent: `teamleaderleo/fieldwork` programme #207 and broad-spectrum round 001

## In simple words

This scan translated a live cross-ecosystem issue survey into Linux Fieldwork execution lanes. It selected work with exact revisions, commands, likely owning files, and clear environment gates. It also retained active upstream fixes so local work can avoid duplication and identify downstream patches ready for removal later.

Promotion state is perishable. A live refresh found an active libarchive fix after the original scan, so that candidate moved from execution to reference without losing its technical lesson.

## Sources surveyed

- Nixpkgs package regressions and package expressions;
- Homebrew Core unsolved formula and migration trackers;
- CPython and Rust issue queues;
- Ruff and pip correctness queues;
- libarchive parser and portability reports;
- DuckDB reproduced SQL defects;
- systemd lifecycle and resource-management reports.

## Immediate Linux selections

### 1. Nixpkgs `gomarkdoc` test restoration

Issue: [Nixpkgs test-regression issue](https://redirect.github.com/NixOS/nixpkgs/issues/516481)  
Environment: current Linux CI with Nix  
Route: LF-35 package candidate harvesting and investigation #136

Current package state:

```text
pkgs/by-name/go/gomarkdoc/package.nix
version = 1.1.0
doCheck = false
```

The issue pins a successful nixpkgs revision and a failing revision. The package comment attributes the disabled suite to inherited `GOFLAGS=-mod=vendor` reaching gomarkdoc's own flag parser, while the issue also reports a missing relative fixture. The first probe isolates environment flags and test working-directory behavior.

Promotion signal: restore the suite with a bounded package or shared `buildGoModule` correction.

### 2. Homebrew unsolved formula intake

Issue: [Homebrew unsolved-formula tracker](https://redirect.github.com/Homebrew/homebrew-core/issues/139929)  
Environment: macOS or Linuxbrew, selected per formula  
Route: LF-35 recurring intake

Select leaf formulae with current logs and no active equivalent pull request. Record whether the fix belongs in the formula, upstream build system, dependency declaration, or source project.

### 3. systemd-oomd registration loss

Issue: [systemd-oomd reload-registration issue](https://redirect.github.com/systemd/systemd/issues/43174)  
Environment: cgroup-v2 VM with PSI and a lingering user  
Route: `services-resources`, investigation #140

`user@<uid>.service` begins monitored, then disappears from oomd after `systemctl --user daemon-reload` while the unit remains active with `ManagedOOMMemoryPressure=kill`.

Likely source boundaries:

```text
src/oom/oomd-manager.c
src/core/varlink.c
test/units/TEST-55-OOMD.sh
```

First probe: capture the ManagedOOM notification sequence around reload, identify the message that removes the PID-1-owned cgroup, and verify whether any re-registration follows.

### 4. Nixpkgs AAVMF regression

Issue: [Nixpkgs AAVMF regression](https://redirect.github.com/NixOS/nixpkgs/issues/485220)  
Environment: aarch64 QEMU or equivalent VM  
Route: `boot-kernel`, capability queue

The issue provides pinned working and failing nixpkgs revisions and a QEMU command. Convert the console boundary into an automated pass/fail marker before bisecting edk2, package flags, firmware variants, and QEMU compatibility.

## Active-fix reference — libarchive PPMd short reads

Issue: [libarchive PPMd small-buffer issue](https://redirect.github.com/libarchive/libarchive/issues/3337)  
Active fix: [libarchive PR 3340](https://redirect.github.com/libarchive/libarchive/pull/3340)

The candidate originally entered the current-CI queue. The live refresh found a focused active fix covering the same mechanism and fixture:

- PPMd reads ahead after exhausting an input block;
- those extra bytes were excluded from consumed-input accounting;
- the next read could replay them;
- the regression crosses the boundary with four 1 KiB entries and 1000-byte input blocks.

Independent implementation is stopped. Retain the case for parser refill accounting, regression-fixture design, and downstream patch retirement after release adoption.

## Adjacent non-Linux-first work retained in Fieldwork

- Ruff RUF038 automatic-fix runtime mutation;
- DuckDB Hive partition marker collision;
- CPython free-threaded `GenericAlias` iterator race;
- assigned Rust diagnostic examples.

Linux Fieldwork may provide containers, compilers, or test matrices for these, while canonical coordination remains in Fieldwork.

## Active-fix references

| Project | Issue | Active fix | Linux Fieldwork use |
|---|---|---|---|
| libarchive | PPMd small-buffer decode | PR 3340 | parser-state reference and future downstream patch retirement |
| Nixpkgs | pandoc loses Lua | PR 540913 | force automatic features and fail on silent loss |
| Nixpkgs | libffi/macOS 27 | PR 541990 | platform-transition diagnosis reference |
| libarchive | standalone AppleDouble entries | PR 3334 | retire downstream copies after release adoption |
| CPython | zip repack/live reader | PR 154843 | mutable-file lifecycle reference |
| pip | latest marker | PR 14178 | compact type-comparison fix reference |

## Selection rule applied

A candidate enters the immediate queue when it has:

- exact source identity or a pinned revision range;
- a repeatable command or small fixture;
- a consequential result;
- a likely owning file or subsystem;
- no active equivalent fix or claim;
- an environment available now or a clearly named capability gate.

Recheck issue comments, linked work, assignees, claims, and pull requests immediately before branch creation.

## Current decision

Run the `gomarkdoc` test-restoration probe first in current CI. Queue the systemd-oomd trace for a VM. Keep AAVMF behind aarch64 QEMU capacity. Retain libarchive PPMd as an active-fix reference. Continue harvesting Homebrew and Nixpkgs regression reports into LF-35.