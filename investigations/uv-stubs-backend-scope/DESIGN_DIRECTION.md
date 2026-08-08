# UV stub-only initialization: design direction after backend research

State: `PROPOSAL FOR INTERNAL DEBATE — NO PRODUCT CHANGE`  
Date: 2026-08-09  
Research inputs: Linux Fieldwork #458 and #459  
Controlled containment candidate: `teamleaderleo/uv#54`  
Canonical upstream bug: [astral-sh/uv#19663](https://redirect.github.com/astral-sh/uv/issues/19663)  
Current upstream candidate: [astral-sh/uv#19671](https://redirect.github.com/astral-sh/uv/pull/19671)  
Further upstream mutation authorized by this record: `false`

## TL;DR

Treat a distribution whose project name is a PEP 561 `*-stubs` name as a **stub-only project kind**, independent of the selected build backend.

The common project-kind layer should generate the stub source shape and suppress runtime behavior:

```text
src/foo-stubs/__init__.pyi
```

with no generated runtime `main()` and no `[project.scripts]` entry.

The backend layer should then answer a separate capability question: can this backend package that stub-only tree directly, does it need backend-specific configuration or a minimum backend version, or is the backend/project combination unsupported and better rejected during `uv init`?

This proposal supersedes the earlier working idea that stub-only behavior should be scoped only to `uv_build`. The `uv_build`-only candidate remains useful as a containment control because it proved the cross-backend regression mechanism, but it would turn `foo-stubs` back into an ordinary runtime package whenever a third-party backend is selected.

## Explain like I'm five

`foo-stubs` says what kind of package the user is trying to make: a package of type information rather than runnable Python code.

Hatch, Poetry, Flit, PDM, setuptools, Scikit-build, Maturin, and `uv_build` are different machines for putting files into a Python distribution. Choosing a different machine should not silently change the thing being built from “typing stubs” into “normal Python program.”

So UV should first decide **what the project is**, then ask **how the chosen backend expresses that project**.

## Why care

The upstream candidate correctly generates the PEP 561 layout for `uv_build`, but applying the shared hyphenated path without backend-specific policy breaks generated Hatch, Poetry, Flit, and Maturin projects.

The first controlled repair scoped the special behavior to `uv_build`, which restored an all-green build matrix. Later research showed why that is only a containment fix: several third-party backends can build a genuine `foo-stubs` distribution, but some require explicit configuration or newer backend versions, while Maturin is not an appropriate pure-stub backend.

The product decision therefore is not “special-case `uv_build` or break the others.” The product decision is how `uv init` should map one stub-only project kind onto several backend capability contracts.

## Evidence boundary

This document is a design synthesis, not new product execution.

Executed artifact evidence from #458 establishes the Hatch, Poetry, and Flit rows for the fixed fixture `src/foo-stubs/__init__.pyi`:

- Hatchling 1.31.0 succeeds with explicit `packages = ["src/foo-stubs"]` and ships `foo-stubs/__init__.pyi`.
- Poetry Core 2.4.1 requires `{ include = "foo-stubs", from = "src" }` for the `src/` layout and ships `foo-stubs/__init__.pyi`.
- Flit Core 3.12.0 under UV's current `flit_core>=3.2,<4` requirement fails; Flit Core 4.0.2 succeeds directly with the same stub tree.

#459 established the remaining capability/version model from current source plus partial execution:

- PDM Backend has direct `*-stubs` support beginning at 2.4.4; the hosted carrier built a PDM 2.4.9 wheel containing `foo-stubs/__init__.pyi`.
- Modern setuptools packages the stub tree directly, while the hosted discriminator showed setuptools 68.2.2 building a wheel that omitted the `.pyi`; source history places implicit `.pyi` inclusion at setuptools 69.
- Scikit-build-core can copy the tree with explicit pure-Python configuration, but that configuration changes the semantics of UV's current Scikit starter away from its CMake/pybind11 extension template.
- Maturin's documented project model does not support a pure stub-only distribution as the package being built.

The #459 hosted matrix stopped after the expected setuptools-68 discriminator because the carrier shell still treated that expected negative case as fatal. The PDM and setuptools observations above are executed; the Scikit/Maturin policy remains grounded in the backend/source contract rather than a complete green execution matrix. That incomplete carrier should not be described as whole-matrix execution evidence.

## Proposed semantic model

Keep project-kind detection and backend adaptation separate.

Conceptually:

```text
project name
    |
    +-- ordinary distribution --------------------------+
    |                                                   |
    +-- PEP 561 *-stubs distribution -> StubOnly -------+--> backend adapter
                                                         |
                                                         +--> files
                                                         +--> pyproject config
                                                         +--> version floor
                                                         +--> supported/rejected
```

The exact Rust type is open to implementation review. The important invariant is that stub-only status is derived once and carried as semantic state instead of rediscovered through scattered backend/name checks.

A possible shape is:

```rust
// Illustrative only.
enum PythonProjectKind {
    Runtime,
    StubOnly,
}
```

or a narrower `StubPackage` value attached to the existing initialization kind. The design does not depend on introducing this exact enum.

## Common stub-only behavior

For a distribution such as `foo-stubs`, every supported backend should start from the same user-facing project meaning:

```text
src/foo-stubs/__init__.pyi
```

and should not generate:

```text
src/foo_stubs/__init__.py
```

for the purpose of pretending the distribution is an ordinary runtime package.

The scaffold should also omit a runtime console-script entry because there is no generated runtime module for such an entry point to call.

This common behavior should be decided before backend-specific configuration is rendered.

## Proposed backend policy

| Backend | Research classification | Proposed `uv init` policy for `foo-stubs` |
|---|---|---|
| `uv_build` | direct support | Generate the common stub tree; no extra backend config. |
| Hatch | explicit config | Generate the common stub tree plus `[tool.hatch.build.targets.wheel] packages = ["src/foo-stubs"]`. |
| Poetry | explicit config | Generate the common stub tree plus `[tool.poetry] packages = [{ include = "foo-stubs", from = "src" }]`. |
| Flit | direct support in 4.x | Generate the common stub tree and select a Flit 4.x build requirement. |
| PDM | direct support from 2.4.4 | Generate the common stub tree and require `pdm-backend>=2.4.4` for stub-only scaffolds. |
| setuptools | direct support from 69 for implicit `.pyi` data | Generate the common stub tree and require `setuptools>=69` for stub-only scaffolds. |
| Scikit-build-core | possible only with an explicit pure-Python configuration that changes UV's current template meaning | Prefer rejecting the combination under the existing `--build-backend scikit` contract. Revisit only if UV intentionally adds a separate pure-stub Scikit template. |
| Maturin | unsupported for pure stub-only distribution | Reject the combination during initialization with a clear diagnostic. |

## Why backend-specific configuration is preferable to backend-specific project meaning

The name `foo-stubs` is user input describing a distribution identity with established PEP 561 semantics. A backend selector should choose packaging machinery, not reinterpret that identity as a normal runtime package merely to preserve old build success.

This distinction also fixes the misleading success criterion from the earlier matrix. A generated project is not a successful `foo-stubs` scaffold merely because `uv build` exits zero. The resulting wheel should actually contain the stub package path, for example:

```text
foo-stubs/__init__.pyi
```

A wheel containing only normalized runtime-package output, or a wheel that omits the sole `.pyi`, is not equivalent evidence.

## Version floors should be capability floors

Where the template depends on a backend feature introduced at a known release, the generated build requirement should guarantee that feature.

Proposed narrow floors for stub-only projects:

```toml
# PDM stub-only project
[build-system]
requires = ["pdm-backend>=2.4.4"]
build-backend = "pdm.backend"
```

```toml
# setuptools stub-only project
[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"
```

For Flit, the conservative stub-specific form is:

```toml
[build-system]
requires = ["flit_core>=4,<5"]
build-backend = "flit_core.buildapi"
```

These do **not** imply that UV must raise the backend requirement for every ordinary project. Keeping the version change conditional on the project feature keeps the compatibility surface narrow.

A reviewer may reasonably prefer a general Flit template upgrade from `<4` to `<5` now that Flit 4 is released. That is a separate compatibility decision and should be argued on its own merits rather than being hidden inside the stub fix.

## Rejection is part of correct generation

If a selected backend cannot honestly represent the requested project kind, `uv init` should fail before writing a misleading project that only fails later during `uv build`.

For Maturin, the useful diagnostic should explain that pure stub-only packages are not supported by that backend and suggest choosing a Python packaging backend that supports the project kind.

For Scikit-build, the diagnostic should be about UV's current template contract, not a claim that scikit-build-core can never package Python files. The important distinction is:

- backend capability: scikit-build-core can copy an explicit Python package tree;
- UV selector meaning: the current Scikit starter is a CMake/pybind11 extension project.

Supporting `foo-stubs + scikit` would therefore be a new pure-stub Scikit template, not a small metadata tweak to the existing extension starter.

## Suggested internal implementation boundary

Avoid scattering checks of the package-name suffix through script generation, source-directory generation, and build-system generation independently.

A cleaner flow is conceptually:

```text
1. classify project kind once
2. validate (project kind, backend) capability
3. generate common project-kind files
4. render backend build-system/config adaptation
5. generate runtime-only files/scripts only for runtime project kinds
```

Illustratively:

```rust
match (project_kind, build_backend) {
    (StubOnly, Uv) => generate_stub_project(...),
    (StubOnly, Hatch) => generate_stub_project_with_hatch_config(...),
    (StubOnly, Poetry) => generate_stub_project_with_poetry_config(...),
    (StubOnly, Flit) => generate_stub_project_with_flit4(...),
    (StubOnly, Pdm) => generate_stub_project_with_pdm_floor(...),
    (StubOnly, Setuptools) => generate_stub_project_with_setuptools_floor(...),
    (StubOnly, Maturin | Scikit) => reject_unsupported_combination(...),
    (Runtime, backend) => existing_runtime_behavior(...),
}
```

This snippet is explanatory, not a recommendation to duplicate complete generators per backend. An implementation should probably share the common stub-tree generation and keep backend adaptation small.

## Test contract for a future product candidate

Build success alone is insufficient. A future candidate should assert the generated project and final artifact contract.

For every supported stub-only backend:

1. `uv init --package foo-stubs --build-backend <backend>` succeeds;
2. generated source contains `src/foo-stubs/__init__.pyi`;
3. generated source does not contain `src/foo_stubs/__init__.py` as the scaffolded package implementation;
4. generated `pyproject.toml` contains no runtime script entry for the stub package;
5. backend-specific config/version floor matches the intended adapter;
6. `uv build` succeeds;
7. the wheel contains `foo-stubs/__init__.pyi`;
8. the wheel does not gain a runtime console entry point from the scaffold.

For rejected combinations:

1. initialization fails before misleading backend starter files are produced;
2. the error names the incompatible project/backend combination;
3. the message suggests a supported class of backend without claiming that every alternative has identical configuration.

Negative controls should include ordinary non-`-stubs` package and library projects for each backend so the new project-kind path cannot silently alter existing runtime scaffolds.

## What the existing controlled candidate still proves

`teamleaderleo/uv#54` remains useful evidence even if this design replaces it as a product direction.

Its all-backend green matrix demonstrated that the public candidate's regressions come from applying the shared stub path/script behavior without backend adaptation. That makes it a good containment control.

It should not be promoted as the final semantic model without an explicit decision to make third-party backend selection change `foo-stubs` back into a runtime package. The backend research gives us a stronger alternative, so retaining #54 as provenance/control is more useful than silently extending it into a new design.

## Debate points

The main questions worth arguing internally are:

1. **Project-kind representation:** should stub-only be a formal internal project kind, a smaller capability flag/value, or another representation that still guarantees one-time classification?
2. **Flit policy:** use Flit 4 only for stub-only projects, or upgrade UV's general Flit template to 4.x?
3. **Version-floor style:** make PDM/setuptools capability floors conditional on stub-only generation, or raise their general template floors?
4. **Scikit policy:** reject under the existing extension-template meaning, or intentionally introduce a separate pure-stub Scikit template?
5. **Diagnostic timing:** validate incompatible backend/project combinations before any backend prerequisite files are written.
6. **Artifact tests:** how much wheel inspection belongs in UV integration tests versus generated-tree assertions plus backend-specific fixtures?

None of those questions requires changing the controlled UV product candidate before the design is chosen.

## Current recommendation

Use this as the working design direction for debate:

> `foo-stubs` selects stub-only project semantics first; the selected backend then supplies a capability/configuration adapter. Supported backends generate the same PEP 561 stub tree with backend-specific metadata or version floors. Incompatible backend/project combinations are rejected early rather than silently converted into ordinary runtime packages.

Before product implementation, finish or explicitly close the remaining #459 execution gap so the evidence record cleanly distinguishes executed artifact proof from source-backed policy. Then choose the backend policy and build a new candidate from current UV main rather than mutating the older containment candidate in place.

## Publication boundary

This is an internal design record. It grants no authority for another canonical UV comment, review, reaction, pull request, email, or other maintainer contact. Any third-party GitHub references written into controlled-repository interaction text should use `redirect.github.com`.