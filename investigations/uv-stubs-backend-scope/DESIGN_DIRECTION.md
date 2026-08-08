# UV simple-stub initialization: reconciled design direction

State: `PROPOSAL FOR INTERNAL DEBATE — NO PRODUCT CHANGE`  
Date: 2026-08-09  
Research inputs: Linux Fieldwork #458 and #459  
Independent challenge: Linux Fieldwork #476  
Controlled containment candidate: `teamleaderleo/uv#54`  
Canonical upstream bug: [astral-sh/uv#19663](https://redirect.github.com/astral-sh/uv/issues/19663)  
Current upstream candidate: [astral-sh/uv#19671](https://redirect.github.com/astral-sh/uv/pull/19671)  
Further upstream mutation authorized by this record: `false`

## Working conclusion

The bug can be fixed with a **narrow scaffold inference**, not a universal model of PEP 561 distributions.

When UV is synthesizing its normal project→package source layout and the project name normalizes to a `*-stubs` name, it is reasonable for the default scaffold to infer the common simple-stub shape:

```text
src/foo-stubs/__init__.pyi
```

with no generated runtime `main()` and no generated `[project.scripts]` entry.

The selected backend should then receive the smallest configuration needed to package that generated tree, or the source-generating template should reject a genuinely incompatible backend.

For ordinary project names, existing behavior remains unchanged.

## Critical scope correction from independent review

`project.name.ends_with("-stubs")` is **not** a normative statement that the finished distribution is globally "stub-only".

PEP 561 describes installed stub-package conventions, but real packaging can be richer:

- project/distribution naming and import-package layout are not required to be a one-to-one identity in every project;
- namespace stub packages need not have a root `__init__.pyi`;
- partial stub packages use `py.typed` with `partial`;
- a distribution can ship a `*-stubs` package and executable Python support code together.

A concrete counterexample is `django-stubs`, whose distribution includes both the stub package and runtime/plugin support code.

Therefore the internal concept should describe **what UV is generating by default**, not assert a permanent content invariant about the distribution.

Conceptual names such as `SimpleStubScaffold` or `GeneratedPackageContent::SimpleStub` are safer than `StubOnly`.

## Where the inference should apply

Apply the inference only on source-generating packaged initialization paths where UV is choosing the default package layout.

Do not apply it globally to every distribution object or every build-system declaration.

### Preserve `--bare`

`--bare` intentionally lets users create metadata/build-system scaffolding without UV creating the expected source files.

A project ending in `-stubs` should therefore remain allowed with `--bare --build-backend ...`, including Scikit and Maturin. The user may be supplying a custom layout or richer project that is outside the simple scaffold.

Backend rejection belongs to the **source-generating simple-stub scaffold**, not to the package name in isolation.

### Explicit app intent

If the eventual implementation can cheaply distinguish an explicit `--app --package` request from the ordinary inferred packaged scaffold, explicit user intent should be considered before silently overriding it with the name heuristic.

This is a small CLI-precedence question, not a reason to broaden the model. The reported bug and current research contract concern UV's generated default package layout for `foo-stubs`.

## Architectural boundary

Do not add `SimpleStub` as another value of the existing `InitProjectKind` unless implementation details make that clearly simpler.

`InitProjectKind` currently describes scaffold form such as packaged application, flat application, library, and bare project. The simple-stub inference is orthogonal generated-package content.

Current UV source already centralizes the relevant work in a few places:

- project/build-system rendering;
- backend prerequisite generation;
- package source generation;
- project-script generation.

The upstream patch can remain smaller than the internal model: a helper/derived value passed through those choke points is enough. Avoid a compatibility registry, trait hierarchy, or new user-facing mode.

## Executed backend evidence for the exact simple scaffold

Research target:

```text
project/distribution: foo-stubs
source:               src/foo-stubs/__init__.pyi
generated runtime CLI: absent
```

### `uv_build`

Direct support. Generate the common stub tree with no extra backend configuration.

### Hatch

Executed with `hatchling==1.31.0`.

Required generated config:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/foo-stubs"]
```

The wheel contains `foo-stubs/__init__.pyi` and no runtime console script.

Classification: **support with explicit config**.

### Poetry

Executed with `poetry-core==2.4.1`.

Required generated config for UV's `src/` layout:

```toml
[tool.poetry]
packages = [{ include = "foo-stubs", from = "src" }]
```

The wheel contains `foo-stubs/__init__.pyi` and no runtime console script.

Classification: **support with explicit config**.

### Flit

UV currently generates `flit_core>=3.2,<4`. The executed row resolved 3.12.0 and failed on the simple stub tree.

The same tree with `flit_core>=4,<5` resolved 4.0.2 and built correctly without extra package configuration.

Independent review also checked the apparent Flit 3 escape hatch: older Flit could accept a hyphenated module through `[tool.flit.module]`, but maintainers described that behavior as a bug and the old path still required `__init__.py`. Do not generate against accidental Flit 3 behavior.

Classification: **Flit 4 is the first stable clean path for this scaffold**.

Open policy: use Flit 4 only for simple-stub scaffolds or update the general Flit template.

### PDM

Current PDM has automatic stub discovery, but a newer floor is unnecessary.

Hosted lower-bound proof:

```toml
[tool.pdm.build]
includes = ["src/foo-stubs"]

[build-system]
requires = ["pdm-backend==2.1.4"]
build-backend = "pdm.backend"
```

produced the correct wheel with no console script. The unconfigured 2.1.4 control produced metadata only.

Classification: **support with explicit config; preserve UV's existing backend requirement**.

### setuptools

Setuptools 69 added implicit `.pyi` inclusion, but no new floor is needed.

Hosted lower-bound proof:

```toml
[tool.setuptools.package-data]
"*" = ["*.pyi"]

[build-system]
requires = ["setuptools==61.0.0"]
build-backend = "setuptools.build_meta"
```

produced the correct wheel with no console script. The unconfigured 61.0.0 control omitted the stub.

The wildcard is intentional: older pyproject schemas reject a package-specific `"foo-stubs"` key while permitting `"*"`.

Classification: **support with explicit config; preserve `setuptools>=61`**.

### Scikit-build-core

Artifact execution now proves all three important states with scikit-build-core 1.0.3:

1. explicit pure-Python configuration

   ```toml
   [tool.scikit-build]
   minimum-version = "build-system.requires"
   wheel.cmake = false
   wheel.packages = ["src/foo-stubs"]
   ```

   builds a correct wheel containing `foo-stubs/__init__.pyi` with no console script;

2. `wheel.cmake = false` without explicit `wheel.packages` builds a metadata-only wheel and misses the stub;
3. UV's current CMake-oriented contract fails on the pure stub fixture because it expects a CMake project.

This removes backend capability as an uncertainty. The remaining question is purely **UV template semantics**.

Two coherent policies remain:

- **support:** if `--build-backend scikit` means "use this backend for the requested scaffold", generate the CMake-less explicit package configuration;
- **reject:** if UV deliberately defines the current selector as an extension-module starter family, reject the source-generating simple-stub combination and preserve `--bare` as the custom-layout escape hatch.

Under the strict "scaffold first, backend adapter second" model, support is the internally consistent result. Rejection is still defensible as a product-template decision, but should not be described as backend incapability.

### Maturin

Artifact execution with Maturin 1.14.1 reached the backend and failed because the pure stub fixture has no Cargo project, matching maintainer/source guidance.

Classification: **incompatible with the source-generating simple-stub scaffold**.

Recommended behavior: reject before UV writes Cargo/PyO3 starter files, while preserving `--bare --build-backend maturin` for expert/custom projects.

## Reconciled matrix

| Backend | Exact simple-stub result | Suggested generated adapter |
|---|---|---|
| `uv_build` | direct | none |
| Hatch | explicit config | `packages = ["src/foo-stubs"]` |
| Poetry | explicit config | `{ include = "foo-stubs", from = "src" }` |
| Flit | stable support begins in 4.x | Flit 4.x requirement |
| PDM | explicit config works on older backend | `includes = ["src/foo-stubs"]`; preserve current requirement |
| setuptools | explicit config works at current UV floor | `"*" = ["*.pyi"]`; preserve `>=61` |
| Scikit-build-core | explicit pure-Python config artifact-proven | support with `wheel.cmake=false` + `wheel.packages`, **or** reject by deliberate template policy |
| Maturin | current native template incompatible | reject source-generating simple-stub scaffold; preserve bare mode |

## Backend-floor principle

Prefer stable explicit generated configuration over raising a backend floor when both produce the same correct artifact and the explicit config preserves UV's existing compatibility surface.

Raise a floor only when the needed capability is genuinely unavailable or unstable in older supported versions.

For this scaffold:

- PDM: no new floor.
- setuptools: no new floor.
- Flit: 4.x remains necessary for the stable clean path.

## Likely generation order

```text
1. determine whether UV is generating a normal source package or operating in bare/custom mode
2. on the normal generated-package path, infer the simple-stub scaffold from the project name
3. resolve the selected backend's adapter/policy
4. render backend config
5. generate src/foo-stubs/__init__.pyi
6. skip runtime script/native starter generation for the simple-stub path
```

For rejected source-generating combinations, validate before native prerequisite files are written.

## Test contract

For supported simple-stub adapters:

1. initialization succeeds;
2. `src/foo-stubs/__init__.pyi` exists;
3. UV does not substitute `src/foo_stubs/__init__.py`;
4. generated runtime `[project.scripts]` is absent;
5. backend-specific configuration is exact;
6. the resulting wheel contains `foo-stubs/__init__.pyi`;
7. no generated runtime console script appears.

For rejected source-generating templates:

1. initialization fails before misleading native starter files are written;
2. the diagnostic names the scaffold/template incompatibility rather than claiming the backend can never be used with a `-stubs` project;
3. `--bare` remains available.

Negative controls should prove ordinary non-`-stubs` templates are unchanged.

## Non-goals for this bug fix

Do not widen this work into:

- general namespace-stub scaffolding;
- partial-stub scaffolding;
- arbitrary distribution-name → import-package mapping;
- a claim that `*-stubs` distributions contain no runtime Python at all;
- a public `--stub-only` project type;
- dynamic build-backend capability detection;
- a general backend feature registry.

Those can be successor features if real demand appears.

## What `teamleaderleo/uv#54` still proves

The old `uv_build`-only candidate remains useful containment evidence: it proved the public candidate's third-party regressions were caused by changing shared source/script behavior without adapting backend templates.

It is not the preferred semantic direction because it changes `foo-stubs` back into an ordinary runtime scaffold whenever a third-party backend is selected.

If product implementation is authorized, use a fresh current-main candidate rather than mutating #54 into a different design.

## Remaining product decisions

Evidence is saturated for the current **simple generated stub scaffold**. The remaining decisions are policy:

1. **Scikit:** backend-adapter support or preserve the current extension-template family and reject?
2. **Flit:** conditional 4.x requirement or general template upgrade?
3. **Explicit `--app --package`:** should explicit app intent outrank the `-stubs` scaffold heuristic if that distinction is readily available?
4. **Diagnostics/testing depth:** exact rejection wording and how much third-party wheel execution belongs in UV CI versus template snapshots.

Everything else in the current eight-backend matrix is now evidence-backed enough to implement once policy is chosen.

## Publication boundary

This is an internal design record. It grants no authority for another canonical UV comment, review, reaction, pull request, email, or other maintainer contact. Third-party GitHub references written into controlled-repository interaction text must use `redirect.github.com`.
