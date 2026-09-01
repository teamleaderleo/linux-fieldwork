# UV stub-only backend research

Observed: `2026-08-08`  
State: `SOURCE-LEVEL PASS COMPLETE; EXECUTION/WHEEL MATRIX STILL REQUIRED`  
External mutation authorized by this record: `false`

This note records what the selected Python build backends actually say about a PEP 561 stub-only distribution before another product candidate is built.

The target project is:

```text
distribution: foo-stubs
source tree:  src/foo-stubs/__init__.pyi
runtime script: absent
```

The typing specification requires the installed stub package itself to use the `foopkg-stubs` naming scheme. A successful ordinary `foo_stubs/__init__.py` runtime package is therefore not the success criterion for this lane.

Primary specification: https://typing.python.org/en/latest/spec/distributing.html#stub-only-packages

## UV's current backend templates

Current UV `main` still generates these build requirements/configurations in `crates/uv/src/commands/project/init.rs`:

```text
Hatch          hatchling
Flit           flit_core>=3.2,<4
PDM            pdm-backend
Poetry         poetry-core>=2,<3
setuptools     setuptools>=61
Maturin        maturin>=1.0,<2.0
Scikit-build   scikit-build-core>=0.12 + pybind11>=3
```

Source snapshot inspected: `57c6ca2b740b27febdba4f0a61b85a8319f780eb`.

The important point is that “backend supports stubs today” and “the backend version range UV currently asks for supports stubs” are separate questions.

## Preliminary capability table

This is a source/docs classification, not yet the final execution result.

| Backend | Source-level classification | Extra change indicated | Confidence before execution |
|---|---|---|---|
| `uv_build` | direct stub-only support | none for the known case | high |
| Hatch | explicit configuration | select `src/foo-stubs` as wheel package | high |
| Poetry | explicit configuration | include `foo-stubs` from `src` | high |
| Flit | direct support in Flit 4+, **not in UV's current `<4` range** | bump backend requirement, then use stub layout | high |
| PDM | direct current support | probably none | high |
| setuptools | direct on modern releases, version floor caveat | either require a new enough setuptools or emit compatibility config | medium-high |
| Maturin | pure stub-only package unsupported | reject this backend/project combination | high |
| Scikit-build | packaging machinery can copy a stub tree, but UV's selected template is a compiled-extension project | policy decision after execution | medium |

## Hatch

