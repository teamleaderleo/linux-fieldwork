# LF-35 Result — Fork Inventory Reconnaissance Round 002

Date: 2026-08-02  
Worker or variant: GPT-5.6 Thinking / `LF-R02`  
Branch: `research/lf-35-round-002-fork-scouting`  
State: `ACTIVE`  
External contact authorized: `false`

## In simple words

This round replaces the stale assumption that Linux Fieldwork's candidate universe is limited to the repositories named by priority-zero issue #397. The current project instructions make LF-35 an active discovery lane and explicitly ask for twenty candidates, five live upstream checks, and two reproduction-ready selections.

The user's controlled GitHub inventory now contains many substantial upstream forks that were absent from the older target registry and LF-35 round 001. This record treats issue #397 as one backlog-specific coordination surface rather than the global research map.

## Authority and method

Current authority comes from `README.md`, `START_HERE.md`, `FIELD_GUIDE.md`, `ADAPTIVE_COORDINATION.md`, `RESEARCH_LANES.md`, and the LF-35 brief.

Selection favors a bounded source owner, small fixture, two plausible outcomes, a negative control, cleanup, and a concrete next decision. Existing upstream work is checked to avoid duplicate implementation, but a claim or existing worker does not lock the question.

No upstream issue, pull request, comment, review, reaction, email, or other external contact is authorized.

## Controlled fork inventory — twenty new or under-mapped candidates

These repositories are selected from the user's current owner-controlled fork inventory. They intentionally exclude the heavily repeated mmdebstrap, BuildKit, systemd, util-linux, Nixpkgs, uv, DuckDB, and libarchive lanes from the first-pass ranking.

| Rank seed | Controlled fork | Candidate surface | Current project coverage |
| ---: | --- | --- | --- |
| 1 | `teamleaderleo/coreutils` | filesystem/path/exit-status compatibility in Rust core utilities | no dedicated target or investigation found |
| 2 | `teamleaderleo/curl` | protocol state, cancellation, partial I/O, redirects, and test portability | named as a target class; no dedicated current target found |
| 3 | `teamleaderleo/llvm-project` | compiler/runtime test assumptions, cross-toolchain behavior, crash reductions | no dedicated target or investigation found |
| 4 | `teamleaderleo/rust` | compiler/toolchain distribution regressions and process behavior | target class only; no dedicated current target found |
| 5 | `teamleaderleo/qemu` | device lifecycle, image publication, firmware, cancellation, and migration tests | AAVMF capability work exists; repository itself is under-mapped |
| 6 | `teamleaderleo/httpx` | streaming cleanup, cancellation, proxy and redirect semantics | no dedicated target or investigation found |
| 7 | `teamleaderleo/execa` | subprocess signals, cancellation, descriptor and cleanup semantics | no dedicated target or investigation found |
| 8 | `teamleaderleo/node-lru-cache` | async fetch cancellation, stale publication, disposal, and timing | no dedicated target or investigation found |
| 9 | `teamleaderleo/opentelemetry-js` | shutdown/flush ordering, context propagation, resource cleanup | no dedicated target or investigation found |
| 10 | `teamleaderleo/deno` | subprocess, permissions, filesystem, package and runtime compatibility | no dedicated target or investigation found |
| 11 | `teamleaderleo/biome` | parser/formatter determinism, filesystem traversal, configuration boundaries | no dedicated target or investigation found |
| 12 | `teamleaderleo/oxc` | parser/minifier/linter correctness and deterministic reduced fixtures | no dedicated target or investigation found |
| 13 | `teamleaderleo/rspack` | build graph invalidation, filesystem cache, watcher cleanup, source maps | no dedicated target or investigation found |
| 14 | `teamleaderleo/playwright` | browser-process cleanup, downloads, filesystem state and cancellation | no dedicated target or investigation found |
| 15 | `teamleaderleo/bevy` | asset loading, task lifecycle, filesystem watching and platform regressions | no dedicated target or investigation found |
| 16 | `teamleaderleo/dioxus` | desktop/server process lifecycle, hot reload, path and packaging behavior | no dedicated target or investigation found |
| 17 | `teamleaderleo/next.js` | build cache, file tracing, worker cleanup and cross-platform paths | no dedicated target or investigation found |
| 18 | `teamleaderleo/react` | scheduler/test environment and server rendering lifecycle | no dedicated target or investigation found |
| 19 | `teamleaderleo/supabase` | local service lifecycle, migrations, CLI/test orchestration | no dedicated target or investigation found |
| 20 | `teamleaderleo/jotai` | async state cancellation, store lifecycle and test portability | no dedicated target or investigation found |

## Initial ranking criteria

Each candidate receives a later score for:

1. current open defect with an exact reproduction;
2. no active equivalent fix or clearly assigned implementation;
3. current-CI or small-container feasibility;
4. bounded source and test owner;
5. meaningful consequence beyond cosmetic behavior;
6. fit with Fieldwork's lifecycle, path, metadata, package, cache, streaming, evidence, or reproducibility strengths;
7. controlled fork availability.

## Live upstream checks

Status: `IN PROGRESS`.

The first broad issue query was too heavily skewed toward LLVM because of repository size. Per-repository queries and exact issue/PR overlap checks are required before ranking. One promising bounded lead is LLVM issue 111974, where LLDB's minidump test expects a libc++ ABI module name in a fresh x86_64 build that actually uses libstdc++; this may be a test-environment assumption rather than a product failure. It remains unselected until current comments, source ownership, and equivalent pull requests are checked.

## First incomplete step

Run per-repository live issue and pull-request checks for at least five genuinely under-mapped forks. Record exact issue identities, activity, assignees or equivalent ownership, reproducer quality, likely source/test owner, environment cost, and duplicate-stop status. Select the best two only after those checks.

## Cleanup and evidence boundary

No fork branches were changed during intake. No external repository was contacted. No local service, process, mount, VM, credential, package transaction, or temporary artifact was created. Current evidence is repository metadata, project instructions, fork inventory, and public issue search results only.
