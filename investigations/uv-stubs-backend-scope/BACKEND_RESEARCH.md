# UV stub-only backend scope

Issue: #458

## Executed contract

The fixture is the exact stub-only layout requested by #458:

```text
src/foo-stubs/__init__.pyi
```

with distribution metadata `name = "foo-stubs"`. The positive fixtures omit `[project.scripts]`.

Execution receipt:

- Linux Fieldwork carrier: #461
- workflow run: `31199088142`
- job: `92934436459`
- carrier head: `dda14e26a73344e991fa8dbb5e511038af035ca1`
- runner: Ubuntu 24.04.4, `ubuntu-24.04` image `20260720.247.2`
- Python: 3.12.3
- uv: 0.12.3
- current uv source identity used for generated build-system constraints: `astral-sh/uv@507230998c9541d67814b57463ac00e454ff6991`

Current uv 0.12.3 generates these third-party build requirements:

- Hatch: `hatchling`
- Poetry: `poetry-core>=2,<3`
- Flit: `flit_core>=3.2,<4`

Source: [uv init backend generation](https://redirect.github.com/astral-sh/uv/blob/507230998c9541d67814b57463ac00e454ff6991/crates/uv/src/commands/project/init.rs).

## Result

| Backend | Exact executed backend | Minimal successful stub-only config beyond current uv build-system | Result | Classification |
|---|---:|---|---|---|
| Hatch | `hatchling==1.31.0` | `[tool.hatch.build.targets.wheel] packages = ["src/foo-stubs"]` | build succeeds; wheel ships `foo-stubs/__init__.pyi` | support with explicit config |
| Poetry | `poetry-core==2.4.1` | `[tool.poetry] packages = [{ include = "foo-stubs", from = "src" }]` | build succeeds; wheel ships `foo-stubs/__init__.pyi` | support with explicit config |
| Flit | current uv row: `flit_core==3.12.0`; 4.x control: `flit_core==4.0.2` | Flit 4 needs no backend-specific package config | uv's current `<4` row fails; Flit 4 succeeds and ships `foo-stubs/__init__.pyi` | current uv template unsupported; Flit 4 direct support |

PEP 561 defines separately distributed stub packages with the `foopkg-stubs` naming convention. The successful wheels below preserve that literal hyphenated package directory. See the [PEP 561 packaging specification](https://peps.python.org/pep-0561/#stub-only-packages).

## Hatch

### Current/default control

With only the current uv build-system declaration, Hatchling 1.31.0 fails. Its file-selection error says no directory matches the normalized project name `foo_stubs` and asks for an explicit wheel file-selection option.

### Minimal working config

```toml
[project]
name = "foo-stubs"
version = "0.1.0"
description = "stub-only fixture"
requires-python = ">=3.9"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/foo-stubs"]
```

Hatch documents `packages` as a wheel file-selection option that collapses a selected source package path to its final component in the wheel: <https://hatch.pypa.io/latest/plugins/builder/wheel/#packages>.

### Wheel evidence

`hatchling==1.31.0`, `uv build --wheel --no-build-isolation`: success.

```text
foo-stubs/__init__.pyi
foo_stubs-0.1.0.dist-info/METADATA
foo_stubs-0.1.0.dist-info/RECORD
foo_stubs-0.1.0.dist-info/WHEEL
```

`foo-stubs/__init__.pyi` is present. `entry_points.txt` is absent.

## Poetry

### Controls

With only the current uv build-system declaration, Poetry Core 2.4.1 fails with `No file/folder found for package foo-stubs`.

The maintainer-suggested declaration without a source root also fails for this `src/` fixture:

```toml
[tool.poetry]
packages = [{ include = "foo-stubs" }]
```

Poetry Core searches the project root and reports that `<project>/foo-stubs` contains no element.

### Minimal working config

```toml
[project]
name = "foo-stubs"
version = "0.1.0"
description = "stub-only fixture"
requires-python = ">=3.9"

[build-system]
requires = ["poetry-core>=2,<3"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
packages = [{ include = "foo-stubs", from = "src" }]
```

This matches Poetry Core's own PEP 561 `src/` fixture: [stub-only src fixture](https://redirect.github.com/python-poetry/poetry-core/blob/5de24118d23a05a23af5d9eb1d8bd98850d09205/tests/masonry/builders/fixtures/pep_561_stub_only_src/pyproject.toml). Its wheel test explicitly asserts the hyphenated stub package members: [Poetry Core wheel test](https://redirect.github.com/python-poetry/poetry-core/blob/5de24118d23a05a23af5d9eb1d8bd98850d09205/tests/masonry/builders/test_wheel.py).

### Wheel evidence

`poetry-core==2.4.1`, `uv build --wheel --no-build-isolation`: success.

```text
foo-stubs/__init__.pyi
foo_stubs-0.1.0.dist-info/METADATA
foo_stubs-0.1.0.dist-info/RECORD
foo_stubs-0.1.0.dist-info/WHEEL
```

`foo-stubs/__init__.pyi` is present. `entry_points.txt` is absent.

For this source layout, `from = "src"` is required.

## Flit

### Current uv row

The current uv declaration is:

```toml
[build-system]
requires = ["flit_core>=3.2,<4"]
build-backend = "flit_core.buildapi"
```

That resolves to `flit_core==3.12.0` in the executed environment. The build fails with `No file/folder found for module foo_stubs`.

### Flit 4 control

Using the same project metadata and the same exact `src/foo-stubs/__init__.pyi` tree, with only the major-version build requirement changed:

```toml
[build-system]
requires = ["flit_core>=4,<5"]
build-backend = "flit_core.buildapi"
```

resolves to `flit_core==4.0.2` and succeeds with no Flit-specific package configuration.

Flit PR 742 added the `-stubs` handling: [pypa/flit#742](https://redirect.github.com/pypa/flit/pull/742). Flit's 4.0 release history says typing stub packages with a `-stubs` suffix work in 4.0 and tells `[project]` users moving to 4.x to change the upper bound from `<4` to `<5`: [Flit release history](https://redirect.github.com/pypa/flit/blob/60c0b3d97bf095fbdb7671a02e51f8d8aba2fb85/doc/history.rst).

### Wheel evidence

`flit_core==4.0.2`, `uv build --wheel --no-build-isolation`: success.

```text
foo-stubs/__init__.pyi
foo_stubs-0.1.0.dist-info/METADATA
foo_stubs-0.1.0.dist-info/RECORD
foo_stubs-0.1.0.dist-info/WHEEL
```

`foo-stubs/__init__.pyi` is present. `entry_points.txt` is absent.

The version boundary is part of the Flit result: current uv's `<4` template cannot produce this stub-only package; Flit 4 can do so directly.

## Runtime scripts

A stub-only distribution carries typing interfaces and has no runtime implementation for a generated console script to call. The tested positive configurations therefore omit `[project.scripts]`; all three successful wheels contain no `.dist-info/entry_points.txt`.

## Product consequence

The executed result supports backend-specific generation for Hatch and Poetry:

- Hatch needs `packages = ["src/foo-stubs"]`.
- Poetry needs `packages = [{ include = "foo-stubs", from = "src" }]`.

Flit requires a separate backend-version decision because uv 0.12.3 pins the generated Flit backend below 4 while direct stub-only support begins in Flit 4. A Flit stub-only template therefore needs a 4.x build requirement, or the current `<4` combination should be rejected for this package form.

No controlled product candidate was changed. No canonical upstream interaction was made.
