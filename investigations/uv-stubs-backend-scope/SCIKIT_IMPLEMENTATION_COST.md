# UV simple-stub Scikit policy: implementation-cost comparison

State: `SOURCE-LEVEL THUNDERDOME — NO PRODUCT CHANGE`

Date: 2026-08-09

Related internal work: #458, #459, #475, #476, `teamleaderleo/uv#54`.

Current UV source pin reviewed: `astral-sh/uv@dd0584d560a4693b5713a78be54304123ada3e77`.

External GitHub references in this record use redirect form.

## Question

The Scikit backend-capability question is already closed: explicit CMake-less configuration builds the exact simple `foo-stubs` wheel. The remaining choice is product policy:

1. **Scikit-S:** support the inferred simple-stub scaffold with a CMake-less Scikit template; or
2. **Scikit-R:** preserve UV's current Scikit extension-starter meaning and reject that source-generating combination.

This pass asks whether one option is materially more invasive or harder to maintain in current UV source.

## Current source ownership

Current UV keeps Scikit-specific generation in `crates/uv/src/commands/project/init.rs`.

The current source has three relevant ownership points:

- `pyproject_build_system(...)` emits Scikit's `[tool.scikit-build]`, cache keys, `scikit-build-core>=0.12`, and `pybind11>=3` requirement;
- `pyproject_build_backend_prerequisites(...)` emits `CMakeLists.txt` for Scikit;
- `generate_package_scripts(...)` emits `src/main.cpp`, `_core.pyi`, and the Python wrapper for Scikit.

Source:

- https://redirect.github.com/astral-sh/uv/blob/dd0584d560a4693b5713a78be54304123ada3e77/crates/uv/src/commands/project/init.rs

A repository code search for `ProjectBuildBackend::Scikit` finds the behavioral uses in this init source rather than a wider runtime/build subsystem.

That matters: a simple-stub Scikit branch does **not** need resolver, installer, lockfile, cache-database, or configuration-crate semantics.

## Current test ownership

`crates/uv/tests/project/init.rs` has dedicated Scikit app and library tests. They assert the current extension starter:

- `CMakeLists.txt`;
- `src/main.cpp`;
- `src/<module>/_core.pyi`;
- runtime `__init__.py` wrapper;
- `pybind11>=3`;
- C/C++/CMake cache keys.

Source:

- https://redirect.github.com/astral-sh/uv/blob/dd0584d560a4693b5713a78be54304123ada3e77/crates/uv/tests/project/init.rs

This is real evidence that today's ordinary Scikit template intentionally means an extension starter. It does not by itself require the same files for a separately inferred simple-stub scaffold.

## Lower-bound check: support already exists at UV's current Scikit floor

Earlier artifact execution used current scikit-build-core 1.0.3. This pass checked UV's actual lower bound, scikit-build-core 0.12.0.

In v0.12.0:

- `WheelSettings.cmake` exists and defaults to `true`;
- setting `wheel.cmake = false` makes the wheel target purelib unless overridden;
- `WheelSettings.packages` explicitly accepts a package-directory list;
- `_get_packages(...)` maps an explicit list item with `{Path(p).name: p}`.

Therefore:

```toml
[tool.scikit-build]
minimum-version = "build-system.requires"
wheel.cmake = false
wheel.packages = ["src/foo-stubs"]

[build-system]
requires = ["scikit-build-core>=0.12"]
build-backend = "scikit_build_core.build"
```

is supported by the capability already guaranteed by UV's current floor.

Sources:

- https://redirect.github.com/scikit-build/scikit-build-core/blob/v0.12.0/src/scikit_build_core/settings/skbuild_model.py
- https://redirect.github.com/scikit-build/scikit-build-core/blob/v0.12.0/src/scikit_build_core/build/wheel.py

No Scikit version-floor change is needed for the simple-stub adapter.

`pybind11` is also unnecessary on this CMake-less branch; it is part of UV's extension starter, not a requirement for scikit-build-core to copy the Python package tree.

## Incremental code cost after the common stub scaffold exists

The common fix already needs to distinguish normal runtime source generation from the inferred simple-stub source tree for every backend. It also already needs backend-specific stub TOML for Hatch, Poetry, PDM, setuptools, and Flit.

So the fair comparison is the **incremental** Scikit cost after that shared machinery exists.

### Scikit-S — support

Incremental production responsibilities:

