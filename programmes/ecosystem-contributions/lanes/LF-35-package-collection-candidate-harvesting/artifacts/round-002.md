# LF-35 Result — Fork Inventory Reconnaissance Round 002

Date: 2026-08-02  
Worker or variant: GPT-5.6 Thinking / `LF-R02`  
Branch: `research/lf-35-round-002-fork-scouting`  
State: `SCOUTED — TWO INVESTIGATIONS ACTIVE`  
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
| 11 | `teamleaderleo/biome` | parser/formatter determinism, filesystem traversal, configuration boundaries | no dedicated target or investigation found before this round |
| 12 | `teamleaderleo/oxc` | parser/minifier/linter correctness and deterministic reduced fixtures | no dedicated target or investigation found |
| 13 | `teamleaderleo/rspack` | build graph invalidation, filesystem cache, watcher cleanup, source maps | no dedicated target or investigation found |
| 14 | `teamleaderleo/playwright` | browser-process cleanup, downloads, filesystem state and cancellation | no dedicated target or investigation found |
| 15 | `teamleaderleo/bevy` | asset loading, task lifecycle, filesystem watching and platform regressions | no dedicated target or investigation found |
| 16 | `teamleaderleo/dioxus` | desktop/server process lifecycle, hot reload, path and packaging behavior | no dedicated target or investigation found |
| 17 | `teamleaderleo/next.js` | build cache, file tracing, worker cleanup and cross-platform paths | no dedicated target or investigation found |
| 18 | `teamleaderleo/react` | scheduler/test environment and server rendering lifecycle | no dedicated target or investigation found |
| 19 | `teamleaderleo/supabase` | local service lifecycle, migrations, CLI/test orchestration | no dedicated target or investigation found |
| 20 | `teamleaderleo/jotai` | async state cancellation, store lifecycle and test portability | no dedicated target or investigation found |

## Ranking criteria

Each candidate is judged by:

1. current open defect with an exact reproduction;
2. no active equivalent fix or clearly assigned implementation;
3. current-CI or small-container feasibility;
4. bounded source and test owner;
5. meaningful consequence beyond cosmetic behavior;
6. fit with Fieldwork's lifecycle, path, metadata, package, cache, streaming, evidence, or reproducibility strengths;
7. controlled fork availability.

## Live upstream screen

### Top five inspected

| Rank | Public work | State checked 2026-08-02 | Overlap result | Disposition |
| ---: | --- | --- | --- | --- |
| 1 | Biome #11174 — mutable member false positive in `noUnnecessaryConditions` | open, unassigned, needs response/triage, exact fixture | no PR referencing `11174` found | selected |
| 2 | Biome #11110 — `.git` watcher errors plus symlinked workspaces | open, unassigned, needs triage, public repro | no PR referencing `11110` found | split; `.git` half selected |
| 3 | Biome #11023 — `check --only` applies changes outside selected lint rules | open, unassigned, needs triage, public repro supplied | no PR referencing `11023` found | hold for command-contract decision |
| 4 | Biome #11025 — first-start logging emits missing-directory stderr | open, unassigned, bug confirmed | PRs #11026 and #11075 both propose the correction | duplicate implementation stop; review/test help only |
| 5 | Biome #10139 — LSP footprint grows across branch/config reloads | open, unassigned, bug confirmed, deterministic macOS repro | PR #11037 claims the fix with bounded cache tests | duplicate implementation stop; review/test help only |

### Additional inspected leads and stops

- LLVM #111974 remains open but is assigned and requires a large LLDB build; it is a supporting test-assumption inquiry rather than a first reproduction packet.
- Deno #34582 was closed through PR #35160.
- Execa #1219 was closed through PR #1232, and Node 26 test issue #1233 is also closed.
- curl #21797 is closed.
- the HTTPX searches used in this pass produced no open matching issue suitable for immediate promotion.
- Biome #10515, initially attractive as an idempotence defect, was already closed as completed.

