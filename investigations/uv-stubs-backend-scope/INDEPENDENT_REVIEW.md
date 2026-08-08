# Independent review: UV stub-only backend capability model

State: `EXECUTED — REVISES DESIGN BOUNDARY`

Date: 2026-08-09

Primary design carrier: internal PR #475 (`investigations/uv-stubs-backend-scope/DESIGN_DIRECTION.md`)

Research inputs: #458, #459, #476.

External context only:

- https://redirect.github.com/astral-sh/uv/issues/19663
- https://redirect.github.com/astral-sh/uv/pull/19671

No upstream mutation is authorized by this review.

## TL;DR

The backend-capability model mostly survives, but two premises should be narrowed and one backend policy should be reopened.

1. A project/distribution name ending in `-stubs` is a strong **UV scaffold-intent signal**, but it is not itself a PEP 561 semantic guarantee. The current typing specification requires the installed stub package name to follow `foopkg-stubs`, while explicitly allowing the distribution/project name to differ.
2. Stub-only inference and backend rejection should apply only when UV is generating a packaged source tree. `--bare --build-backend ...` is an existing expert/custom-layout path and should not become invalid merely because the distribution name ends in `-stubs`.
3. Flit 4 remains the first stable path for the exact clean `src/foo-stubs/__init__.pyi` scaffold. Flit 3 had an accidental escape hatch via `[tool.flit.module] name = "foo-stubs"` plus `__init__.py`, but its maintainer explicitly called acceptance of the hyphenated module name a bug; it is not a stable generated contract.
4. PDM/setuptools explicit configuration remains the better compatibility choice. PDM's explicit `includes` collector exists in 2.0.0 source, so the mechanism predates the tested 2.1.4 row and does not depend on the later 2.4.4 automatic stub discovery.
5. The proposed Scikit rejection is not compelled by backend capability or by the orthogonal-content model. scikit-build-core officially supports CMake-less pure-Python wheels and explicit `wheel.packages`. If `-stubs` selects stub scaffold content first, generating that valid Scikit adapter is internally consistent. Rejection is defensible only as an explicit UV template-policy choice.
6. Maturin early rejection remains appropriate for a source-generating stub scaffold, but the same rejection should not be imposed on `--bare`.
7. `src/foo-stubs/__init__.pyi` is a good default simple stub fixture, not a universal PEP 561 invariant: namespace stub packages omit the root `__init__.pyi`, and partial stub packages need `py.typed` containing `partial`.

The smaller surviving model is therefore:

> In source-generating packaged modes, treat a `*-stubs` project name as UV's default request for a simple stub-only scaffold. Generate the common simple stub layout, adapt each selected backend with stable public configuration where possible, use a real capability floor where necessary, and reject only genuinely incompatible source-generating templates. Leave `--bare` as an expert/custom-layout escape hatch.

## Finding 1: project name suffix is not the normative PEP 561 identity

The current typing specification distinguishes **distribution/project name** from the installed **stub package name**.

It says the stub package name must use the `foopkg-stubs` form, but it also says the distribution containing that package may have a different name.

Source:

- https://typing.python.org/en/latest/spec/distributing.html#stub-only-packages

That weakens wording in #475 such as “a distribution whose project name is a PEP 561 `*-stubs` name”. The standard does not define the distribution name that way.

This does **not** make UV's suffix trigger unreasonable. `uv init` normally derives the generated module/package from the project name, and `uv_build` documents that stub modules use the `-stubs` form and `__init__.pyi`.

Source:

- https://docs.astral.sh/uv/concepts/build-backend/#stub-packages

So for a normal source-generating `uv init --package foo-stubs`, the suffix is a strong intent signal. The precise design claim should be “UV infers a stub scaffold from the default project-to-module mapping”, not “PEP 561 makes every distribution ending in `-stubs` semantically stub-only”.

### Counterexample class

Python distribution names and import package names need not match. It is therefore legal in principle for an ordinary runtime distribution named `foo-stubs` to install a differently named runtime package.

The current proposal would erase that possibility if suffix classification were global and unconditional.

The practical mitigation is small: scope the inference to UV's **generated default package layout**, where UV itself is choosing the package name from the project name.

## Finding 2: `--bare` is a concrete compatibility counterexample to global inference

Current UV has a distinct `BareWithBuildSystem` initialization kind described in source as:

```text
Initialize only a pyproject.toml with [build-system] table (but without associated source files).
```

In that branch, UV adds the selected build-system metadata but does not call backend prerequisite generation or package source generation.

Current source:

- https://redirect.github.com/astral-sh/uv/blob/dd0584d560a4693b5713a78be54304123ada3e77/crates/uv/src/commands/project/init.rs

The public docs also explicitly allow `--bare` with `--lib` or `--build-backend`; UV configures a build system while skipping the expected file structure.

