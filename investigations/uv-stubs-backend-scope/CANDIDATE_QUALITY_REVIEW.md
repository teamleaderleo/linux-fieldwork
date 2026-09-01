# UV simple-stub candidate: quality and history review

State: `CURRENT-MAIN PRODUCT TREE PRESERVED; HISTORY HYGIENE REPAIRED`

Date: 2026-08-09

Controlled candidate: `teamleaderleo/uv#82`

External context only:

- https://redirect.github.com/astral-sh/uv/issues/19663
- https://redirect.github.com/astral-sh/uv/pull/19671

No canonical upstream interaction is authorized by this record.

## Source freshness

Current upstream `astral-sh/uv` main remains:

```text
dd0584d560a4693b5713a78be54304123ada3e77
```

The candidate comparison base points exactly at that commit.

## Product tree

Current candidate head after hygiene repair:

```text
64f94a41fd7c472224d340337dd4b6cab2a7d3fd
```

It is exactly one product commit ahead of the upstream base and changes exactly two files:

```text
crates/uv/src/commands/project/init.rs  +108/-20
crates/uv/tests/project/init.rs         +160
```

No temporary workflow/execution file exists in the current candidate tree or product history.

## History hygiene finding and repair

Before this pass, #82 had the correct final two-file tree but was 20 commits ahead of the upstream base. The PR description and final head commit showed that temporary materialization/rollback workflows had existed and later been removed inside the same product branch history.

Old head:

```text
488125f382d1987a9657eb2d190cf0db9f4fa7ae
```

Its final commit was `Remove temporary explicit-app rollback workflow`.

That violated the Fieldwork source-branch rule even though the final diff was clean: execution machinery and product candidate history were not separated.

### Repair

The old final product/test blob IDs were read directly:

```text
crates/uv/src/commands/project/init.rs
40234899bbb4a7a9499a67fa0c007215f3c7c05f

crates/uv/tests/project/init.rs
c5cc9e3b5c8ff2ce0812a7bf1d3976099c220b93
```

A new Git tree was created from the exact upstream base with only those two final blobs, then committed once as:

```text
64f94a41fd7c472224d340337dd4b6cab2a7d3fd
Implement simple stub scaffold backend adapters
```

The #82 head branch was moved to that one-commit history only after confirming the PR head had not changed underneath the repair.

The prior 20-commit history remains available at:

```text
research/19671-simple-stub-candidate-history-pre-squash
```

for provenance.

## Tree-equivalence evidence

The clean head has the same two final blob IDs as the old artifact-tested head:

```text
init.rs  40234899bbb4a7a9499a67fa0c007215f3c7c05f
tests    c5cc9e3b5c8ff2ce0812a7bf1d3976099c220b93
```

Both base comparisons are exactly the same two-file `+268/-20` product/test diff.

Therefore the existing exact-tree artifact receipt remains evidence for the implementation content:

```text
run: 31291276332
job: 93188764477
conclusion: success
old head carrying identical tree: 488125f382d1987a9657eb2d190cf0db9f4fa7ae
```

That matrix proved:

- default `uv_build` build success;
- correct Hatch/Poetry/Flit/PDM/setuptools stub wheels with no runtime console script;
- Scikit/Maturin selected rejection before target-directory side effects;
- `--bare` controls;
- ordinary Hatch/Flit/Scikit behavior unchanged.

A fresh normal UV CI run is attached to the new clean commit and should be treated as the authoritative **branch-health** receipt after the history rewrite. Tree-equivalent artifact evidence does not replace branch CI status reporting.

## Canonical-name review

The candidate checks:

```rust
package.as_str().ends_with("-stubs")
```

on `PackageName`.

`PackageName` is already normalized by UV: it lowercases names and collapses runs of `-`, `_`, and `.` to a single `-`.

Therefore equivalent distribution spellings such as conceptually:

```text
Foo_Stubs
foo.stubs
foo---stubs
foo-stubs
```

all map to canonical `foo-stubs` before the scaffold heuristic runs.

That is intentional for this design: the rule is defined on the **canonical project name**, not the user's original separator/case spelling. No new normalization logic belongs in the patch.

A direct candidate test for every equivalent spelling is optional rather than required because the normalization contract is already owned and tested by `uv-normalize`; duplicating its matrix in `uv init` would add low-value regression surface.

## Rejection ordering review

The selected Scikit/Maturin validation runs inside `InitProjectKind::init` before:

```text
create_dir_all(project path)
init_vcs(...)
```

and therefore satisfies the chosen contract: rejected generated templates do not leave a target project directory or Git repository behind.

However `init_project(...)` performs workspace discovery and `determine_requires_python(...)` first. `determine_requires_python` may call `PythonInstallation::find_or_download` for some Python requests or for the default interpreter.

So the current implementation does **not** promise “no work/side effects of any kind before rejection.”

Moving the validation earlier would change error precedence against workspace/Python-resolution errors and broaden the patch beyond the reported project-scaffold side-effect problem.

Disposition: keep the narrower tested contract—**before project-directory/VCS side effects**—unless a concrete issue demonstrates that Python/workspace resolution before deterministic backend rejection is harmful.

## Representation review

The current candidate uses one local `simple_stub: bool`, which the executed #491 comparison selected over a two-case scaffold enum.

No candidate change is needed.

## Test-shape review

The product test suite deliberately combines:

- one default `uv_build` end-to-end build test;
- table-driven generated config/source checks for affected pure-Python backends;
- rejection and `--bare` controls for Scikit/Maturin.

Third-party artifact execution remains in Fieldwork's hosted exact-head matrix instead of becoming permanent networked UV CI.

This split is appropriate for ownership: UV tests its generated templates, while Fieldwork supplies the external backend artifact receipts.

## Current disposition

Candidate architecture, content, and history are coherent with the selected first-fix policy.

Do not add new modes, scaffold enums, normalization code, or earlier global validation without a concrete failing case.

Remaining candidate work is ordinary review/CI hygiene rather than further architecture research.

No canonical upstream interaction was made.
