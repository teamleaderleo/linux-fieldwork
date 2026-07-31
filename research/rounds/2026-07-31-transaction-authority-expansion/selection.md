# Transaction authority and liveness expansion — selection record

Date: 2026-07-31  
Programme: ecosystem contributions with Debian, filesystem, service, and networking routes  
Authority: internal Linux Fieldwork research only; no new upstream contact authorized

## TL;DR

This round selected work where a component crosses one of four boundaries without naming the owner clearly enough:

1. **publication** — when does a new generation become visible and usable?
2. **cancellation** — who owns cleanup, and what can a timeout truthfully claim?
3. **path identity** — does authority belong to source identity, invocation spelling, or resolved destination?
4. **partial transaction state** — when one step fails, which desired, resolved, and applied facts remain authoritative?

The strongest confirmed result is DuckDB issue #256: DuckDB 1.5.4 can persist a secondary ART index that returns zero for existing rows after a second independently loaded engine checkpoints a pending WAL. The strongest new current-CI probes are uv launcher portability (#307) and node-lru-cache same-key fetch reentrancy. The strongest capability-gated directions are uv managed-Python publication (#309), Windows self-update recovery (#317), and Windows locked-file uninstall (#318).

## Explain like I'm five

Many bugs in this round come from showing a half-finished thing too early, letting two workers believe they own the same thing, or saying “finished” when only one step finished.

The useful experiment is rarely “did an error happen?” It is:

- which actor owned the old state;
- which actor first published the new state;
- what another reader could observe in the middle;
- what survived after failure or cancellation;
- which receipt is fact and which part is still unknown.

## Why care

These boundaries create plausible success around wrong state:

- a database returns a clean-looking false negative through a corrupt index;
- a read-only query mutates later results;
- a package manager updates desired dependencies while leaving a half-removed environment;
- an updater removes the canonical executable before the replacement is durable;
- a cancellation API returns one comforting terminal word while remote execution or cleanup remains unknown;
- two aliases to one script select different dependency lockfiles.

The common review rule is: **one operation needs one explicit authority, one publication boundary, and one honest receipt.**

# Ranked execution queue

## A1 — DuckDB persisted secondary ART false negatives

Linux Fieldwork: #256  
Durable result carrier: PR #316  
Controlled-fork evidence: `teamleaderleo/duckdb#10`

### Current result

A five-case hosted matrix at fork head `e4543e7d2e6aa12f6d4e75ec2266ac9030e59fc5` completed successfully:

- DuckDB 1.3.2 secondary ART: correct index lookup;
- DuckDB 1.5.4 secondary ART at two rows: index lookup returns zero, sequential scan returns one;
- DuckDB 1.5.4 secondary ART at 10,000 rows: same false negative;
- DuckDB 1.5.4 primary key: correct;
- DuckDB 1.5.4 without index: correct.

The table rows remain present. The persisted secondary index is the wrong-result owner in the characterized fixture.

### Why this is first

This is silent, persisted data correctness with a clean historical control and generated artifacts. It has enough mechanism evidence for source archaeology while still carrying an explicit hold on production repair.

### Next action

Map the first bad commit around the 1.4 boundary, reproduce current main from one exact source identity for both engine images, and inspect secondary ART checkpoint/serialization ownership.

### Wrong-fix traps

- globally disabling index scans hides corruption;
- rebuilding every index on open can mask the writer defect and impose broad startup cost;
- declaring duplicate engines unsupported is insufficient while current code permits a bad persistent write;
- allowing normal writer shutdown can heal the file and erase evidence.

## A2 — DuckDB read-only decode mutates shared BLOB storage

Linux Fieldwork: #254  
Controlled-fork candidate: `teamleaderleo/duckdb#9`

### Current direction

For `decode(blob, 'replace')`, analyze through a const pointer. Allocate a result-owned equal-sized buffer only when invalid bytes require replacement; copy, repair, finalize, and return that buffer. Preserve the existing valid-input fast path.

### Why this is strong

The ownership rule is local and testable: a read-only scalar transform must never write into shared input storage. The neighboring `ignore` path already uses result-owned storage.

### Current hold

The first hosted failures were harness failures before the regression ran: missing `mold`, then a stale SQL test path. The repaired workflow now pins the exact PR head, verifies both candidate files, installs the linker, and runs the focused SQL test. Exact-head jobs remain queued.

### Wrong-fix traps

- disabling dictionary optimization masks the mutating implementation;
- copying every valid value creates avoidable allocation regression;
- removing the writable accessor without allocating transformed output leaves ownership unresolved;
- returning a result string without the correct heap lifetime can replace corruption with a dangling reference.

## A3 — node-lru-cache same-key fetch reentrancy

