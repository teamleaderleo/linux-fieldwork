# UV stub-only design review saturation

State: `SATURATED FOR CURRENT SIMPLE-SCAFFOLD QUESTION — NO PRODUCT CHANGE`

Date: 2026-08-09

Related internal work: #458, #459, #475, #476.

External upstream contact authorized by this record: `false`.

## TL;DR

The independent challenge found enough real corrections to narrow the design without opening another unbounded research layer.

The surviving product question is smaller than the original proposal:

> In source-generating packaged modes, a project name ending in `-stubs` is UV's default signal to scaffold a simple complete stub package. UV should generate the simple `src/foo-stubs/__init__.pyi` starter, suppress its generated runtime console script, and adapt the selected backend with stable public configuration when possible. `--bare` remains outside that inference. Maturin is incompatible with the generated simple-stub starter. Scikit-build-core is technically capable with explicit CMake-less configuration, so rejecting Scikit is a product-template policy choice rather than a capability result.

Three earlier overstatements are now retired:

1. the distribution/project name suffix is not itself the normative PEP 561 package identity;
2. a "stub-only distribution" need not contain only stub files or only one import package;
3. the red status of the repaired broad #459 workflow does not mean the Scikit/Maturin rows failed to execute.

## New execution receipt closes the Scikit/Maturin artifact gap

The repaired broad matrix finally executed:

```text
carrier: teamleaderleo/linux-fieldwork#460
head: f21b2f158fe47c06e5f81369be1f08fb727b982c
workflow: Research 459 stub backend matrix
run: 31282617615
job: 93166265448
runner: Ubuntu 24.04.4
Python: 3.13.14
uv build frontend: 0.11.29
```

The workflow concluded `failure`, but the first unexpected failure owner is a stale fixture, not Scikit or Maturin.

The stale case still used:

```toml
[tool.setuptools.package-data]
"foo-stubs" = ["*.pyi"]
```

with `setuptools==68.2.2`. Setuptools rejects that package-data key because the schema accepts a Python module name or `*`. The later lower-bound run `31282617646` already repaired this with:

```toml
[tool.setuptools.package-data]
"*" = ["*.pyi"]
```

and proved the correct wheel on setuptools 61.0.0.

All later broad-matrix rows still ran, so their observations are valid artifact evidence despite the final red job.

### Artifact results

| Case | Build | Wheel payload result |
|---|---:|---|
| PDM current (`2.4.9`) | success | `foo-stubs/__init__.pyi` present; generated `entry_points.txt` contains empty `console_scripts`/`gui_scripts` sections, so no console command exists |
| setuptools current (`84.0.0`) | success | `foo-stubs/__init__.pyi` present; no console script |
| setuptools `68.2.2` default | success | metadata-only with respect to the stub; `foo-stubs/__init__.pyi` absent |
| setuptools `69.0.0` default | success | `foo-stubs/__init__.pyi` present; no console script |
| Scikit explicit | success | `foo-stubs/__init__.pyi` present; no console script |
| Scikit auto with CMake disabled | success | metadata-only with respect to the stub; `foo-stubs/__init__.pyi` absent |
| Scikit current UV-like CMake contract | failure | CMake configuration fails because the stub-only fixture has no `CMakeLists.txt` |
| Maturin build-system-only contract | failure | Maturin fails because the pure stub fixture has no `Cargo.toml` |

The Scikit explicit positive configuration is therefore artifact-proven:

```toml
[tool.scikit-build]
minimum-version = "build-system.requires"
wheel.cmake = false
wheel.packages = ["src/foo-stubs"]
```

This removes the last capability uncertainty from the Scikit policy debate. Scikit-build-core can represent the fixed simple stub scaffold correctly. The unresolved question is only what UV wants the `scikit` selector to mean.

The Maturin negative row is also now artifact-proven for the fixed pure-stub fixture and agrees with the maintainer/source contract already recorded in #459.

## The suffix is an inference, not the specification boundary

The current typing specification says the installed stub package name must use `foopkg-stubs`, while explicitly allowing the distribution/project name containing it to be different.

Source:

- https://typing.python.org/en/latest/spec/distributing.html#stub-only-packages

Python packaging also does not require a distribution name to match the import package(s) it installs.

Source:

- https://packaging.python.org/en/latest/discussions/distribution-package-vs-import-package/

So `project.name.ends_with("-stubs")` should be described as UV's default scaffold-intent inference under its normal project-to-package mapping. It should not become a universal property attached to every distribution object.