Hatch's wheel `packages` option explicitly selects a package directory and strips the source prefix while retaining the final path component. The maintainer-suggested configuration matches the documented mechanism:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/foo-stubs"]
```

Hatch documentation states that this is equivalent to including `src/foo-stubs` while using `src` as the source prefix. That should place the selected tree in the wheel as `foo-stubs/...`, which is exactly the PEP 561 shape we need.

Primary docs:

- https://hatch.pypa.io/dev/config/build/#packages

**Working classification:** supported with explicit configuration.

**Execution still required:** resolve the actual hatchling version selected by UV's unpinned requirement, build the wheel, and verify `foo-stubs/__init__.pyi` in the archive.

## Poetry

Poetry Core has explicit PEP 561 stub-only package handling. Current source recognizes a package as stub-only when its package name ends in `-stubs` and its files are `.pyi`/`py.typed` rather than requiring `.py` modules.

Current source:

- https://redirect.github.com/python-poetry/poetry-core/blob/main/src/poetry/core/masonry/utils/package_include.py

This support is not new to Poetry Core 2. A 2022 test/fix already built a `pkg-stubs` wheel and asserted the hyphenated `.pyi` paths in the wheel:

- https://redirect.github.com/python-poetry/poetry-core/commit/a435116ed0928318d8d6cb91fc740373782f0695

For UV's `src/` layout, current Poetry Core's `Module` implementation only searches the explicit package under `src` automatically when it is deriving the package from a normalized project name. An explicit `packages` entry uses the supplied base/source directly. Since `foo-stubs` cannot be reached from the normalized `foo_stubs` auto-discovery path, the likely correct generated form is:

```toml
[tool.poetry]
packages = [{ include = "foo-stubs", from = "src" }]
```

Current module source:

- https://redirect.github.com/python-poetry/poetry-core/blob/main/src/poetry/core/masonry/utils/module.py

**Working classification:** supported with explicit configuration.

**Execution still required:** confirm the exact `from = "src"` form with `poetry-core>=2,<3` and inspect the wheel.

## Flit

The maintainer pointer to Flit PR 742 is important, but it exposes a version-boundary mismatch in UV.

Flit PR 742 changed Flit so that stub packages:

- do not require the ordinary package `__init__.py` path;
- preserve the `-stubs` package name rather than normalizing that suffix;
- can avoid normal runtime metadata discovery when metadata is static.

PR:

- https://redirect.github.com/pypa/flit/pull/742

That work was released in **Flit 4.0**. Flit's own release history lists “Making typing stubs packages with a `-stubs` suffix will now work” under version 4.0:

- https://flit.pypa.io/en/stable/history.html#version-4-0

Current UV still generates:

```toml
[build-system]
requires = ["flit_core>=3.2,<4"]
build-backend = "flit_core.buildapi"
```

So the current UV-generated Flit requirement excludes the release containing the cited stub support.

**Working classification:** direct support exists in Flit 4+, but **current UV's Flit template cannot rely on it**.

A likely stub-only policy would need to move the Flit requirement to a compatible 4.x range (for example `flit_core>=4,<5`, subject to the broader UV compatibility policy) in addition to generating the hyphenated `.pyi` tree.

**Execution still required:** compare the current `<4` template against a Flit 4 template and inspect both wheel outcomes. This is now a first-class discriminator rather than a small implementation detail.

## PDM backend

Current PDM Backend has explicit out-of-box stub-package discovery. Its `is_python_package()` logic accepts either an ordinary `__init__.py` package or a directory whose name ends in `-stubs` and contains `__init__.pyi`.

Current source:

- https://redirect.github.com/pdm-project/pdm-backend/blob/main/src/pdm/backend/utils.py

The feature was added in April 2025 as “out-of-box stubs package support,” including a fixture with:

```text
src/my_package-stubs/__init__.pyi
```

and no backend-specific package declaration:

- https://redirect.github.com/pdm-project/pdm-backend/commit/9a9884a41dbca8a3b2b03cb03f032ceac6a28333

PDM's wheel builder also removes the configured/detected `src` package-dir prefix when writing wheel paths.

Relevant source/docs:

- https://backend.pdm-project.org/build_config/#the-src-layout
- https://redirect.github.com/pdm-project/pdm-backend/blob/main/src/pdm/backend/wheel.py

**Working classification:** direct current support, likely no additional UV configuration beyond generating the real stub-only tree and omitting the runtime script.

**Version caveat:** UV specifies only `pdm-backend`, so the exact resolved version must be recorded by the execution lane. Older PDM Backend releases predate the out-of-box stub feature.

## setuptools

Modern setuptools has two pieces that line up well with the stub-only layout:

1. automatic `src`-layout discovery uses `PEP420PackageFinder`, whose package test accepts directories without `__init__.py` and does not reject a directory merely for containing a hyphen;
2. since setuptools 69.0.0, `.pyi` and `py.typed` are included as package data by default.

Primary source/docs:

- https://redirect.github.com/pypa/setuptools/blob/main/setuptools/discovery.py
- https://setuptools.pypa.io/en/stable/userguide/miscellaneous.html
- https://setuptools.pypa.io/en/stable/history.html#v69-0-0

Current UV, however, generates only:

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"
```

That lower bound predates default `.pyi` inclusion. A normal isolated build today will generally resolve a much newer setuptools, but the declared UV contract itself does not guarantee the feature.

**Working classification:** modern setuptools likely supports the stub tree directly, but UV must decide whether to raise its minimum to a version with default PEP 561 data inclusion or emit explicit package-data configuration that works with the existing floor.

**Execution still required:** build with (a) current/latest resolved setuptools and (b) the declared floor or a representative pre-69 version, then inspect the wheel. This should tell us whether the version floor is a real compatibility boundary or only a source-level concern.

## Maturin

Maturin is the cleanest unsupported case.

Its normal project model builds Rust binaries/extensions or mixed Rust/Python packages. The documented mixed layout expects a runtime Python package into which the native extension is placed.

Primary docs:

- https://www.maturin.rs/index.html
- https://www.maturin.rs/project_layout.html

More directly, Maturin issue 792 records the maintainers' explicit statement that Maturin did not support pure stub packages; the suggested solution was to publish the PEP 561 `*-stubs` distribution separately rather than make it a Maturin project:

- https://redirect.github.com/PyO3/maturin/issues/792

The current UV maintainer reply says the same thing for this case.