Controlled-fork characterization: `teamleaderleo/node-lru-cache#4`

### Current result under test

`fetchMethod` runs synchronously before the provisional `BackgroundFetch` owns the key. Existing controls show synchronous same-key writes are replaced or lost. A new bounded control shows nested `cache.fetch(key)` redispatches the fetch method instead of coalescing because the first reservation is not installed yet.

### Design opinion

The initial `fetch()` should reserve the key before user code runs. Nested same-key fetch should coalesce. Later same-key `set` or `delete` should supersede and abort the reservation. A deferred placeholder installed before callback dispatch is more coherent than silently ignoring reentrant mutation.

### Wrong-fix traps

- suppressing same-key writes contradicts documented overwrite/delete abort behavior;
- reserving only after user code preserves recursive redispatch;
- fixing missing-key insertion without stale refresh leaves two contracts;
- changing same-key behavior can disturb size accounting, disposal order, abort signals, and synchronous return values.

## A4 — uv relocatable launcher portability

Linux Fieldwork: #307  
Controlled-fork evidence: `teamleaderleo/uv#2`

### Current probe

Compare uv's current generated fragment:

```sh
"$(dirname -- "$(realpath -- "$0")")"/python
```

with a no-delimiter form under GNU coreutils and Alpine BusyBox. Exercise absolute, relative, PATH, space-containing, leading-hyphen, and symlink invocation.

### Why this is useful

The baseline command succeeds on BusyBox while leaking `realpath: --: No such file or directory` to stderr. The tempting one-line repair—remove `--`—needs pathname controls before product code changes.

### Design opinion

Normalize a leading-hyphen operand only where needed, call `realpath` portably, then pass its absolute output to `dirname`. Review all sibling launcher generators together so wheel, virtualenv, and project-run scripts do not drift.

### Current hold

Focused and ordinary fork CI remain queued. No result is claimed yet.

# Capability-gated high-value queue

## B1 — uv publishes managed Python before finalization

Linux Fieldwork: #309

A managed interpreter becomes visible under its final discoverable directory before finalization steps such as sysconfig patching, metadata, policy files, and minor-version links finish. Discovery does not appear to join the installer lock.

### Preferred direction

Perform identity-affecting work in a hidden same-filesystem staging directory, then publish once. Split path-sensitive finalization only when evidence proves it cannot target staging safely.

### Wrong-fix traps

- a reader-only lock leaves non-uv consumers exposed;
- cache invalidation after finalization misses readers that already cached identity;
- staging can accidentally embed temporary paths in sysconfig or links;
- replacing an old generation needs rollback and concurrent-reader controls.

## B2 — uv self-update interruption on Windows

Linux Fieldwork: #317

Current source downloads the installer, renames running `uv.exe` to `.previous.exe`, runs PowerShell, restores on ordinary failure, and deletes the backup on success. Process death after the rename bypasses rollback.

### Preferred direction

Stage and validate a complete generation, publish under generation identity with a small durable journal, and retain the previous generation until every canonical name and receipt belong to one generation.

### Wrong-fix traps

- catching more Rust errors does not handle process death or power loss;
- unconditional restore can overwrite a legitimate newer publisher;
- `uv`, `uvx`, `uvw`, and receipt can form a mixed generation;
- startup recovery cannot run when the canonical executable is missing unless another trusted launcher remains.

## B3 — uv locked-file uninstall transaction

Linux Fieldwork: #318

Wheel uninstall removes `RECORD` entries one by one and stops on an unhandled Windows removal failure. `uv remove` writes desired project metadata before environment lock/sync. One locked executable or extension module can leave declared, resolved, and applied state diverged.

### Preferred direction

Stage wheel-owned paths into a same-volume transaction area where rename is allowed. When Windows refuses even staging, preserve explicit desired-versus-applied failure state and deterministic retry metadata instead of rolling back user intent silently.

### Wrong-fix traps

- lockfile rollback can erase the requested dependency change;
- best-effort deletion can leave a mixed importable package;
- preflight races actual removal;
- rollback can overwrite a path recreated by another writer;
- shared namespace packages and scripts cross distribution ownership.

## B4 — uv symlinked script lock authority

Linux Fieldwork: #311

One PEP 723 source reached through two symlinks can select two different `.lock` files because lock authority follows invocation spelling.

### Preferred direction

Canonical source identity owns the default lock. An alternate lock location should be explicit in CLI/configuration and visible in diagnostics. Avoid canonical-first implicit fallback because absence silently changes authority and undermines source-side scanning.

### Wrong-fix traps

- canonical-only writing breaks centrally managed read-only scripts;
- alias-owned locks preserve convenience while weakening reproducibility;
- canonicalization followed by pathname reopen still permits target replacement under a hostile local race;
- Windows junctions and remote/stdin scripts need a separate identity rule.