The `--bare` counterexample makes this concrete: UV explicitly allows `--bare` with `--build-backend` while skipping the expected file structure. Bare mode must remain available for custom layouts regardless of the distribution-name suffix.

UV docs:

- https://docs.astral.sh/uv/concepts/projects/init/#creating-a-minimal-project

## "Stub-only" should not mean "the whole distribution contains only stubs"

A second ecosystem counterexample narrows the internal representation.

`django-stubs` is a real stub distribution, but its current build configuration packages two top-level modules/packages:

```toml
[tool.uv.build-backend]
module-name = ["django-stubs", "mypy_django_plugin"]
module-root = ""
```

The project description also states that it ships Django type stubs together with a custom mypy plugin.

Source:

- https://redirect.github.com/typeddjango/django-stubs/blob/master/pyproject.toml
- https://pypi.org/project/django-stubs/

This does not make UV's minimal starter wrong. A fresh stub project can still start with only:

```text
src/foo-stubs/__init__.pyi
```

But it means a value literally described as `StubOnly` can be misleading if later code interprets it as an invariant that the complete distribution may never contain executable Python support code.

Prefer a representation whose scope is clearly scaffold generation, for example conceptually:

```text
PackageScaffold::Runtime
PackageScaffold::SimpleStub
```

or an equivalent boolean/value local to initialization. The name is illustrative; the important point is that this is a generation decision, not a permanent ontology for the finished distribution.

## Simple complete stub is one scaffold variant

The current typing specification also defines variants that the fixed fixture intentionally does not exercise:

- namespace stub packages omit root `__init__.pyi` files;
- partial stub packages contain `py.typed` with `partial`.

Source:

- https://typing.python.org/en/latest/spec/distributing.html#stub-only-packages
- https://typing.python.org/en/latest/spec/distributing.html#partial-stub-packages

So the current bug should be fixed around a **simple complete stub scaffold**, not by encoding `src/foo-stubs/__init__.pyi` as the only possible PEP 561 layout forever.

This is a future-proofing boundary, not a requirement to add namespace/partial-stub CLI options now.

## Backend conclusions after challenge

| Backend | Saturated conclusion for the simple generated scaffold |
|---|---|
| `uv_build` | direct support |
| Hatch | explicit package selection |
| Poetry | explicit package selection from `src` |
| Flit | stable clean support requires Flit 4; the Flit 3 hyphenated-module escape hatch was acknowledged upstream as accidental behavior |
| PDM | explicit `tool.pdm.build.includes` is sufficient without a new automatic-discovery floor |
| setuptools | explicit wildcard `.pyi` package data is sufficient at the existing `>=61` template floor |
| Scikit-build-core | artifact-proven support with explicit CMake-less configuration; rejection is only a UV template-policy choice |
| Maturin | artifact- and source-backed incompatibility for a pure generated stub scaffold; reject in source-generating mode, preserve bare custom-layout mode |

## Stop condition

The bounded #476 challenge is saturated for the current bug when the question is:

> What should `uv init` generate for the simple default `foo-stubs` scaffold across today's backend selectors?

Every decision branch now has either executed wheel evidence, a stable backend/source contract, or an explicit product-policy fork:

- Hatch / Poetry / PDM / setuptools: explicit adapter is known;
- Flit: capability floor is known;
- Scikit: capability is proven and only selector policy remains;
- Maturin: incompatibility is proven;
- `--bare`: compatibility exception is identified;
- distribution-name versus stub-package-name distinction is recorded;
- namespace/partial layouts are separated as successor questions.

Further searching for every possible PEP 561 ecosystem variation would no longer change this implementation decision. It would be a new feature-design investigation.

## Reopen triggers

Reopen this bounded review only if one of these happens:

1. current UV changes the meaning or generated files of a backend selector before implementation;
2. a backend changes or deprecates one of the explicit configuration mechanisms relied on here;
3. maintainers state that `scikit` must remain exclusively an extension-starter selector, resolving the current policy fork toward rejection;
4. UV wants to support namespace, partial, or explicitly named stub-package layouts in `uv init` rather than only the simple default scaffold;
5. a concrete compatibility case shows that the source-generating suffix inference itself produces the wrong default project.

Otherwise the next useful step is design selection and a fresh current-main product candidate, not another research layer.

No UV product candidate was changed and no canonical upstream interaction was made.
