# UV simple-stub design: current-source architecture

State: `EXECUTED ARCHITECTURE DIRECTION — NO PRODUCT CHANGE ON THIS RECORD`

Date: 2026-08-09

Source snapshot: `astral-sh/uv@dd0584d560a4693b5713a78be54304123ada3e77`.

Controlled implementation reference: `teamleaderleo/uv#82`.

External source links in this record use redirect form:

- https://redirect.github.com/astral-sh/uv/blob/dd0584d560a4693b5713a78be54304123ada3e77/crates/uv/src/commands/project/init.rs
- https://redirect.github.com/astral-sh/uv/blob/dd0584d560a4693b5713a78be54304123ada3e77/crates/uv-configuration/src/project_build_backend.rs

## TL;DR

The current source supports a narrow implementation:

- keep `InitProjectKind` unchanged;
- resolve the canonical project name first;
- compute one local `simple_stub: bool` on source-generating packaged/library paths;
- validate the selected backend before filesystem/VCS side effects for rejected combinations;
- thread that boolean through the existing project-init/template owners;
- keep backend deltas as explicit match arms/config helpers rather than adding a capability framework.

An executed bool-vs-enum experiment confirms that a dedicated `PackageScaffold` type is unnecessary for this bug fix. See `SCAFFOLD_TYPE_EXPERIMENT.md`.

## Existing project-kind meaning

Current `InitProjectKind` variants are:

```text
ApplicationWithLibrary
Application
Library
Bare
BareWithBuildSystem
```

They answer scaffold-shape questions:

- packaged application or flat application;
- library;
- bare metadata only;
- bare metadata plus build system.

They should continue to do that. The simple-stub rule is an orthogonal **generated-template adaptation**, not another public/project-kind mode.

Do not add `SimpleStub` to `InitProjectKind`.

## Why a local boolean beats a scaffold enum here

The architecture review originally suggested a conceptual content type such as `PackageContentKind::{Runtime, StubOnly}` to preserve orthogonality.

That concept was useful for reasoning, but the implementation hypothesis has now been tested.

Internal Fieldwork #491 rewrote the green implementation from `simple_stub: bool` to:

```rust
enum PackageScaffold {
    Runtime,
    SimpleStub,
}
```

and passed formatting, `cargo check`, the simple-stub backend test, and ordinary Scikit app/library tests.

The rewrite cost:

```text
crates/uv/src/commands/project/init.rs | 61 ++++++++++++++++++++++------------
1 file changed, 39 insertions(+), 22 deletions(-)
```

More importantly, `BareWithBuildSystem` uses the backend renderer while deliberately generating **no package scaffold**. A two-case enum calls that state `Runtime`, which is false. Modeling it honestly requires `Option<PackageScaffold>` or a third `None` case.

The boolean is more precise for the current implementation question:

> Should this init path receive the simple-stub adaptation?

`false` can correctly mean ordinary runtime generation **or** no generated package scaffold at all.

Therefore the selected implementation representation is the local boolean. Introduce a richer scaffold type only if future work creates multiple genuine generated package-content modes.

## Existing ownership points

Current UV source already centralizes the relevant work.

### 1. Project/build-system rendering

`pyproject_build_system(...)` owns backend requirements and backend-specific build-system declarations.

The selected product candidate also uses a small `pyproject_simple_stub_config(...)` helper for the backend-specific package-selection/data tables.

This is the right boundary for:

- Hatch `packages = ["src/foo-stubs"]`;
- Poetry package mapping from `src`;
- PDM `includes`;
- setuptools wildcard `.pyi` package data;
- conditional Flit 4 requirement.

### 2. Compatibility validation

A small `validate_simple_stub_backend(...)` helper belongs before `create_dir_all`/VCS initialization for combinations the selected policy rejects.

Current conservative policy rejects source-generating simple-stub scaffolds for:

- Maturin, because the backend/template requires a Rust project;
- Scikit, not because scikit-build-core lacks capability, but because UV's selected first-fix policy preserves the current extension-module starter family.

`--bare` bypasses this inference and remains the custom-layout path.

### 3. Package source generation

`generate_package_scripts(...)` already owns normal runtime/native package source generation.

The simple-stub branch belongs at the same boundary:

```text
src/foo-stubs/__init__.pyi
```

then return without generating:

- runtime `__init__.py`;
- application `main()`;
- native starter source;
- `_core.pyi` wrapper material.

### 4. Runtime script metadata

The packaged-application path normally emits `[project.scripts]`.

The simple-stub predicate suppresses that metadata because the generated scaffold has no runtime target.

## Keep backend policy explicit

The backend differences are genuinely heterogeneous:

- Hatch: explicit wheel package selection;
- Poetry: package mapping with `from = "src"`;
- PDM: explicit include path;
- setuptools: package data;
- Flit: requirement-floor change;
- Maturin/Scikit: selected rejection policy.

A general capability table would need special variants or callbacks to encode these different output shapes. That would move the same branching behind a new abstraction while making the generated TOML harder to review.

Prefer explicit exhaustive match arms/helpers in project-init code. Rust will force a decision when another `ProjectBuildBackend` variant is added.

Do not move scaffold-specific policy into resolver, installer, lockfile, or generic configuration subsystems.

## Naming and standards boundary

Do not state that every distribution whose project name ends in `-stubs` is normatively a stub-only distribution.

The current typing specification constrains installed stub-package naming but allows distribution/project naming to differ, and real stub distributions may have richer layouts or helper runtime code.

For this bug, the suffix is a **UV default-scaffold heuristic** because UV normally derives the generated package layout from the project name.

The selected simple scaffold is intentionally narrow:

```text
src/foo-stubs/__init__.pyi
```

It is not intended to cover namespace-stub layouts, partial stubs, arbitrary distribution→import mappings, or richer mixed distributions.

## Source-shaped flow

The selected architecture is:

```text
resolve current InitProjectKind
resolve final canonical project name
resolve selected build backend
compute simple_stub once for packaged/library source-generating modes
if simple_stub:
    validate backend before filesystem/VCS side effects
render project metadata
suppress runtime script metadata when simple_stub
render existing build system plus small explicit stub backend config
write simple stub source or existing runtime/native source
```

`Bare` and `BareWithBuildSystem` do not receive simple-stub source adaptation.

## Current controlled candidate

`teamleaderleo/uv#82` already follows this shape:

```rust
let simple_stub = matches!(self, Self::ApplicationWithLibrary | Self::Library)
    && is_simple_stub_project(name);
```

It uses the boolean through the existing backend/source boundaries and explicitly passes `false` for the bare build-system path.

That matches the executed representation result, so the bool-vs-enum experiment does not call for another product rewrite.

## Reopen conditions

Revisit the representation only if UV gains multiple real generated package-content modes such that one boolean no longer names the decision accurately.

Revisit backend abstraction only if enough backends acquire structurally identical policy that an explicit helper/table removes real duplication without hiding generated output.

Neither condition exists for the current bug fix.

No canonical upstream interaction was made.
