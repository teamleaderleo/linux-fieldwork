# UV stubs-package backend boundary

State: `ACTIVE — PUBLIC CANDIDATE REJECTED AS OVER-BROAD; SCOPED CANDIDATE QUEUED`  
Canonical issues: `astral-sh/uv#19663`, `astral-sh/uv#20734`  
Active public candidate: `astral-sh/uv#19671`  
External contact authorized: `false`  
External contact made: `none`

## Problem

A project named `foo-stubs` has two competing generated-layout contracts:

- `uv_build` requires a PEP 561 stub-only layout at `src/foo-stubs/__init__.pyi` and no runtime console script;
- the other supported build backends currently expect uv's existing normalized import package at `src/foo_stubs/__init__.py`.

Applying one backend's layout globally fixes `uv_build` but breaks other backends.

## Exact public candidate

```text
canonical PR: astral-sh/uv#19671
base: 3d00ce70244d8b5660e8c02136568a9147dc97e8
head: 082af3c5eb95bbc0f0173ebc67965919c14e1a0a
source file: crates/uv/src/commands/project/init.rs
source blob: c4a07138bf1ae1f09ffc8fdc276679e53c01bb4c
```

The public candidate:

1. suppresses `[project.scripts]` whenever the project name ends in `-stubs`;
2. selects a hyphenated module directory whenever the name ends in `-stubs`;
3. writes `__init__.pyi` and returns early only when the backend is `uv_build`.

The third choice is backend-scoped. The first two are not.

## Completed baseline reproducer

Controlled fork PR `teamleaderleo/uv#23` reproduced the original mismatch:

```text
source: 79bbface771210df216b738e9bdc7df95e5a9e6b
run: 30759500353
job: 91527374992
conclusion: success
```

Observed:

- `uv init --package foo-stubs` generated `src/foo_stubs/__init__.py`;
- the project declared `foo-stubs = "foo_stubs:main"`;
- `uv build` exited 2 because `uv_build` expected `src/foo-stubs/__init__.pyi`.

That branch was closed without merge after evidence transfer.

## Completed eight-backend review

Controlled fork PR `teamleaderleo/uv#28` compared exact baseline and public-candidate source:

```text
carrier head: 091c61d9a12060350a6cc0e80af7d67473d9d27f
run: 30800503994
baseline source: 3d00ce70244d8b5660e8c02136568a9147dc97e8
public candidate: 082af3c5eb95bbc0f0173ebc67965919c14e1a0a
baseline job: 91643730813 — success
candidate job: 91643730741 — success
baseline artifact: 8853588265
baseline digest: sha256:d51fc9f3d74ce805a9e27982b36cbc4f8442bf1d75b86465b02932a4481d63be
candidate artifact: 8855188807
candidate digest: sha256:ce26ada1e43fca71735ce1f956038aa3b4fee3cd292bb49dc3553b4867119e63
```

Result:

| Backend | Baseline build | Public candidate build |
|---|---:|---:|
| uv_build | failure | success |
| Hatch | success | failure |
| Flit | success | failure |
| PDM | success | success |
| Poetry | success | failure |
| setuptools | success | success |
| Maturin | success | failure |
| Scikit-build | success | success |

The public candidate correctly fixes `uv_build`, but forces every backend to use `src/foo-stubs/__init__.py` or `.pyi` while removing the application script. Hatch, Flit, Poetry, and Maturin continue to resolve the underscore-normalized import package and fail.

Disposition for the public candidate as written: `DO NOT ROUTE`.

## Scoped controlled candidate

```text
controlled repository: teamleaderleo/uv
exact public-candidate base branch: fieldwork/19671-public-candidate-base
experiment branch: fieldwork/19671-uv-backend-scope
experiment head: b49c4c0e92cb05dc86ae87776c6103fcca457e6b
internal draft PR: teamleaderleo/uv#30
focused run: 30851211326 — queued at last check
ordinary fork CI: 30851211543 — pending at last check
```

The branch commits three carrier files and no product source beyond the exact public candidate base. The disposable one-file transformation:

- resolves `ProjectBuildBackend` before script generation;
- suppresses the runtime application script only for `uv_build` stub packages;
- chooses the hyphenated `.pyi` directory only for `uv_build`;
- preserves the existing underscore `.py` layout for every non-UV backend.

The workflow requires:

- exact public base/head and source blob;
- one-file product diff;
- rustfmt;
- affected compilation;
- existing native `init_package_stubs` and `init_package` controls;
- packaged application and library initialization across all eight backends;
- successful builds for all 16 generated projects.

Expected contract:

```text
uv_build application/library:
  src/foo-stubs/__init__.pyi
  no project script
  build success

non-UV application:
  src/foo_stubs/__init__.py
  project script retained
  build success

non-UV library:
  src/foo_stubs/__init__.py
  no project script
  build success
```

## Decision boundary

If run `30851211326` is green, retain the exact scoped patch and complete matrix. Before promoting a clean source branch, review whether preserving a runtime package for non-UV backends is an intentional compatibility fallback or whether each backend needs explicit stub-only configuration. Do not silently generalize `uv_build`'s directory contract.

If the run fails:

1. classify source transformation and rustfmt before product semantics;
2. distinguish application from library failures;
3. inspect the first backend-specific build failure;
4. repair only the owning layer.

## Publication boundary

No canonical UV issue comment, pull request, review, reaction, email, or maintainer contact is authorized or made.
