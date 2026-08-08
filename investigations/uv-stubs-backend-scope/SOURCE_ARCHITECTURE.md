# UV stub-only design: current-source architecture pass

State: `SOURCE REVIEW — SUPPORTS DESIGN DEBATE, NO PRODUCT CHANGE`

Date: 2026-08-09

Source snapshot: `astral-sh/uv@dd0584d560a4693b5713a78be54304123ada3e77`.

External source links in this record use the requested redirect form:

- https://redirect.github.com/astral-sh/uv/blob/dd0584d560a4693b5713a78be54304123ada3e77/crates/uv/src/commands/project/init.rs
- https://redirect.github.com/astral-sh/uv/blob/dd0584d560a4693b5713a78be54304123ada3e77/crates/uv-configuration/src/project_build_backend.rs

## TL;DR

The current source layout supports the design direction, but it suggests a narrower implementation shape than literally adding `StubOnly` to UV's existing `InitProjectKind` enum.

`InitProjectKind` currently represents CLI/scaffold shape: packaged application, flat application, library, bare project, or bare project with a build system. Stub-only status is orthogonal content semantics derived from the distribution name. A separate one-time classification such as `PackageContentKind::{Runtime, StubOnly}` (name illustrative only) would preserve that distinction and could be passed into the existing centralized generation functions.

Three current choke points already line up with the proposed model:

1. `pyproject_build_system(...)` centralizes backend declarations and backend-specific `[tool.*]` config;
2. `pyproject_build_backend_prerequisites(...)` centralizes Cargo/CMake starter generation for Maturin and Scikit-build;
3. `generate_package_scripts(...)` centralizes source/package generation and the pure-Python versus binary starter split.

That means a backend-capability implementation does not need suffix checks scattered throughout unrelated code. It can classify stub-only once, validate the `(content kind, backend)` pair, and thread that state through these existing boundaries.

## Existing project-kind meaning

Current `InitProjectKind` variants are:

```text
ApplicationWithLibrary
Application
Library
Bare
BareWithBuildSystem
```

The enum therefore answers questions such as:

- should UV make a packaged application with a console entry point?
- should UV make a flat `main.py` application?
- should UV make a library?
- should UV generate source files at all?

It does not currently encode the nature of the packaged content.

A `foo-stubs` request changes that content nature. In particular, a packaged-application-shaped request normally creates `[project.scripts]`, but the stub-only interpretation must suppress runtime application behavior. Treating stub-only as a separate semantic value makes that override explicit without turning the existing scaffold-shape enum into a mixed-purpose type.

## Existing backend adapter point

`pyproject_build_system(package, build_backend)` already owns all generated backend requirements and most backend-specific configuration.

Current examples include:

```text
Hatch       -> hatchling
Flit        -> flit_core>=3.2,<4
PDM         -> pdm-backend
Poetry      -> poetry-core>=2,<3
setuptools  -> setuptools>=61
Maturin     -> [tool.maturin] + maturin>=1.0,<2.0
Scikit      -> [tool.scikit-build] + scikit-build-core>=0.12 + pybind11>=3
```

This is the natural place for stub-only conditional backend configuration and feature floors:

- Hatch package selection;
- Poetry `packages` declaration;
- Flit 4.x requirement;
- PDM minimum stub-support version;
- setuptools minimum implicit-`.pyi` version.

The function would need project/content semantics as an input, but the current organization already avoids needing a new backend configuration subsystem.

## Existing prerequisite point strengthens early rejection

`pyproject_build_backend_prerequisites(...)` currently writes backend starter files:

- Maturin writes `Cargo.toml` for a PyO3 `cdylib`;
- Scikit writes `CMakeLists.txt` for a pybind11 extension.

This is strong source evidence that UV's current Maturin and Scikit selectors mean native-extension starters, not generic Python file packagers.

For a stub-only request, compatibility validation should therefore happen before this function runs. Otherwise UV can create native starter files for a project kind it later decides is incompatible.

For Maturin, the research says pure stub-only is unsupported, so reject before `Cargo.toml` generation.

For Scikit-build-core, the backend itself can copy an explicit Python package tree, but UV's current selector deliberately adds pybind11, writes CMake, and later writes C++ source. Supporting a pure-stub Scikit project would therefore be a separate template mode, not merely adding one package-data key to the existing starter. That strengthens the current recommendation to reject under today's selector semantics unless UV intentionally broadens the selector contract.

## Existing source-generation point

`generate_package_scripts(...)` currently:

1. derives `src/<normalized module name>`;
2. prepares pure-Python runtime source for ordinary backends;
3. for Maturin/Scikit, generates native source plus `_core.pyi` and a Python wrapper;
4. writes the runtime package initializer.

A stub-only content branch belongs near the top of this function or in a small sibling generator invoked from the same call site:

```text
if StubOnly:
    create src/foo-stubs/
    write __init__.pyi
    do not generate runtime wrapper/main/native starter source
else:
    existing runtime path
```

The exact factoring is open, but source generation has one obvious owner today.

## Suggested source-level flow

A current-source-shaped implementation could look conceptually like:

```text
resolve existing InitProjectKind
resolve build backend
classify package content once from project identity
validate content/backend capability
render project metadata
conditionally render runtime script metadata
render backend config using content/backend policy
generate backend prerequisites only when compatible
generate stub or runtime source through one source-generation boundary
```

This is intentionally different from creating one giant `(StubOnly, Backend)` generator per backend. Common stub files should stay common; backend adapters should stay small.

## PEP 561 naming implication

PEP 561 says the name of a separately distributed stub package **must** follow the `foopkg-stubs` scheme, and that the `*-stubs` name itself is enough to identify the distribution as typing information without a `py.typed` marker.

That makes interpreting a generated `foo-stubs` project as stub-only semantics a standards-aligned default, not an arbitrary UV naming convention. A reviewer should still look for a credible counterexample where `uv init --package something-stubs` is intentionally meant to create ordinary runtime code; issue #476 explicitly asks for that challenge.

PEP: https://peps.python.org/pep-0561/#stub-only-packages

## Open design questions after source review

1. What should the orthogonal content-semantic type be called, if a type is introduced at all?
2. Should stub-only classification apply only to packaged source-generating modes, leaving `--bare` behavior untouched?
3. Should compatibility validation happen before any filesystem/VCS initialization, or only before backend/source files are written?
4. Should backend capability policy live as methods near `ProjectBuildBackend`, or remain in project-init code so the configuration crate does not acquire scaffold-specific semantics?
5. Should Scikit rejection be permanent for this selector, or should a future explicit pure-Python/extension mode split make the backend eligible?

## Current conclusion

The current source does not argue for a broad rewrite. It argues for a small orthogonal semantic classification threaded through already-centralized initialization owners.

That is a stronger and more idiomatic implementation direction than scattered `name.ends_with("-stubs")` checks, and more precise than overloading the existing `InitProjectKind` enum with a different conceptual dimension.

No product candidate was modified and no canonical upstream interaction was made.