**Working classification:** unsupported for the `foo-stubs` project kind; UV should likely reject `foo-stubs + maturin` rather than generate a hybrid Rust project.

No workaround should be invented merely to make a matrix row green.

## Scikit-build-core

Scikit-build-core is subtler than Maturin.

Its wheel machinery can explicitly copy Python package directories:

```toml
[tool.scikit-build]
wheel.packages = ["src/foo-stubs"]
```

and it can disable CMake-driven wheel construction with `wheel.cmake = false`. The documented package-copy mechanism recursively copies the selected directory and strips the source prefix.

Primary docs:

- https://scikit-build-core.readthedocs.io/en/latest/configuration/index.html#customizing-the-built-wheel
- https://scikit-build-core.readthedocs.io/en/latest/reference/configs.html

So it is too strong to say “scikit-build-core cannot package a stub-only tree.” It appears capable of doing so as packaging machinery.

But UV's `--build-backend scikit` template is not a generic pure-Python scikit-build configuration. UV generates a CMake project, requires `pybind11>=3`, compiles `_core`, and installs that runtime extension into the Python package. Turning `foo-stubs` into a pure `.pyi` project would therefore change the meaning of the selected UV template substantially.

**Working classification:** technically configurable, but the correct UV product policy is unresolved. Candidate policies are:

1. reject `foo-stubs + scikit-build` because the selected UV template denotes a compiled-extension project;
2. define a special stub-only scikit-build template that disables CMake and copies the stub package;
3. another backend-specific contract justified by execution/source evidence.

Do not call this row supported or unsupported yet.

## Runtime scripts

Once a backend is classified as building a genuine stub-only distribution, generation of the ordinary application console script should stop for that backend too.

This is partly semantic rather than a direct PEP 561 MUST: a stub-only package is type information rather than runtime implementation, and the current generated script target refers to a normalized runtime module that does not exist in the correct `foo-stubs` tree.

So the useful implementation question is no longer “which backends suppress scripts?” It is:

```text
Is this project being generated as a genuine stub-only distribution?
  yes -> no runtime console script
  no  -> ordinary project rules
```

That suggests script suppression belongs to the stub-project decision, while backend-specific logic decides how (or whether) that stub project can be represented.

## Revised mental model

The earlier controlled PR #54 answered a narrower causal question: containing the `-stubs` special case to `uv_build` removes the observed third-party build regressions.

Keep that as a green control, but do not treat its non-UV behavior as the final semantics.

The current model should be:

```text
project name ends in -stubs
        |
        v
stub-only project semantics
  - src/foo-stubs/__init__.pyi
  - no runtime console script
        |
        v
backend policy
  - direct support
  - support with backend-specific config/version
  - incompatible -> reject
```

This keeps the project-kind decision separate from backend mechanics and avoids making `uv_build` part of the definition of a stub-only package.

## Next execution matrix

Source research is now specific enough to justify a focused runtime matrix. The next run should record the exact resolved backend version and inspect wheel contents for every row.

Required rows:

```text
Hatch
  current UV requirement + explicit packages config

Poetry
  current UV requirement + packages = [{ include = "foo-stubs", from = "src" }]

Flit
  current UV requirement (<4) control
  Flit 4 stub-capable candidate

PDM
  current UV requirement, no extra config first

setuptools
  latest/current resolver result
  lower-bound/pre-69 discriminator if practical

Maturin
  current UV template as incompatibility control; do not repair into a fake passing project

Scikit-build
  current UV compiled template control
  optional pure-copy capability probe kept separate from product-policy conclusion
```

For every supported candidate, the wheel must contain:

```text
foo-stubs/__init__.pyi
```

and must not contain an application console-script entry created by `uv init`.

## Decisions that can already be made

- Do **not** promote PR #54 as the final cross-backend design.
- Do **not** restore `foo_stubs/__init__.py` merely to keep non-UV rows green.
- Treat Flit's current `<4` requirement as an explicit research/design problem.
- Treat PDM as a likely direct-support row, not a mystery success.
- Treat Poetry as a deliberate stub-aware backend needing src-layout package configuration.
- Treat Maturin as an incompatibility/rejection candidate.
- Keep setuptools and Scikit-build open until the execution discriminators settle the version/policy questions.

## Publication boundary

This is internal source research. It does not authorize another UV comment, review, reaction, issue, pull request, email, or other external contact. If later summarized on a controlled-repository interaction surface, external GitHub references must remain `redirect.github.com` links.