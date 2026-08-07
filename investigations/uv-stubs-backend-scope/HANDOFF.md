# Handoff — UV stubs-package backend boundary

Handoff date: 2026-08-07  
State: `ACTIVE — BACKEND CAPABILITY RESEARCH SPLIT INTO TWO LANES`  
Further external mutation authorized by this handoff: `false`

## What is already established

### Original mismatch

```text
controlled PR: teamleaderleo/uv#23
source: 79bbface771210df216b738e9bdc7df95e5a9e6b
run: 30759500353
job: 91527374992
result: success
```

`uv init --package foo-stubs` generated an underscore runtime package and console script; `uv_build` rejected it because the backend expects a PEP 561 stub-only layout at `src/foo-stubs/__init__.pyi`.

### Exact public-candidate regression matrix

Public candidate: [uv PR 19671](https://redirect.github.com/astral-sh/uv/pull/19671) at `082af3c5eb95bbc0f0173ebc67965919c14e1a0a`.

```text
controlled PR: teamleaderleo/uv#28
run: 30800503994
baseline job: 91643730813
candidate job: 91643730741
```

Public-candidate result:

```text
uv_build       success
Hatch          failure
Flit           failure
PDM            success
Poetry         failure
setuptools     success
Maturin        failure
Scikit-build   success
```

This proves that the candidate's shared initialization change creates cross-backend regressions. It does not prove that the correct non-UV behavior is the old underscore runtime-package layout.

### UV-only containment control

Current clean controlled candidate:

```text
repository: teamleaderleo/uv
internal draft PR: #54
base: bab65d090d4f05d7dab432ac25304288ff1f2327
branch: candidate/19671-current-main-uv-backend-scope
head: 3e1fa232b6240e0d2617f399d3ca801c4760a30d
matrix run: 31013625610 — all 16 init/build rows passed
```

This candidate scopes the special layout/script behavior to `uv_build`. It is useful as a containment proof and regression control, but it is now **provisional rather than the preferred design**.

Do not promote or broaden #54 while the backend research below is incomplete.

## New maintainer information

The public Fieldwork comment is [comment 5210595906](https://redirect.github.com/astral-sh/uv/pull/19671#issuecomment-5210595906).

A maintainer replied at [comment 5217482196](https://redirect.github.com/astral-sh/uv/pull/19671#issuecomment-5217482196) with backend-specific information:

- Hatch can support the stub-only layout with explicit wheel package configuration;
- Poetry can support it with an explicit package declaration;
- Flit should support stub-only packages; current behavior should be verified against [Flit PR 742](https://redirect.github.com/pypa/flit/pull/742);
- Maturin does not support stub-only packages and is not the right backend for this project kind.

The working model is therefore no longer:

```text
uv_build -> stub-only
other backend -> ordinary underscore runtime package
```

Use this instead:

```text
foo-stubs
  -> supported directly
  -> supported with backend-specific config
  -> unsupported: reject the combination
```

A supported success case must produce the actual stub-only wheel payload, not merely exit zero.

## Worker lane A — pure-Python backends

Internal issue: Linux Fieldwork #458.

Research:

```text
Hatch
Poetry
Flit
```

For each backend establish:

1. exact version used by current UV initialization;
2. minimal `pyproject.toml` for `src/foo-stubs/__init__.pyi`;
3. PEP 517 / `uv build` result;
4. wheel payload containing `foo-stubs/__init__.pyi`;
5. absence of an inappropriate runtime script;
6. direct support vs explicit config vs unsupported;
7. source/docs explaining the result.

Specific starting controls:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/foo-stubs"]
```

and:

```toml
[tool.poetry]
packages = [{ include = "foo-stubs" }]
```

The Poetry lane must determine whether current configuration also needs an explicit `from = "src"`; do not assume either answer.

## Worker lane B — remaining and unsupported backends

Internal issue: Linux Fieldwork #459.

Research:

```text
PDM
setuptools
Scikit-build
Maturin
```

The earlier matrix's successful PDM/setuptools/Scikit-build rows are not sufficient evidence. Verify the actual wheel contents under a genuine hyphenated `.pyi` stub-only tree.

For Maturin, verify the current unsupported-project claim in source/docs and determine the appropriate UV behavior for `foo-stubs + maturin`. Prefer a clean incompatibility classification over inventing a workaround.

## Deliverable from both workers

Return a compact classification table:

| Backend | Direct stub-only | Extra config | Wheel correct | UV policy |
|---|---|---|---|---|

Include exact versions and the minimal relevant config snippets. Distinguish:

- `build succeeded`;
- `correct PEP 561 stub-only wheel produced`.

Those are not interchangeable.

Helpers should report into their internal issue first. Do not modify #54 product source and do not contact upstream.

## Coordinator next step

When #458 and #459 are complete:

1. reconcile the eight-backend capability table;
2. decide whether application script suppression is backend-independent for every real stub-only package;
3. decide which backends need generated tool-specific configuration;
4. decide which backend/name combinations should be rejected by `uv init`;
5. only then build a replacement controlled candidate and a focused matrix that checks wheel contents as well as build status.

Keep #54 as the known-green containment control during that work.

## Publication boundary

One human-posted upstream comment already exists. This handoff does not authorize another canonical UV comment, review, reaction, pull request, issue, email, or other external mutation. Use `redirect.github.com` for external GitHub references on controlled-repository interaction surfaces.