# UV stub-only backend research

Date: 2026-08-08

Issue: #459

## Contract and source pin

This research classifies the fixed PEP 561 stub-only target:

- distribution: `foo-stubs`
- source package: `src/foo-stubs/`
- required package file: `src/foo-stubs/__init__.pyi`
- runtime script: absent

The UV generator contract inspected here is current `astral-sh/uv` main at `507230998c9541d67814b57463ac00e454ff6991`, whose workspace version is 0.12.3. The latest released UV available as a build frontend is 0.11.29; it is only a PEP 517 driver for the execution carrier, while backend declarations come from the pinned 0.12.3 source.

External UV source: https://redirect.github.com/astral-sh/uv/blob/507230998c9541d67814b57463ac00e454ff6991/crates/uv/src/commands/project/init.rs

## Result

| Backend | Current UV declaration | Current top release on Python 3.13 | Stub-only classification | Plausible `uv init` behavior |
| --- | --- | --- | --- | --- |
| PDM | `pdm-backend` / `pdm.backend` | 2.4.9 | **Direct support**, beginning in 2.4.4 | Generate `src/foo-stubs/__init__.pyi`, omit the script, and use `pdm-backend>=2.4.4` so the scaffold guarantees the feature it relies on. |
| setuptools | `setuptools>=61` / `setuptools.build_meta` | 83.0.0 | **Direct support at >=69; current UV floor is too low** | Generate the real stub package and raise the stub-project build floor to `setuptools>=69`. An alternative is explicit package-data config for pre-69, but a version floor is the smaller modern template. |
| scikit-build-core | `scikit-build-core>=0.12`, `pybind11>=3` / `scikit_build_core.build` | 1.0.3 | **Supported with explicit config as a backend; current UV Scikit selector semantics are a mismatch** | Prefer rejecting `foo-stubs + scikit` under the existing selector. Supporting it would require a distinct pure-stub template: no extension/CMake starter, `wheel.cmake = false`, and `wheel.packages = ["src/foo-stubs"]`. |
| Maturin | `maturin>=1.0,<2.0` / `maturin` | 1.14.1 | **Unsupported for pure stub-only projects** | Reject the combination with a clear error. Maturin's intended project is Rust/PyO3; pure stub distributions should be packaged separately. |

## PDM

PDM added explicit out-of-box recognition for stub packages in commit `9a9884a4` on 2025-04-07. Its package detector accepts a directory whose basename ends in `-stubs` when that directory contains `__init__.pyi`. The same commit added a fixture with the ordinary `pdm-backend` PEP 517 declaration and a hyphenated `src/my_package-stubs/__init__.pyi` tree.

Source: https://redirect.github.com/pdm-project/pdm-backend/commit/9a9884a41dbca8a3b2b03cb03f032ceac6a28333

Current 2.4.9 source still has the same rule. Its generic collector recursively includes files under discovered package directories; the wheel collector removes the `src/` package-dir prefix while preserving the package directory basename, so `src/foo-stubs/__init__.pyi` maps to `foo-stubs/__init__.pyi`.

Sources:

- https://redirect.github.com/pdm-project/pdm-backend/blob/2.4.9/src/pdm/backend/utils.py
- https://redirect.github.com/pdm-project/pdm-backend/blob/2.4.9/src/pdm/backend/base.py
- https://redirect.github.com/pdm-project/pdm-backend/blob/2.4.9/src/pdm/backend/wheel.py

Minimal stub-specific config: none beyond the normal backend declaration. To make generated projects feature-safe across resolver choices, the build requirement should carry the support boundary:

```toml
[build-system]
requires = ["pdm-backend>=2.4.4"]
build-backend = "pdm.backend"
```

## setuptools

Setuptools already recognized PEP 561 `-stubs` package directories before 69. The important boundary is package-data inclusion. In 68.2.2, `build_py` only adds configured package-data patterns. In 69.0.0, `build_py` introduces implicit `*.pyi` and `py.typed` patterns.

Sources:

- 68.2.2 discovery: https://redirect.github.com/pypa/setuptools/blob/v68.2.2/setuptools/discovery.py
- 68.2.2 build_py: https://redirect.github.com/pypa/setuptools/blob/v68.2.2/setuptools/command/build_py.py
- 69.0.0 build_py: https://redirect.github.com/pypa/setuptools/blob/v69.0.0/setuptools/command/build_py.py