These stops are retained so future scans do not rediscover solved or actively owned work as empty contribution lanes.

## Selected investigation 1 — mutable member truthiness

Fieldwork record:

- `investigations/biome-no-unnecessary-conditions-member-mutation/README.md`

Controlled source state:

| Item | Value |
| --- | --- |
| Exact upstream base | `biomejs/biome@9847e680ff8bb891a6c910e881af98a4fffa33c2` |
| Controlled snapshot | `teamleaderleo/biome:linux-fieldwork/upstream-main-20260802` |
| Test branch | `teamleaderleo/biome:linux-fieldwork/biome-11174-member-mutation` |
| Test-only head | `468b97947271255528cbb53caddb10831db18ea7` |
| Diff fence | one added 28-line valid-rule fixture |

The source owner is `crates/biome_js_analyze/src/lint/suspicious/no_unnecessary_conditions.rs`. The rule already documents a reassignment exemption for bindings, while the public fixture demonstrates that writes to the same mutable member are ignored. The test-only branch adds direct, ref-like, numeric, and inverse-truthiness member cases without selecting an implementation.

## Selected investigation 2 — Git-internal watcher events

Fieldwork record:

- `investigations/biome-git-watch-events/README.md`

Controlled source state:

| Item | Value |
| --- | --- |
| Exact upstream base | `biomejs/biome@9847e680ff8bb891a6c910e881af98a4fffa33c2` |
| Controlled snapshot | `teamleaderleo/biome:linux-fieldwork/upstream-main-20260802` |
| Test branch | `teamleaderleo/biome:linux-fieldwork/biome-11110-git-watch-noise` |
| Test-only head | `e84a255bb0062d94b419581e5321b371cbcfe6a9` |
| Diff fence | 25 test lines in `watcher.tests.rs` |

The report's symlinked-workspace half is deliberately excluded. The selected test passes `.git/index.lock` and an ordinary source path through `Watcher::watched_paths()` and expects only the source path to survive. Current watcher code delegates the entire decision to workspace ignore policy and contains no watcher-specific Git-internal exclusion.

## Why #11023 was not promoted

Current `check` source deliberately requests formatter, linter, and assist features. Its `--only` values are analyzer selectors, while the command help describes `check` as checking all three domains. The reported extra edits are therefore real behavior but the correction boundary is ambiguous:

- change `--only` to imply only the named feature domains;
- require explicit formatter/assist disabling;
- or clarify the CLI contract.

That question needs a compatibility matrix before a source branch is justified.

## First incomplete steps

### Member-mutation rule

```sh
cargo test -p biome_js_analyze no_unnecessary_conditions
```

Run exact base and test-only head, retain the diagnostic/snapshot difference, rerun, then select a bounded member-write policy without globally widening object properties.

### Git watcher events

```sh
cargo test -p biome_service should_ignore_git_internal_events
```

Run exact base and test-only head, retain the assertion difference, then reproduce the public `.git/index.lock` path through real watch mode. Compare unconditional `.git` exclusion, VCS-disabled-only exclusion, shared scanner classification, and lock-file-only filtering.

## Gates and cleanup

Completed:

- current project-instruction review;
- twenty-fork intake;
- five live public issue checks;
- issue-to-PR overlap searches;
- exact current Biome source identity;
- exact snapshot and test branches;
- one-file complete-diff review for both test branches;
- source/test ownership map;
- scope split for issue #11110.

Pending:

- compilation and focused test execution;
- baseline/candidate receipts;
- public reproduction import for watcher issue #11110;
- source implementation selection;
- `just f`, `just l`, relevant cargo tests, changesets, and complete implementation diff;
- current overlap recheck immediately before any publication decision.

No service, watcher, package transaction, VM, mount, credential, or local temporary artifact was created in this pass. The only source-fork mutations are the three controlled branches and the two test-only commits listed above. No upstream contact occurred.