1. in the existing Scikit build-system arm, render the CMake-less simple-stub form when the scaffold is `SimpleStub`;
2. do not emit the Scikit C/C++ cache keys or `pybind11` requirement for that branch;
3. skip Scikit `CMakeLists.txt` prerequisite generation on the simple-stub path;
4. the common simple-stub source branch already prevents `main.cpp`, `_core.pyi`, and the runtime wrapper from being written.

This is localized to existing init/template owners. No new error type or cross-crate policy is needed.

Test responsibilities:

- one generated-template case proving the Scikit stub TOML;
- assert `src/foo-stubs/__init__.pyi` exists;
- assert `CMakeLists.txt`, `src/main.cpp`, runtime `__init__.py`, `_core.pyi`, and generated console script are absent;
- ordinary Scikit app/library tests remain unchanged and continue proving extension-starter behavior for ordinary names.

### Scikit-R — reject

Incremental production responsibilities:

1. include Scikit alongside Maturin in simple-stub/backend compatibility validation;
2. emit a clear diagnostic explaining that UV's generated Scikit template is an extension starter and suggest another backend or `--bare` for custom configuration;
3. leave the existing Scikit template arms untouched.

Validation should run before `fs_err::create_dir_all(path)` / `init_vcs(...)` if the intended contract is that an unsupported combination fails without leaving a partially initialized directory or Git repository. Current `InitProjectKind::init` creates the directory and initializes VCS before its project-kind match, so rejection placement is part of the implementation review rather than only message text.

Test responsibilities:

- one rejection snapshot;
- assert no generated backend/source files (and, if chosen as the contract, no initialization side effects);
- preserve `--bare --build-backend scikit foo-stubs` as a successful custom-layout control.

## Code-size result

Scikit-R remains the smaller *template delta*: it adds a validation row instead of a second Scikit template.

But Scikit-S is smaller than the earlier design discussion made it sound:

- no backend upgrade;
- no new dependency or capability registry;
- no behavior outside project initialization;
- no hidden Scikit branches elsewhere in current UV;
- common stub source generation already removes most native-file work;
- the additional Scikit logic is one conditional backend-template form plus prerequisite suppression.

So "support would be too invasive" is **not supported by the current source pass**.

The real difference is policy:

- Scikit-S says backend identity is primary and UV may select a different starter within that backend when the inferred scaffold is a simple stub;
- Scikit-R says the CLI value `scikit` denotes UV's extension-starter family strongly enough to reject another valid scikit-build-core project form.

## Maintainability comparison

### Scikit-S risks

- future maintainers must remember that Scikit has two generated starter forms;
- ordinary Scikit tests and simple-stub Scikit tests must both remain explicit;
- documentation that presents Scikit only as an extension starter becomes less complete.

### Scikit-R risks

- compatibility validation and diagnostics become part of init behavior even though the selected backend can technically build the requested project;
- the policy is asymmetric with Hatch/Poetry/PDM/setuptools, where UV adapts backend configuration rather than rejecting the scaffold;
- an early-failure side-effect contract must be chosen and tested;
- users who specifically want scikit-build-core must fall back to `--bare` and configure a capability UV already knows how to express.

## Current verdict

The implementation-cost argument no longer decides the fight.

- **Smallest source change:** Scikit-R.
- **Most internally consistent with the backend-adapter model:** Scikit-S.
- **Capability-floor risk:** tie; neither needs a new Scikit floor.
- **Cross-cutting maintenance risk:** tie/low; both remain inside `uv init`.
- **Extra failure-path semantics:** Scikit-R has more.
- **Change to today's documented starter identity:** Scikit-S has more.

On source maintainability alone, the gap is small enough that **policy should decide, not fear of implementation size**.

If an internal current-main prototype is built later, the useful final discriminator is to materialize both Scikit-S and Scikit-R from the same common simple-stub base and compare exact production/test diffs. There is no reason to reopen backend-capability research before that.

## Adjacent explicit-app result

Current settings resolution still has the raw `app` boolean while processing `InitArgs`. It first resolves `(app, lib)`, then applies `--package`/`--no-package`; both the default packaged application and explicit `--app --package` ultimately become `InitProjectKind::ApplicationWithLibrary`.

Source:

- https://redirect.github.com/astral-sh/uv/blob/dd0584d560a4693b5713a78be54304123ada3e77/crates/uv/src/settings.rs

So explicit-app precedence is implementable, but provenance is currently discarded. Preserving it costs one small value across settings→init, not a new public project-kind hierarchy.

That keeps Variant D from `VARIANT_COMPARISON.md` plausible without widening the product model.

No UV product candidate was changed and no canonical upstream interaction was made.