Source:

- https://docs.astral.sh/uv/concepts/projects/init/#creating-a-minimal-project

Therefore a global validation step such as:

```text
if StubOnly && backend in {Maturin, Scikit}: reject
```

would be a compatibility regression for commands such as:

```text
uv init --bare --build-backend scikit foo-stubs
uv init --bare --build-backend maturin foo-stubs
```

Those commands currently mean “write minimal project/build metadata and let me own the layout”. UV has no generated CMake, Cargo, Python package, or runtime script to protect in that mode.

### Revised boundary

Classify/infer stub scaffold content only in packaged source-generating modes. Keep `Bare` and `BareWithBuildSystem` out of the source-layout semantic path.

This also gives advanced users an escape hatch when the project/distribution name happens to end in `-stubs` but they intentionally want a custom layout.

## Finding 3: Flit 3 had an escape hatch, but not a stable clean one

The earlier statement “Flit 3 has no configuration path” is too absolute.

Flit issue history records a working 3.x-style configuration:

```toml
[tool.flit.module]
name = "pkg-stubs"
```

with a `pkg-stubs` directory. However, Flit 3 still required `__init__.py` for a package, and maintainer Thomas Kluyver explicitly described acceptance of a hyphenated module name as a bug rather than an intended supported contract.

Source discussion:

- https://redirect.github.com/pypa/flit/issues/332#issuecomment-2309820707
- https://redirect.github.com/pypa/flit/issues/332#issuecomment-2309847553

Flit 3.12 source confirms that a package's canonical file is `__init__.py` and that metadata discovery reads that runtime file.

Source:

- https://redirect.github.com/pypa/flit/blob/3.12.0/flit_core/flit_core/common.py

PR 742 added the actual stub-package behavior: preserve the `-stubs` suffix, avoid unconditional runtime metadata extraction, and allow a stub package without `__init__.py`.

Source:

- https://redirect.github.com/pypa/flit/pull/742

### Review result

A Flit 3 workaround could produce a directory containing both an empty `__init__.py` and `__init__.pyi`, but it relies on behavior the maintainer called a bug and produces a less clean artifact than the fixed fixture.

That does not meet #476's “supported stable configuration” standard. Flit 4 remains a genuine capability floor for the exact generated stub-only tree.

## Finding 4: explicit backend config remains preferable for PDM/setuptools

The lower-bound execution on #460 already proves:

- PDM Backend 2.1.4 + `includes = ["src/foo-stubs"]` produces the correct wheel;
- setuptools 61.0.0 + wildcard `*.pyi` package data produces the correct wheel;
- their corresponding unconfigured controls omit the stub.

The PDM source boundary can be pushed earlier than the executed 2.1.4 probe. PDM Backend 2.0.0 already implements user `includes` by collecting exactly the configured paths recursively, and its wheel builder removes the `src/` package-dir prefix while preserving `foo-stubs/__init__.pyi`.

Sources:

- https://redirect.github.com/pdm-project/pdm-backend/blob/2.0.0/src/pdm/backend/base.py
- https://redirect.github.com/pdm-project/pdm-backend/blob/2.0.0/src/pdm/backend/wheel.py

That makes the explicit PDM adapter a longstanding backend contract, not a workaround tied to the modern automatic-discovery implementation.

For setuptools, the executed 61.0.0 wildcard package-data row is already the stronger evidence than source inference.

### Review result

Keep the revised principle, but state it as a conditional design rule rather than an absolute preference:

> Prefer explicit public backend configuration over a higher automatic-feature floor when the configuration is stable, produces the required artifact, and does not overconstrain the generated project's intended layout or compatibility.

PDM and setuptools satisfy that rule on the current evidence.

## Finding 5: Scikit rejection is the weakest row in #475

Official UV documentation uses both concepts:

- `--build-backend` selects a different **build backend template**;
- Scikit-build-core is presented in the extension-module section for C/C++/FORTRAN/Cython projects.

Source:

- https://docs.astral.sh/uv/concepts/projects/init/

That makes today's extension-starter interpretation real.

But scikit-build-core itself officially supports both pieces required for the fixed stub scaffold:

```toml
[tool.scikit-build]
wheel.cmake = false
wheel.packages = ["src/foo-stubs"]
```

Its configuration reference says `wheel.cmake` controls whether CMake runs and `wheel.packages` explicitly copies package directories into the wheel. With CMake disabled, purelib is the natural wheel target.

Sources:

- https://scikit-build-core.readthedocs.io/en/stable/reference/configs.html
- https://scikit-build-core.readthedocs.io/en/stable/configuration/

### Design contradiction

#475's top-level model says content semantics are orthogonal to backend identity: choose the stub project first, then let the selected backend express it.

