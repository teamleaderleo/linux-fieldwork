# Biome watcher: ignore Git-internal event paths

State: `ACTIVE — LOSING TEST MATERIALIZED`  
Programme: `ecosystem-contributions` + `services-resources`  
LF-35 round: `002`  
Worker or variant: `LF-R02`  
External contact authorized: `false`

## TL;DR

Biome issue #11110 combines two behaviors: Git-internal watcher events can produce indexing errors, and symlinked workspaces may not re-lint. They have different source owners and compatibility risks, so this investigation selects only the `.git` event path.

The current watcher filters every notification through the workspace ignore policy. When that policy does not classify `.git/index.lock` as ignored, the event remains eligible for indexing. A controlled branch now adds a test expecting Git-internal events to be removed while an ordinary source event survives. No implementation has been selected and no test run has been claimed.

## Explain like I'm five

Biome watches the project for files that changed. Git also creates private bookkeeping files. Biome should notice the source file, not try to lint Git's temporary lock file.

## Why care

Transient `.git/index.lock` and similar bookkeeping paths can generate `internalError/io` noise during ordinary Git operations. That makes watch mode and editor integration look broken even when project source files are valid.

## Scope split

### Selected here

- watcher notifications below a project's `.git` directory;
- preserving ordinary source notifications in the same event batch;
- recommended and polling watcher policy consistency;
- no dependence on VCS integration being enabled.

### Deliberately separate

- symlinked workspaces inside `node_modules` not being re-linted;
- general symlink traversal and module graph ownership;
- `.gitignore` and user-configured ignore semantics;
- branch-switch source refresh behavior;
- LSP memory growth tracked by issue #10139 and PR #11037.

The symlink half of issue #11110 requires its own reproducer and source map before promotion.

## Exact identities

| Item | Exact value |
| --- | --- |
| Upstream repository | `biomejs/biome` |
| Current upstream base | `9847e680ff8bb891a6c910e881af98a4fffa33c2` |
| Controlled fork | `teamleaderleo/biome` |
| Snapshot branch | `linux-fieldwork/upstream-main-20260802` |
| Investigation branch | `linux-fieldwork/biome-11110-git-watch-noise` |
| Test-only head | `e84a255bb0062d94b419581e5321b371cbcfe6a9` |
| Changed-file fence | `crates/biome_service/src/scanner/watcher.tests.rs` |
| Watcher source | `crates/biome_service/src/scanner/watcher.rs` |
| Watcher source blob | `d0a8f433234ef87c1db841fd7b390b13754432f4` |
| Watcher test blob before change | `801a98a06cc07c3bc109fbdee3698b527619892c` |
| Mock bridge source | `crates/biome_service/src/scanner/test_utils.rs` |
| Mock bridge blob | `96cdd5ce0182029a185bc6d8451f646a3b90877e` |
| Workspace bridge source | `crates/biome_service/src/scanner/workspace_bridges.rs` |
| Workspace bridge blob | `364c519b1d7f858fabe16fc51e5477e67ff19543` |

## Current public state

Checked 2026-08-02:

- issue #11110 is open;
- no assignee is recorded;
- it is labeled `S-Needs triage`;
- one automated comment is recorded;
- no pull request referencing `11110` was found in the repository search.

The report includes a public reproduction repository, but this investigation has not imported or executed it yet.

## Observed mechanism

`Watcher::handle_notify_event()` first calls `Watcher::watched_paths()`. That function:

1. converts each notification path to UTF-8;
2. resolves the owning project and scan kind;
3. delegates the ignore decision to `workspace.is_ignored(...)`;
4. retains the path when the workspace returns `false`.

`ScannerWatcherBridge::is_ignored()` forwards the question to the scanner as an explicit update request. The watcher has no separate Git-internal path exclusion. The test bridge likewise treats only explicitly inserted paths as ignored.

This does not prove that unconditional `.git` exclusion is the final implementation. It establishes the current policy boundary and a deterministic unit-level discriminator.

## Losing test branch

Commit `e84a255bb0062d94b419581e5321b371cbcfe6a9` adds one test to `watcher.tests.rs`:

- input event paths: `<project>/.git/index.lock` and `<project>/ui/something.js`;
- expected retained paths: only `<project>/ui/something.js`.

Comparison against exact upstream base is one commit ahead, zero behind, with 25 added test lines and no source changes.

## First distinguishing probe

On a clean checkout of exact base and then the test-only branch:

```sh
cargo test -p biome_service should_ignore_git_internal_events
```

Required interpretation:

- baseline does not contain the new test;
- test-only branch should fail because current `watched_paths()` returns both paths;
- retain the exact assertion diff;
- run under both the default and polling watcher configurations if later integration work moves beyond the pure path filter;
- rerun immediately and confirm cleanup leaves no watcher thread alive.

The pure test calls `watched_paths()` directly and does not start a real OS watcher, so its cleanup surface is limited to the temporary filesystem.

## Candidate design discriminators

Before selecting an implementation, compare these policies:

1. unconditional exclusion of any component exactly equal to `.git`;
2. exclusion only when VCS integration is disabled;
3. classifying VCS internal directories in the shared scanner ignore layer;
4. filtering only known transient lock paths.

A winning policy must:

- drop `.git/index.lock` and ordinary Git bookkeeping events;
- retain `.github`, `.gitmodules`, and names that merely begin with `.git`;
- preserve source-file updates caused by checkout or branch switching;
- avoid changing user `.gitignore` semantics;
- behave consistently for recommended and polling watchers;
- avoid broad symlink behavior changes.

## Stop and promotion rules

Promote after the test is executed on exact current head, the public reproducer confirms the same event path, and one policy above wins the negative controls.

Stop duplicate implementation if an equivalent current PR appears. Split again if `.git/index.lock` is already excluded in full workspace integration and the report instead depends on a different path produced by symlinked workspaces.

## Authority

Internal reads, branches, test fixtures, source experiments, and Fieldwork records are authorized. No upstream issue, pull request, comment, review, reaction, or other contact has been made or authorized.
