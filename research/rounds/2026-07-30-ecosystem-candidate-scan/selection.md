# Ecosystem Candidate Scan — Selection Record

Date: 2026-07-30  
Programme: [`ecosystem-contributions`](../../../programmes/ecosystem-contributions/STATUS.md)  
Fieldwork parent: `teamleaderleo/fieldwork` programme #207 and broad-spectrum round 001

## In simple words

This scan translated a live cross-ecosystem issue survey into Linux Fieldwork execution lanes. It selected work with exact revisions, commands, likely owning files, and clear environment gates. It also retained active upstream fixes so local work can avoid duplication and identify downstream patches ready for removal later.

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

Issue: `NixOS/nixpkgs#516481`  
Environment: current Linux CI with Nix  
Route: LF-35 package candidate harvesting

Current package state:

```text
pkgs/by-name/go/gomarkdoc/package.nix
version = 1.1.0
doCheck = false
```

The open issue pins a successful nixpkgs revision and a failing revision. The package comment attributes the disabled suite to inherited `GOFLAGS=-mod=vendor` reaching gomarkdoc's own flag parser, while the issue also reports a missing relative fixture. The first probe must isolate both environment flags and test working-directory behavior.

Promotion signal: restore the suite with a bounded package or shared `buildGoModule` correction.

### 2. Homebrew unsolved formula intake

Issue: `Homebrew/homebrew-core#139929`  
Environment: macOS or Linuxbrew, selected per formula  
Route: LF-35 recurring intake

The tracker explicitly lists formulae whose updates remain blocked by build, test, or other failures. Select leaf formulae with current logs and no active pull request. Record whether the fix belongs in the formula, upstream build system, dependency declaration, or source project.

### 3. systemd-oomd registration loss

Issue: `systemd/systemd#43174`  
Environment: cgroup-v2 VM with PSI and a lingering user  
Route: `services-resources`, VM queue

`user@<uid>.service` begins monitored, then disappears from oomd after `systemctl --user daemon-reload` while the unit remains active with `ManagedOOMMemoryPressure=kill`. Likely source boundaries:

```text
src/oom/oomd-manager.c
src/core/varlink.c
test/units/TEST-55-OOMD.sh
```

First probe: capture the ManagedOOM notification sequence around reload, identify the message that removes the PID-1-owned cgroup, and verify whether any re-registration follows.

### 4. libarchive small-buffer PPMd decode

Issue: `libarchive/libarchive#3337`  
Environment: current Linux CI  
Route: `filesystems-images`, candidate corpus

Retain the provided 7z fixture and run the reader through a matrix of chunk sizes. The distinguishing result is whether valid output depends on caller buffer size. Trace the PPMd refill boundary and add a focused regression fixture.

### 5. Nixpkgs AAVMF regression

Issue: `NixOS/nixpkgs#485220`  
Environment: aarch64 QEMU or equivalent VM  
Route: `boot-kernel`, capability queue

The issue provides pinned working and failing nixpkgs revisions and a QEMU command. Convert the console boundary into an automated pass/fail marker before bisecting edk2, package flags, firmware variants, and QEMU compatibility.

## Adjacent non-Linux-first work retained in Fieldwork

- Ruff #27026 automatic-fix runtime mutation;
- DuckDB #24308 Hive partition marker collision;
- Rust #159745 nested-turbofish diagnostic;
- CPython #154916 free-threaded `GenericAlias` iterator race.

Linux Fieldwork may provide containers, compilers, or test matrices for these, while canonical coordination remains in Fieldwork.

## Active-fix references

| Project | Issue | Active fix | Linux Fieldwork use |
|---|---|---|---|
| Nixpkgs | #540900 pandoc loses Lua | PR #540913 | package test pattern: force automatic features and fail on silent loss |
| Nixpkgs | #541367 libffi/macOS 27 | PR #541990 | platform-transition diagnosis reference |
| libarchive | #3310 standalone AppleDouble entries | PR #3334 | watch for downstream copies and retire local patches after release adoption |
| CPython | #154842 zip repack/live reader | PR #154843 | mutable-file lifecycle reference |
| pip | #14177 latest marker | PR #14178 | compact type-comparison fix reference |

## Selection rule applied

A candidate entered the immediate queue when it had:

- exact source identity or a pinned revision range;
- a repeatable command or small fixture;
- a consequential result;
- a likely owning file or subsystem;
- no active equivalent fix;
- an environment available now or a clearly named capability gate.

## Current decision

Run the `gomarkdoc` test-restoration probe first in current CI. In parallel, prepare the libarchive chunk-size fixture. Queue the systemd-oomd trace for a VM. Keep AAVMF behind aarch64 QEMU capacity. Continue harvesting Homebrew #139929 and Nixpkgs regression reports into LF-35.