A local wheel probe with setuptools 82.0.1 and UV's plain `setuptools>=61` style project produced a wheel containing `foo-stubs/__init__.pyi`, confirming the modern direct path. The pre-69 source delta explains why UV's current `>=61` floor does not guarantee the same artifact: a pre-69 backend can discover the package yet omit its sole `.pyi` file unless package-data is configured.

Pre-69 repair if UV ever chooses configuration instead of a version floor:

```toml
[tool.setuptools.package-data]
"foo-stubs" = ["*.pyi"]
```

Recommended generated requirement for stub-only projects:

```toml
[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"
```

## scikit-build-core

Current scikit-build-core has two separate behaviors that matter here:

1. Automatic package discovery normalizes a distribution name by replacing `-` with `_`, then probes `src/<normalized-name>`, `python/<normalized-name>`, and `<normalized-name>`. It accepts either `__init__.py` or `__init__.pyi`, but `foo-stubs` therefore probes `foo_stubs` and misses the required PEP 561 path `src/foo-stubs`.
2. An explicit `wheel.packages` list is copied using the listed directory basename as the wheel package key. `wheel.packages = ["src/foo-stubs"]` therefore preserves `foo-stubs` in the wheel. Setting `wheel.cmake = false` skips the CMake configure/build path and produces a pure-Python wheel path.

Sources:

- package discovery: https://redirect.github.com/scikit-build/scikit-build-core/blob/ee120a892a2207647a9676c1a535fb794f089344/src/scikit_build_core/build/_editable.py
- package copy mapping: https://redirect.github.com/scikit-build/scikit-build-core/blob/ee120a892a2207647a9676c1a535fb794f089344/src/scikit_build_core/build/_pathutil.py
- wheel build flow: https://redirect.github.com/scikit-build/scikit-build-core/blob/ee120a892a2207647a9676c1a535fb794f089344/src/scikit_build_core/build/wheel.py

Minimal backend configuration for this exact pure stub target:

```toml
[tool.scikit-build]
minimum-version = "build-system.requires"
wheel.cmake = false
wheel.packages = ["src/foo-stubs"]
```

That establishes backend capability. UV's existing `--build-backend scikit` meaning is different: the initializer emits a CMake/pybind11 extension starter and declares `pybind11>=3`. The maintainer-facing product choice should preserve that meaning and reject stub-only + Scikit unless UV intentionally adds a separate pure-stub Scikit template.

## Maturin

Maturin maintainers have explicitly classified pure stub packages as outside Maturin's project model and recommended distributing the PEP 561 stub package separately.

Source: https://redirect.github.com/PyO3/maturin/issues/792

Current 1.14.1 source still resolves a Cargo manifest for project layout and errors when the expected `Cargo.toml` is absent. Its Python-first package detection is also built around a Python package accompanying the Rust project, rather than a pure `*-stubs/__init__.pyi` distribution.

Source: https://redirect.github.com/PyO3/maturin/blob/v1.14.1/src/project_layout.rs

UV's own maintainer discussion for the stub-only feature also says Maturin does not support stubs-only packages and is the wrong backend for that target:

https://redirect.github.com/astral-sh/uv/pull/19671#issuecomment-5217482196

Classification: unsupported; reject.

## Execution status

The old cross-backend matrix is intentionally excluded as success evidence because its third-party fixture used `src/foo-stubs/__init__.py`, not the required stub-only `__init__.pyi` artifact.

A dedicated runtime carrier for this exact fixture is on internal PR #460 and checks full wheel ZIP contents, including current setuptools plus 68.2.2/69.0.0 discriminators, Scikit explicit/auto/current-template variants, and the Maturin failure case. GitHub Actions run `31200726540` is still queued as of this write-up. A second execution-only carrier exists on `teamleaderleo/uv:research/459-stub-backend-runtime` and is configured to commit its own `research-459-results.txt` receipt when a hosted runner executes it.

Until one of those carriers emits a receipt, artifact-level execution is complete only for the local modern-setuptools probe. The classifications above are supported by the backend source paths that determine discovery/copy behavior; the queued carrier remains the final independent wheel-payload check before implementation work resumes.
