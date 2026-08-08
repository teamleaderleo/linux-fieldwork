# UV simple-stub initialization: upstream acceptance shape

State: `INTERNAL REVIEW STRATEGY — NO UPSTREAM MUTATION`  
Date: 2026-08-09

External context:

- [uv issue 19663](https://redirect.github.com/astral-sh/uv/issues/19663)
- [uv PR 19671](https://redirect.github.com/astral-sh/uv/pull/19671)

## Thesis

The most reviewable fix is **not** a general backend compatibility framework and **not** a global claim that every `*-stubs` distribution is permanently stub-only.

It is a narrow `uv init` scaffold rule:

> When UV is generating its normal project→package source layout and the project name normalizes to `*-stubs`, infer the common simple-stub scaffold. Then adapt the already-selected backend template with small generated configuration, or reject a source-generating template that cannot honestly represent that scaffold.

Preserve `--bare` and custom-layout use cases outside that inference.

For ordinary project names, existing initialization behavior remains unchanged.

## Why this looks upstream-plausible

The live upstream discussion gives two positive signals.

First, the initial code review did not reject the stub special case. It asked for a comment explaining it and explicitly noted that UV already has similar special-casing.

Second, after the cross-backend regression was reported, maintainer feedback supplied backend-specific Hatch and Poetry configuration, pointed to Flit stub support, and identified Maturin as the wrong backend for a pure stub-only scaffold.

That means the likely review question is about **scope and template policy**, not whether UV is allowed to recognize the conventional scaffold at all.

## Important narrowing from adversarial review

Do not lead upstream with "`*-stubs` is a new project kind".

That phrasing is too broad because:

- PEP 561 permits richer layouts than a root `__init__.pyi` package;
- namespace and partial stub packages differ;
- project/distribution naming need not encode the entire import layout;
- real distributions such as `django-stubs` can ship the stubs plus runtime/plugin support code.

The safer framing is:

> UV currently maps the project name to a default source-package scaffold. For the conventional `foo-stubs` case, that default mapping should generate the simple PEP 561 stub package instead of a normalized runtime package.

This is a scaffold heuristic, not a permanent distribution-content invariant.

## Preserve expert/custom surfaces

### `--bare`

Do not reject `foo-stubs --bare --build-backend scikit` or `maturin` merely because of the name.

`--bare` intentionally skips the source files UV normally expects. A user may be supplying a custom multi-package, native, partial-stub, or otherwise richer layout.

Any Maturin/Scikit policy applies only when UV itself is generating the simple stub source scaffold.

### Explicit application intent

If current argument resolution can cheaply tell that the user explicitly requested `--app --package`, consider whether explicit app intent should outrank the name heuristic.

This should remain a small precedence question. Do not introduce a broad mode system just to answer it.

## Keep the implementation smaller than the design model

A revised upstream patch can stay close to the existing PR's helper style.

The existing PR already derives the conventional hyphenated stub directory from the normalized package name. A current-main implementation can keep one small helper/derived value and use it only along the source-generating packaged path.

Avoid:

- compatibility registries;
- backend feature databases;
- trait hierarchies;
- a public `--stub-only` flag;
- global changes to package-name semantics.

## Smallest production behavior

### 1. Infer the simple stub scaffold only when UV is generating source

For the conventional generated `foo-stubs` scaffold:

```text
src/foo-stubs/__init__.pyi
```

and no generated runtime entry point.

For ordinary names, use the existing path unchanged.

For bare/custom initialization, do not infer or reject from the name alone.

### 2. Adapt pure-Python backend templates in the existing backend match

Executed evidence supports these generated deltas:

| Backend | Simple-stub template delta |
|---|---|
| `uv_build` | none beyond the generated stub tree |
| Hatch | `packages = ["src/foo-stubs"]` |
| Poetry | `{ include = "foo-stubs", from = "src" }` |
| Flit | stable clean support requires 4.x |
| PDM | `includes = ["src/foo-stubs"]` |
| setuptools | wildcard `"*" = ["*.pyi"]` package data |

Do not raise PDM or setuptools floors just to gain automatic detection. Older supported backends produce the correct wheel with explicit generated configuration.

Flit remains different: the stable clean capability is genuinely a 4.x boundary for this exact scaffold.

### 3. Treat Scikit as an explicit product-policy fork

Artifact evidence is now complete:

- `wheel.cmake = false` + `wheel.packages = ["src/foo-stubs"]` builds the correct wheel;
- CMake-disabled auto discovery misses the stub;
- UV's current CMake-style contract fails on the pure stub fixture.

Therefore do **not** say "Scikit cannot support stub packages."

Two reviewable policies exist:

- **support it:** treat `--build-backend scikit` as backend selection and generate the CMake-less explicit adapter;
- **reject the generated simple-stub combination:** preserve UV's current interpretation of Scikit as an extension-module starter, while leaving `--bare` available for custom use.

If optimizing for semantic consistency with the other backend adapters, support is cleaner. If optimizing for preserving the current template family with the smallest behavior change, rejection is smaller. This is a maintainer decision, not an evidence gap.

### 4. Reject Maturin only on the source-generating simple-stub path

Maturin 1.14.1 artifact execution failed because the fixture has no Cargo project, matching maintainer/source guidance.

If UV is about to generate the simple `src/foo-stubs/__init__.pyi` scaffold, reject Maturin before writing Cargo/PyO3 starter files.

Do not block `--bare --build-backend maturin` based on the name alone.

## Likely code footprint

A review-friendly production patch should still be small:

1. one helper/derived "simple stub scaffold" value on the generated-package path;
2. one condition suppressing the generated runtime script;
3. one source-generation branch writing `__init__.pyi` under the hyphenated directory;
4. small backend-specific TOML branches in existing template rendering;
5. narrow validation for source-generating incompatible templates, if maintainers choose rejection rows.

No resolver, installer, lockfile, or runtime execution path needs to change. This logic runs during `uv init` only.

The test diff may be much larger than the production diff because generated-template snapshots are verbose.

## Test shape that matches UV ownership

Prefer testing the thing UV owns: generated templates.

Upstream tests should focus on:

- exact generated `pyproject.toml` per affected backend;
- exact `src/foo-stubs/__init__.pyi` path;
- absence of the generated runtime `[project.scripts]` entry;
- preservation of `--bare` behavior;
- rejection snapshots only for backend/template combinations maintainers choose to reject;
- ordinary non-stub package/library snapshots unchanged;
- keep the existing `uv_build` end-to-end build assertion.

Fieldwork's hosted backend matrix provides artifact evidence for the third-party templates. UV does not necessarily need networked/live third-party builds in its normal test suite.

## Explicit non-goals

Do not make this bug fix responsible for:

- all PEP 561 namespace-stub layouts;
- partial stub packages;
- arbitrary distribution→import-package mappings;
- proving a `*-stubs` distribution contains no runtime code;
- dynamic backend capability detection;
- a general backend feature registry;
- global PDM/setuptools upgrades;
- a public project-kind API.

## Main review choices that remain

### Flit

Use Flit 4 only for the inferred simple-stub scaffold, or upgrade the general Flit template. The bug fix only requires the conditional form.

### Scikit-build-core

Support with the proven CMake-less explicit adapter, or preserve the current extension-template family and reject only the source-generating simple-stub combination.

### Explicit `--app --package`

If explicit app provenance is available without architectural churn, decide whether it should outrank the project-name scaffold heuristic.

## Acceptance risks

Nothing guarantees merge.

The primary risks are normal product/review risks:

- the current public PR is stale and non-mergeable against current main;
- maintainers may prefer the existing author to update it rather than accept a competing implementation;
- maintainers may choose a different Scikit or Flit policy;
- they may intentionally support only a subset of backend adapters in the first patch;
- they may prefer build-time failure over init-time rejection for some advanced combinations.

Technically, though, this does **not** require a large compatibility switch or ongoing runtime subsystem.

## Recommended upstream framing, if authorized

Lead with the narrow result:

1. the original shared hyphenated layout was correct in intent but incomplete across backend templates;
2. Hatch/Poetry/PDM/setuptools need only generated configuration;
3. Flit needs 4.x for the stable clean scaffold;
4. Scikit is artifact-capable and now purely a template-policy choice;
5. Maturin is incompatible with the generated simple-stub scaffold, but bare/custom mode should remain available;
6. ordinary projects are untouched;
7. the inference applies to UV's default generated scaffold, not every possible `*-stubs` distribution.

Then ask whether maintainers prefer the existing PR to be updated or a fresh current-main candidate.

That avoids an unsolicited competing PR and gives maintainers control over patch ownership and the two remaining policy decisions.

## Internal next step

Evidence is saturated enough to build a minimal controlled current-main prototype once the desired Scikit policy is chosen.

Keep that prototype internal until there is explicit authorization for another canonical upstream interaction.
