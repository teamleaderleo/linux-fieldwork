# Round 003 work checkpoint 03

Work window: 2026-08-03 14:56 +08:00  
Worker: `LF-R03`  
External contact authorized: `false`

## Instruction refresh

This pass followed `ADAPTIVE_COORDINATION.md`, `START_HERE.md`, `FIELD_GUIDE.md`, and the LF-35 brief:

- refresh current issue, comment, PR, branch, and workflow state before implementation;
- preserve exact source and branch identities;
- split implementation lanes from review-only or already-owned lanes;
- use distinguishing probes and negative controls;
- do not claim green execution for staged patches;
- do not contact upstream without authorization.

The pass intentionally deprioritized Biome and focused on `uv`, `wgpu`, and safetensors.

## Decision table

| Lane | Current decision | Exact internal state | Current upstream owner |
| --- | --- | --- | --- |
| `uv` workspace member index persistence, #20678 | `ACTIVE — CANDIDATE STAGED` | research head `1091bcb0b5fbf06e00c42563e34399f1500cecba`; candidate head `6d8be29feeea6346db78346d28b2e76cbae6d851`; exact source base `79bbface771210df216b738e9bdc7df95e5a9e6b` | issue open and unassigned; no issue-number PR carrier found |
| `uv` stub-only init layout, canonical #19663 / newer #20734 | `STOP — RETAIN REPRODUCTION ONLY` | internal candidate `b911394d2d42e8a6098fc8d7c229ce1768c32dfd` | open upstream PR #19671, head `082af3c5eb95bbc0f0173ebc67965919c14e1a0a`, contains the same correction and an end-to-end `uv build` test |
| `wgpu` BLAS lock order, #9981 | `STOP — REVIEW EVIDENCE ONLY` | internal candidate `6df67c85960613de2087245bb4b52755313a270a` | open draft PR #9479, head `def5cbc458788536ecaabd519cc9c7bd14d45682`, covers the exact `compact_blas_inner` lock order |
| safetensors s390x `TensorSpec`, #812 | `ACTIVE — RAW-PAYLOAD DISCRIMINATOR REFINED` | Linux Fieldwork commits `0dbb5740a5197c94c7d14337e3bfe34a56677104` and `469bd428e27e4a2f4c95dfbea0a9ae6a3a37ece1`; source reviewed at `6eb4dc9a28ebce297606e0f4836bbf28839cacef` | issue open and unassigned; no issue-number PR carrier found |

## `uv` #20678: promoted candidate

### Current mechanism

`uv add --package child` creates its mutable TOML representation from the selected member. Command-line indexes are then added to that same TOML and written through the selected `AddTarget`. General workspace index resolution, however, is rooted at the workspace project.

A single named index is different: the dependency edit is pinned to it through `tool.uv.sources`, so the member-local index definition is replayable as an explicit package source.

`AddTargetSnapshot::Project` already retains the workspace-root TOML, selected member TOML, and lockfile. Root routing therefore does not require inventing a second recovery store, but it does require treating both writes and rediscovery as one recoverable operation.

### Research matrix

Branch `research/uv-20678-workspace-member-index-authority` now contains a localhost-only three-case matrix:

1. root project plus implicit index: clean lock should succeed;
2. workspace member plus implicit index on current source: clean lock should fail;
3. workspace member plus one named source-pinned index: clean lock should succeed.

The script builds a minimal wheel locally, serves populated and empty PEP 503 indexes on localhost, removes the lockfile, uses fresh caches, and verifies which TOML file changed.

### Candidate contract

Branch `candidate/uv-20678-route-implicit-indexes-to-workspace-root` stages:

- unnamed or multi-index general search configuration in the workspace root;
- dependency changes in the selected member;
- one named source-pinned index in the selected member;
- snapshot reversion if either TOML write or full workspace rediscovery fails;
- full `VirtualProject::discover` after a root edit instead of member-only in-memory update;
- two `--frozen` native integration tests that do not require index network access.