# Design reviews that changed the next experiment

## C1 — Codex non-settling runtime cancellation

Controlled-fork source PR: `teamleaderleo/codex#110`  
Execution carrier: `teamleaderleo/codex#111`

Cancellation needs three facts: requested, cleanup confirmed, and cleanup outcome unknown after a host deadline. Mapping a timeout directly to ordinary `aborted` manufactures certainty.

Preferred contract: runtime-configurable cleanup deadline, one terminal `cancelled_cleanup_unconfirmed` receipt, drop the dispatch future, and fence late duplicate events. Tests must cover owner drop, repeated cancellation, deadline boundaries, parallel calls, and runtime opt-out.

## C2 — HTTPX failed async response close

Controlled-fork candidate: `teamleaderleo/httpx#6`

The candidate correctly attempts arbitrary cleanup once and avoids retaining the owner exception traceback for every observer. The missing discriminator is reentrant close: a stream whose `aclose()` calls `response.aclose()` can wait on the event owned by its outer invocation and deadlock itself.

Preferred implementation shape: an explicit `OPEN | CLOSING(owner,event) | CLOSED | FAILED` state, owner-task reentrancy detection, observer cancellation isolation, and a documented public contract for “cleanup failed, reads blocked, retry forbidden, `is_closed` false.”

## C3 — Bun executable replacement

Fieldwork issue: `teamleaderleo/fieldwork#345`

The missing race is concurrent destination ownership:

```text
A owns destination
installer removes A
another writer publishes C
installer publishes or restores B/A
```

Both rollback and atomic rename can clobber C. Prove one transaction lock covers package metadata, package files, and bin links before selecting the ordinary sibling-temp-plus-rename design. Treat directory replacement separately.

## C4 — Upstash Box cancellation receipts

Fieldwork issue: `teamleaderleo/fieldwork#329`

Separate request delivery from remote run outcome:

```text
request: not-sent | in-flight | accepted | rejected | transport-unknown
run: authoritative terminal | latest observed | unknown
```

Single-flight also needs waiter-cancellation ownership. One cancelled caller must not cancel the shared remote request for every observer unless explicitly assigned that authority.

## C5 — workerd generated receiver specialization

Controlled-fork test PR: `teamleaderleo/workerd#4`

The source direction is sound: specialize a replacement class receiver from the replacement declaration's type parameters. The missing proof is final-pipeline validity, not another redesign. Add final emitted-text parse/typecheck controls and ensure internal receiver markers disappear.

# Stops and negative results

## D1 — libarchive blanket non-seekable bidder rejection

Linux Fieldwork durable result: merged PR #280

Current master lists the small 7-Zip fixture through every tested non-seekable transport, while extraction fails with a seek error through those transports. A blanket `can_seek == 0` bidder rejection would remove working listing and format identity together with failing extraction.

Future work should separate list/header capability from backward-seeking data extraction or improve the extraction diagnostic. Do not lower the bidder globally without preserving the passing list controls.

## D2 — Deno stdin readable cancellation

The old public report remains open, but current Deno source contains a dedicated cancellation regression and merged fix commit `53b969f2c8559af2c62fbf1c9642811bf0d0c867`. Independent implementation stops. The remaining value is stale-issue hygiene and downstream adoption/version mapping.

# Portfolio opinion

The most productive current theme is not a specific language or project. It is **authority during transition**:

- reserve before reentrant user code;
- finish before publication;
- distinguish desired from applied state;
- retain the old generation until the new one is authoritative;
- never convert timeout into certainty;
- attach lockfiles and caches to a deliberate identity;
- test the concurrent writer that every rollback plan hopes does not exist.

This theme is broad enough to produce many candidates and narrow enough to demand concrete probes.

## Next execution order

1. merge the strengthened DuckDB record after exact-head Linux Fieldwork CI;
2. map DuckDB's first bad commit and current-main secondary ART behavior;
3. consume uv launcher and node-lru exact-head results;
4. complete DuckDB decode candidate execution;
5. build uv managed-Python publication failpoint fixture;
6. build Windows locked-file uninstall fixture before self-update, because it tests the same filesystem semantics with a smaller transaction;
7. run Codex, HTTPX, and workerd missing discriminators after their current exact-head jobs settle;
8. keep libarchive global bidder changes stopped unless a design preserves working listing.

## Evidence boundary

This record links confirmed hosted evidence, active internal candidates, and newly opened investigation plans. Only the DuckDB release matrix and merged libarchive record are completed technical results here. Queued fork workflows remain unclaimed. Windows and managed-Python directions remain proposals until their deterministic fixtures execute.

No external issue comment, pull request, review, reaction, or other upstream interaction was made or authorized in this round.