Under that principle, Scikit has a valid public adapter. Rejecting it solely because the ordinary Scikit scaffold contains CMake/pybind11 makes the existing runtime starter more authoritative than the newly introduced content classification.

That is the opposite precedence from Hatch, Poetry, PDM, and setuptools, where the stub content changes backend-specific generated configuration.

### Review recommendation

Reopen the Scikit row. The internally consistent default is:

- source-generating `foo-stubs + scikit`: generate the pure-stub Scikit adapter (`wheel.cmake = false`, explicit `wheel.packages`), omit CMake/pybind11/C++ starter files;
- `--bare + scikit`: preserve today's minimal build-system behavior and let the user configure the layout;
- if UV maintainers explicitly want `scikit` to mean “extension starter family” rather than merely “scikit-build-core owns the build”, then early rejection is a product-policy choice, not a capability consequence.

The queued #459 artifact matrix can prove the explicit wheel payload, but it cannot by itself decide this policy question.

## Finding 6: Maturin rejection survives, with the same bare-mode qualification

Maturin's documented project layouts are Rust or mixed Rust/Python projects and require a Cargo project. Its typing support describes stubs for the Rust module or mixed package, not a pure separately distributed stub-only project.

Source:

- https://www.maturin.rs/project_layout.html

Maintainer guidance already recorded in #459 also says pure stub-only packages are not the right Maturin project kind.

Source:

- https://redirect.github.com/PyO3/maturin/issues/792

For a normal source-generating `uv init --package foo-stubs --build-backend maturin`, an early diagnostic is therefore better than writing Cargo/PyO3 starter files that contradict the inferred scaffold intent.

But `--bare --build-backend maturin foo-stubs` should remain available for the same reason as the Scikit bare case: bare mode is explicitly the custom-layout surface, and the distribution name alone is not a normative stub-package identity.

## Finding 7: the common tree is a default fixture, not the entire PEP 561 model

The current typing specification has two important variants:

- namespace stub packages omit the root `__init__.pyi`;
- partial stub packages include `py.typed` containing `partial` so type checkers merge missing modules from the runtime package or typeshed.

Source:

- https://typing.python.org/en/latest/spec/distributing.html#stub-only-packages

Therefore this exact tree:

```text
src/foo-stubs/__init__.pyi
```

should be described as UV's **simple complete stub scaffold**, not a universal invariant for every stub-only package.

That distinction avoids hard-coding a future design dead end if UV later supports namespace or partial stub scaffolds.

It does not invalidate the #458/#459 fixture; that fixture remains the right small discriminator for the current bug.

## Smallest implementation model after challenge

The current source already centralizes backend metadata, prerequisites, and source generation, so the architecture finding in `SOURCE_ARCHITECTURE.md` remains good.

The review recommends an even narrower scope for the semantic value:

```text
resolve existing InitProjectKind
resolve backend
if source-generating packaged mode:
    infer StubScaffold from the default project->module mapping
    validate/adapt backend
    generate simple stub or runtime source
else:
    preserve bare behavior
```

The internal representation can stay tiny: a boolean or two-state content/layout value is enough. It should not be described as a universal property of the distribution object.

Validation should happen before backend prerequisite/source files are written, but only on paths where UV is actually generating those files.

## Backend disposition after independent challenge

| Backend | Review disposition |
|---|---|
| `uv_build` | direct simple-stub support |
| Hatch | explicit config survives |
| Poetry | explicit config survives |
| Flit | 4.x capability floor survives; 3.x escape hatch is accidental/unclean |
| PDM | explicit config survives; source support is present by 2.0.0 |
| setuptools | explicit config at `>=61` survives |
| Scikit-build-core | **reopen rejection; backend support with explicit CMake-less config is the more internally consistent default unless UV explicitly chooses extension-template semantics** |
| Maturin | reject in source-generating stub scaffold; preserve bare custom-layout path |

## Remaining evidence boundary

The repaired broad #459 workflow run `31282617615` is still queued. Do not describe Scikit/Maturin artifact execution as complete until that receipt runs.

This review changes design reasoning from source/specification evidence; it does not pretend that queued execution has happened.

## Decision for #475

Do not implement the current draft wording unchanged.

Revise it so that:

1. `-stubs` is a UV scaffold-intent inference under its default project-to-package mapping, not a universal distribution-name semantic claim;
2. stub inference/rejection is scoped to source-generating packaged modes, leaving `--bare` unchanged;
3. the common `__init__.pyi` tree is explicitly the simple/default stub scaffold;
4. Flit 4 remains a real floor;
5. PDM/setuptools keep their existing backend requirements with explicit config;
6. Scikit is reopened as supported-with-explicit-config unless maintainers deliberately choose the extension-template policy;
7. Maturin is rejected early only for the source-generating inferred stub scaffold.

No UV product candidate was changed and no canonical upstream interaction was made.