Candidate files:

- `.github/fieldwork/20678-route-implicit-indexes-to-root.patch`
- `.github/fieldwork/20678-check-root-routing.sh`
- `.github/fieldwork/20678-route-implicit-indexes-to-root.md`

Execution state: staged and unexecuted. No apply, compiler, formatter, or focused-test success is claimed.

## `uv` stubs: reproduction confirmed, implementation stopped

The previously queued focused run `30759500353` completed successfully. It built `uv` and confirmed the exact current mismatch:

- `uv init --package foo-stubs` generated `src/foo_stubs/__init__.py`;
- it generated `[project.scripts] foo-stubs = "foo_stubs:main"`;
- `uv build` failed with `Expected a Python module at: src/foo-stubs/__init__.pyi`.

That is strong reproduction evidence, but it is not a candidate validation.

Canonical overlap refresh found open upstream PR #19671. Its patch removes the runtime script, generates `src/foo-stubs/__init__.pyi`, and includes an end-to-end integration test that successfully builds both sdist and wheel. The internal candidate adds no unique implementation value and is retained only as provenance and independent reproduction evidence.

## `wgpu` #9981: existing carrier and invalid internal detector

The issue discussion points to open draft PR #9479, and the reporter explicitly held off because that PR covers the problem. The PR changes `compact_blas_inner` to acquire `Device::command_indices` before `Queue::pending_writes`, matching the exact source path under investigation.

The old internal focused run `30759780777` completed with failure, but the failure was in the detector itself: `.github/fieldwork/9981-lock-order.py` raised `ValueError: substring not found` while searching for `pending_writes.lock()`. It did not execute a lock-order test and provides no evidence about the product defect.

Because the upstream carrier owns the exact correction and the repository instructions prohibit making commits in this work mode, no new `wgpu` write occurred. The internal branch remains review evidence only.

## Safetensors #812: writer evidence separated from reader interpretation

The previous endian matrix used `load_file()` to classify what the writer emitted. That could create an evidence donut on a big-endian host because reader interpretation is itself platform-sensitive.

The refined `endian_matrix.py` now parses the safetensors file directly:

1. reads the little-endian header length;
2. decodes the JSON header;
3. extracts the tensor's `data_offsets`;
4. compares raw payload bytes against explicit `<f4` and `>f4` NumPy buffers.

Expected distinguishing result:

- high-level NumPy save normalizes big-endian input to little-endian payload;
- direct little-endian `TensorSpec` writes little-endian payload;
- direct big-endian `TensorSpec` copies source bytes unchanged;
- explicit conversion restores little-endian payload;
- threaded direct writes are byte-identical to the single-thread direct write.

The README now maps the source owner and keeps the corrected GIL timing test separate from the byte-order contract test.

Execution state: unexecuted. The available local safetensors installation is `0.7.0` and does not expose the current public `TensorSpec` API.

## First incomplete gates

1. Run the `uv` #20678 candidate harness in a clean checkout at exact base `79bbface...`.
2. Correct apply, compiler, formatter, snapshot, or test failures before broadening the candidate.
3. Run the localhost #20678 matrix with the candidate applied and require the member-implicit case to change from failure to success.
4. Add failed-lock and Ctrl-C rollback tests covering both root and member changes.
5. Test existing root index ordering, named and unnamed combinations, default and explicit indexes, relative paths, and credential redaction.
6. Run the safetensors raw-payload matrix against source exposing `TensorSpec`, then run a corrected thread timing test on emulated and native s390x.
7. Track upstream PR #19671 and #9479 only as overlap stops; do not create competing implementations while they remain active.
8. Refresh exact upstream heads and overlap immediately before any future authorization request.

## Authority

All new work remains internal to controlled repositories and Linux Fieldwork records. No public upstream issue, pull request, comment, review, reaction, email, or other contact occurred.
