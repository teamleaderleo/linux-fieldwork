# UV simple-stub initialization: bool vs scaffold type experiment

State: `EXECUTED — KEEP THE LOCAL BOOLEAN`

Date: 2026-08-09

Related internal work: #475, #476, `teamleaderleo/uv#82`.

External context only:

- https://redirect.github.com/astral-sh/uv/issues/19663
- https://redirect.github.com/astral-sh/uv/pull/19671

No canonical upstream interaction is authorized by this record.

## Question

The selected narrow design needs one internal value that answers whether UV should apply the generated simple-stub scaffold behavior at the existing project-init choke points.

Compare:

1. the current local boolean, conceptually `simple_stub: bool`; and
2. a small semantic type:

```rust
#[derive(Debug, Copy, Clone, Eq, PartialEq)]
enum PackageScaffold {
    Runtime,
    SimpleStub,
}
```

The experiment keeps behavior constant. It asks only whether the extra type makes the current two-way implementation clearer or safer.

## Executed source

Common product source:

```text
teamleaderleo/uv#82 direction / green Scikit-support comparator
source commit: 1993c1e81ec8446d2db76308c4d516fdf23d5162
upstream ancestor: dd0584d560a4693b5713a78be54304123ada3e77
```

Disposable Fieldwork execution carrier:

```text
teamleaderleo/linux-fieldwork#491
run: 31290923478
job: 93187796036
runner: Ubuntu 24.04
conclusion: success
```

The carrier rewrote only `crates/uv/src/commands/project/init.rs` from boolean plumbing to the two-case enum and ran:

```text
cargo fmt --all
git diff --check
cargo check --locked -p uv
cargo test --locked -p uv --test project init::init_package_stubs_backends -- --exact
cargo test --locked -p uv --test project init::init_app_build_backend_scikit -- --exact
cargo test --locked -p uv --test project init::init_lib_build_backend_scikit -- --exact
```

All gates passed.

## Exact representation delta

Boolean → enum:

```text
crates/uv/src/commands/project/init.rs | 61 ++++++++++++++++++++++------------
1 file changed, 39 insertions(+), 22 deletions(-)
```

The enum variant added the type plus an `is_simple_stub()` helper and changed the existing conditional plumbing from forms such as:

```rust
if simple_stub { ... }
if !simple_stub { ... }
ProjectBuildBackend::Hatch if simple_stub => ...
```

to forms such as:

```rust
if scaffold.is_simple_stub() { ... }
if !scaffold.is_simple_stub() { ... }
ProjectBuildBackend::Hatch if scaffold.is_simple_stub() => ...
```

It is technically valid, but it does not reduce branching or centralize policy further than the boolean already does.

## The decisive semantic problem: bare has no package scaffold

`InitProjectKind::BareWithBuildSystem` legitimately uses `pyproject_build_system(...)` while deliberately generating **no package source scaffold**.

A two-case enum forces that path to be called:

```text
PackageScaffold::Runtime
```

even though no runtime package scaffold exists.

That label is semantically stronger than the program state warrants.

Representing the current source truth honestly would require one of:

```rust
Option<PackageScaffold>
```

or:

```rust
enum PackageScaffold {
    None,
    Runtime,
    SimpleStub,
}
```

Either form adds another state and more matching/plumbing solely to express a distinction the current bug does not need.

The boolean has the narrower and more accurate meaning:

> Should this generated init path receive the simple-stub adaptation?

`false` does not claim that a runtime package scaffold exists. It also naturally covers bare build-system rendering.

## Why not a backend capability table either

The same pass reviewed the backend rendering in the green implementation.

The backend differences are not uniform data:

- Hatch adds a wheel-package selection table;
- Poetry adds a package mapping with `from = "src"`;
- PDM adds `includes`;
- setuptools adds wildcard package data;
- Flit changes the backend requirement floor;
- Scikit/Maturin are selected policy rejections in the conservative product candidate.

A generic capability/config table would need backend-specific variants, callbacks, or mini templates to represent those differences. That would hide the generated TOML behind another abstraction without removing the real semantic differences.

The explicit guarded `match` arms are therefore preferable for this patch: Rust keeps the backend list exhaustive and each generated backend delta remains visible where reviewers expect it.

## Comparison against the current controlled product candidate

Current controlled product candidate `teamleaderleo/uv#82` already uses the preferred shape:

```rust
let simple_stub = matches!(self, Self::ApplicationWithLibrary | Self::Library)
    && is_simple_stub_project(name);
```

and threads that boolean only through the relevant init/template generation boundaries.

It also passes `false` explicitly for `BareWithBuildSystem`, which accurately means “do not apply simple-stub template adaptation” without asserting a runtime scaffold.

No product change is needed from this representation experiment.

## Result

**Keep the local `simple_stub: bool` for the current bug fix.**

The orthogonality discovered during design review remains conceptually useful—stub scaffold semantics should not be encoded as another `InitProjectKind`—but the implementation does not need a dedicated enum while there is only one special generated adaptation.

Introduce a semantic scaffold type later only if UV gains multiple real generated package-content modes whose behavior cannot be represented clearly by one predicate.

## Implementation guardrail

Preferred shape:

```text
resolve current project kind and canonical project name
compute simple_stub once on source-generating packaged/library paths
validate selected backend when simple_stub
render existing backend template with small explicit stub deltas
write simple stub source or existing runtime/native source
```

Avoid:

- adding `SimpleStub` to `InitProjectKind`;
- adding a two-case enum that mislabels bare paths;
- adding a three-case/optional scaffold type solely for this bug;
- building a backend capability registry around a handful of explicit generated-template differences.

No UV product branch was changed by this experiment and no canonical upstream interaction was made.
