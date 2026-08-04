# Round 003 work checkpoint 04

Date: 2026-08-05  
Worker or variant: `LF-R04`  
External contact authorized: `false`

## Current decision table

| Lane | Current decision | Exact controlled state | Current public overlap |
| --- | --- | --- | --- |
| uv workspace member index authority, #20678 | `ACTIVE — PUBLIC-CANDIDATE AUTHORITY MATRIX QUEUED` | `teamleaderleo/uv#35`, head `0da9e6d121548e9db150fc28e99c35828944b1b3`; focused run `30946501753`; ordinary CI `30946500961` | public PR #20922, head `64d6042d4b30830042d3a402d0b2e953730a8ede`, open with successful public CI |
| uv stub-only init layout, #19663 / #20734 | `ACTIVE — SCOPED CARRIER REPAIRED` | `teamleaderleo/uv#30`, repaired head `80b413cb8dedbb2b4a79c85d41c7f12fd911c987`; focused run `30946811586`; ordinary CI `30946812859` | public PR #19671 remains open; its policy applies the uv_build layout to every backend |
| Biome mutable member truthiness, #11174 | `ACTIVE — FIXTURE HARNESS REPAIRED` | `teamleaderleo/biome#2`, head `cd6a8d1f9aed7b1ac23eff0a8cdda14b115ac52c`; focused run `30946698463`; zizmor `30946697501` | issue open, unassigned, unchanged since 2026-08-02 |
| Biome Git-internal watcher paths, #11110 | `ACTIVE — FEATURE/HOSTED-CARRIER REPAIRED` | `teamleaderleo/biome#3`, head `4093a3a5ab9fe8407ba9c251c0a577856e68872c`; workflow now runs directly on controlled-branch pushes | issue open, unassigned, unchanged since 2026-07-28 |
| wgpu BLAS lock order, #9981 | `STOP — EXISTING PUBLIC CARRIER` | retained internal candidate `6df67c85960613de2087245bb4b52755313a270a` | draft PR #9479 remains open at `def5cbc458788536ecaabd519cc9c7bd14d45682` |
| safetensors s390x TensorSpec byte order, #812 | `HOLD — NEEDS EXECUTABLE SOURCE ENVIRONMENT` | raw-payload matrix retained on this LF-35 branch | issue open and unchanged since 2026-07-08; no controlled safetensors fork is installed |

## uv #20678: public design changed the question

The old internal candidate moved unnamed or general index search configuration to the workspace root. Public PR #20922 instead changes resolution to gather indexes from every workspace member.

The public candidate has successful upstream CI. It therefore replaces the old question, “can the reported case be fixed?”, with an authority question:

> Does an index declared by one member intentionally become workspace-global search configuration, including for dependencies declared by unrelated sibling members?

Controlled PR `teamleaderleo/uv#35` builds exact public base `92b7185783b56e8ad1dbe0bb7600432708f2c9fb` and exact public candidate `64d6042d4b30830042d3a402d0b2e953730a8ede`, then runs four localhost-only cases:

1. root-owned populated index;
2. dependency and index in the same member;
3. dependency in one member while an unrelated sibling owns the only populated index;
4. named explicit member index with a source pin.

Expected distinction:

- exact base: root and named-source controls pass; both unpinned member-index cases fail;
- public candidate: all four pass, including the unrelated-sibling case.

A passing sibling case establishes workspace-global member-index authority under the public candidate. It is not by itself a defect verdict. It is the discriminator between the public design and the retained root-owned alternative.

Execution state: both controlled runs are queued. No result is claimed.

## uv stubs: the scoped carrier had a rewriter failure

The first run of controlled PR #30 stopped before compilation because its Python source transformer converted a Rust `\n` escape into a literal newline inside a character constant.

The failure owner was the carrier, not uv product code and not the scoped backend design.

Head `80b413cb8dedbb2b4a79c85d41c7f12fd911c987` changes the generated replacement to a raw Python string so the Rust escape is preserved. The focused and ordinary reruns are queued.

No eight-backend result is claimed yet.

## Biome #11174: fixture contract repaired

The prior red run never evaluated the expected analyzer behavior. The fixture lacked the test harness marker requiring a diagnostic-free case.

Head `cd6a8d1f9aed7b1ac23eff0a8cdda14b115ac52c` adds:

```ts
// should not generate diagnostics
```

The focused rerun and zizmor are queued. Until the focused test completes, neither baseline reproduction nor candidate validation is claimed.

## Biome #11110: feature selection and trigger repaired

The prior watcher run compiled `biome_service` without the shipped language features and failed in unrelated feature-gated modules before reaching `should_ignore_git_internal_events`.

The focused command is now:

```sh
cargo test -p biome_service --features stable should_ignore_git_internal_events -- --nocapture
```

The workflow also accepts direct pushes to `ci/biome-11110-git-watch-noise`, removing dependence on a missing pull-request synchronization event. The focused test now documents that `.git` metadata churn is excluded while an ordinary project path in the same batch remains observable.

Head: `4093a3a5ab9fe8407ba9c251c0a577856e68872c`.

No hosted result is visible yet and no product conclusion is claimed.

## Broad repository refresh

Linux Fieldwork has continued broad non-Debian work since the prior checkpoint, including active coreutils, libarchive, systemd, runc, jq, BuildKit, kmod, fsck/udev, and repository-evidence carriers. LF-35 therefore remains an intake and comparison lane rather than the sole active queue.

This pass did not stop broader reconnaissance. It avoided duplicating public implementations while opening a new exact comparison where the public solution introduced a materially different authority model.

## First incomplete gates

1. Classify uv PR #35 exact base-versus-candidate matrix and retained artifacts.
2. Decide whether sibling-owned index success is intended workspace policy or excessive authority expansion.
3. Classify uv PR #30 after the repaired rewriter reaches formatting, compile, native tests, and the backend matrix.
4. Classify Biome PR #2 after the fixture reaches analyzer assertions.
5. Classify Biome PR #3 after the stable-feature watcher test runs.
6. Preserve any new harness failure separately from product behavior and repair the first owning layer only.
7. Continue broad scouting in parallel; recheck public overlap immediately before creating implementation branches.

## Authority

All writes in this pass were limited to controlled `teamleaderleo/*` repositories. No canonical-upstream issue, pull request, comment, review, reaction, email, or other contact was created or performed.
