# UV stub-only Scikit policy: backend capability versus template semantics

State: `DESIGN EVIDENCE — NO PRODUCT CHANGE`

Date: 2026-08-09

## TL;DR

Scikit-build-core itself can build a pure-Python stub-only wheel, but UV's current `--build-backend scikit` scaffold is intentionally an extension-module template.

That makes these two claims compatible:

1. **Backend capability:** scikit-build-core can package `src/foo-stubs/__init__.pyi` with explicit `wheel.packages` and `wheel.cmake = false`.
2. **Current UV policy:** rejecting `foo-stubs + --build-backend scikit` can still be the least-surprising behavior today, because changing that selector into a CMake-less pure-Python template only for `*-stubs` would change the template family selected by the same CLI value.

A future explicit distinction between pure-Python and extension Scikit templates could reopen that policy without changing the backend-capability result.

## UV's documented selector contract

UV's current CLI reference describes `--build-backend` as choosing a build backend, but the project-creation guide is more specific: it calls the choices different **build backend templates**.

The same guide has a dedicated “Projects with extension modules” section and presents:

- Maturin for Rust extension projects;
- scikit-build-core for C, C++, FORTRAN, and Cython extension projects.

Current UV source and tests match that documentation. The Scikit scaffold creates:

- `CMakeLists.txt`;
- `src/main.cpp`;
- a Python package wrapper;
- `_core.pyi` for the compiled extension;
- `pybind11>=3` in the build requirements;
- source cache keys covering C/C++ files and `CMakeLists.txt`.

Official UV docs:

- https://docs.astral.sh/uv/concepts/projects/init/
- https://docs.astral.sh/uv/reference/cli/

Current source/tests:

- https://redirect.github.com/astral-sh/uv/blob/dd0584d560a4693b5713a78be54304123ada3e77/crates/uv/src/commands/project/init.rs
- https://redirect.github.com/astral-sh/uv/blob/dd0584d560a4693b5713a78be54304123ada3e77/crates/uv/tests/project/init.rs

## Scikit-build-core's broader backend capability

Scikit-build-core's own documentation explicitly supports CMake-less wheel builds:

```toml
[tool.scikit-build]
wheel.cmake = false
```

Its changelog describes this as support for pure-Python packages. Its configuration documentation also says `wheel.packages` may explicitly name package directories and that the final path element is used as the wheel package name.

For the fixed stub fixture, the relevant backend-level form is therefore:

```toml
[tool.scikit-build]
wheel.cmake = false
wheel.packages = ["src/foo-stubs"]
```

Official scikit-build-core docs:

- https://scikit-build-core.readthedocs.io/en/stable/about/changelog.html
- https://scikit-build-core.readthedocs.io/en/stable/configuration/
- https://scikit-build-core.readthedocs.io/en/stable/reference/configs.html

This is why “Scikit-build-core does not support stub-only packages” would be incorrect.

## Policy options

### A. Reject under today's selector semantics

For `uv init --package foo-stubs --build-backend scikit`, return a clear diagnostic that UV's current Scikit template is an extension-module starter and is not offered for stub-only projects.

Advantages:

- preserves the documented/template meaning of the current selector;
- avoids silently dropping CMake, pybind11, generated C++, and the compiled-extension wrapper only because the distribution name ends in `-stubs`;
- keeps the stub-only change bounded to adapting templates that already represent pure-Python package shapes;
- leaves room for a separately named or explicitly selected pure-Python Scikit template later.

### B. Adapt Scikit to a pure-stub template automatically

For a `*-stubs` name, suppress the extension starter and generate:

```toml
[tool.scikit-build]
minimum-version = "build-system.requires"
wheel.cmake = false
wheel.packages = ["src/foo-stubs"]
```

Advantages:

- honors the literal request to use scikit-build-core as the backend;
- the backend is genuinely capable of the result;
- makes the supported-backend matrix broader.

Cost:

- `--build-backend scikit` no longer selects one coherent starter family; the same option means “pybind11/CMake extension project” for ordinary names and “pure Python, no CMake” for stub names.

## Current recommendation

Prefer **A: reject under today's selector semantics**, but phrase the reason as a UV template boundary rather than a backend limitation.

The reopen trigger is explicit: if UV decides `--build-backend` should mean only “which PEP 517 backend should own the project,” independent of starter family, or adds a separate pure-Python Scikit template choice, then the backend-capability evidence already shows how stub-only support can be generated.

This is a policy choice, not an artifact capability claim. The repaired #459 hosted matrix remains useful for proving the wheel behavior, but a successful explicit Scikit wheel would not by itself invalidate the rejection recommendation.

No product candidate was changed and no canonical upstream interaction was made.
