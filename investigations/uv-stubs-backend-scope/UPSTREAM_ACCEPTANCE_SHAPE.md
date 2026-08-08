# UV stub-only initialization: upstream acceptance shape

State: `INTERNAL REVIEW STRATEGY — NO UPSTREAM MUTATION`  
Date: 2026-08-09

External context:

- [uv issue 19663](https://redirect.github.com/astral-sh/uv/issues/19663)
- [uv PR 19671](https://redirect.github.com/astral-sh/uv/pull/19671)

## Thesis

The most reviewable fix is **not** a general backend compatibility framework.

It is a narrow `uv init` template rule:

> When the normalized distribution name is a PEP 561 `*-stubs` distribution, generate stub-only package content. Then use the already-selected build-backend template to render the small amount of backend-specific configuration needed for that content, or reject a template that cannot honestly represent it.

For every ordinary project name, existing initialization behavior remains unchanged.

This should be framed as a template correctness bug, not a new public compatibility subsystem.

## Why this looks upstream-plausible

The live PR discussion already contains two useful signals.

First, the initial maintainer review did not object to a stub-package special case as such. The review asked for a comment explaining the special case and explicitly noted that similar special-casing already exists in UV.

Second, after the cross-backend regression was reported, the maintainer response did not suggest limiting correct stub semantics to `uv_build`. It supplied backend-specific Hatch and Poetry configuration, pointed to Flit stub support, and identified Maturin as the wrong backend for a pure stub-only package.

That makes the likely review question:

> What is the smallest correct backend-aware template change?

rather than:

> Should UV ever know that `*-stubs` packages are special?

## Keep the implementation smaller than the design model

The internal design model uses an orthogonal "stub-only package content" concept because that is the clean way to reason about the behavior.

The upstream code does **not** necessarily need a new public or heavyweight enum to express it.

The existing PR already has a compact helper:

```rust
fn stubs_package_module_dir(package: &PackageName) -> Option<String> {
    package
        .as_dist_info_name()
        .strip_suffix("_stubs")
        .map(|stem| format!("{stem}-stubs"))
}
```

A revised patch can keep this style, or derive the result once near the start of packaged-project initialization and pass a small boolean/path value through the existing rendering functions.

Avoid creating a registry, compatibility database, trait hierarchy, or new user-facing project-kind flag for this bug.

## Smallest runtime behavior

Conceptually, the runtime path only needs four decisions.

### 1. Recognize the stub-only distribution

Use the normalized package identity, as the existing PR does, so equivalent normalized distribution spellings are handled consistently.

For ordinary package names, return immediately to existing behavior.

### 2. Suppress runtime application scaffolding

For a stub-only distribution:

- do not generate `[project.scripts]`;
- do not generate a runtime `main()` or `hello()` implementation;
- generate `src/foo-stubs/__init__.pyi`.

This is common package-content behavior, not backend policy.

### 3. Adapt the selected pure-Python backend in the existing backend match

The existing `pyproject_build_system(package, build_backend)` match is already the natural owner for backend template text.

The executed research supports these small stub-only branches:

| Backend | Stub-only template delta |
|---|---|
| `uv_build` | none beyond the common stub tree |
| Hatch | add `packages = ["src/foo-stubs"]` |
| Poetry | add `{ include = "foo-stubs", from = "src" }` |
| Flit | select a 4.x build requirement |
| PDM | add `includes = ["src/foo-stubs"]` |
| setuptools | add wildcard `"*" = ["*.pyi"]` package data |

PDM and setuptools do **not** need new general backend floors. Hosted lower-bound execution proved that their existing older template range can package the correct stub wheel with explicit generated configuration.

Flit is different: the current generated `<4` major actually lacks the relevant stub-package capability, so a Flit 4 decision is real rather than merely an automatic-discovery convenience.

### 4. Reject incompatible native templates before generating their starter files

For Maturin, pure stub-only is not the project kind the backend represents.

For Scikit-build-core, the backend itself can package a CMake-less Python tree, but UV's current `scikit` selection is specifically an extension-module starter that generates CMake, pybind11, C++ source, and `_core.pyi`.

The smallest current patch should therefore reject those combinations **before** backend prerequisite files are written.

If maintainers prefer a pure-stub Scikit template, that is a separable design choice and should not force the first fix to introduce a broader template mode system.

## Likely code footprint

A review-friendly implementation should mostly stay in the current `uv init` source and tests.

Expected production-code shape:

1. one small stub-package helper or derived value;
2. one conditional around `[project.scripts]`;
3. a stub branch in package-source generation;
4. small backend-specific TOML additions in the existing backend match;
5. one validation helper for rejected backend/template combinations.

That is a handful of branches on a path that only runs during `uv init`. There is no ongoing resolver/install/runtime cost for normal UV operations, and ordinary non-stub initialization should remain byte-for-byte equivalent in tests.

The code size may look larger than the behavior because generated-template snapshot tests are verbose. That is test surface, not architectural complexity.

## Test shape that matches UV's existing style

UV's existing backend initialization tests primarily assert generated project files and snapshots. Native Scikit tests explicitly avoid requiring a full C++ build in the normal test path.

For an upstream candidate, prefer:

- generated `pyproject.toml` snapshots for each affected backend;
- exact source-tree assertions for `src/foo-stubs/__init__.pyi`;
- absence of `[project.scripts]`;
- rejection snapshots for Maturin/Scikit if those remain rejected;
- existing ordinary package/library backend tests as negative controls;
- keep the existing `uv_build` end-to-end build assertion.

The Fieldwork hosted matrix remains useful external evidence that the generated third-party configurations produce the intended wheels, but UV does not necessarily need to turn every backend row into a networked/live-backend CI test.

## Explicit non-goals

Do not make the first patch responsible for:

- a general compatibility registry for all build backend features;
- dynamically detecting installed backend capabilities;
- adding a public `--stub-only` mode;
- redefining arbitrary `--build-backend` semantics;
- supporting pure-stub Scikit as a second Scikit template unless maintainers explicitly want it;
- changing any ordinary non-`*-stubs` scaffold;
- upgrading PDM or setuptools globally;
- refactoring unrelated `uv init` project-kind code.

## Main design choices maintainers still legitimately own

### Flit

Two reasonable policies remain:

1. use `flit_core>=4,<5` only for stub-only scaffolds; or
2. update UV's general Flit template to 4.x.

The stub bug only requires the first. The second is a broader maintenance decision and should not be smuggled into the fix unless desired.

### Scikit-build-core

Two reasonable policies remain:

1. reject `*-stubs + scikit` because today's UV selector means an extension-module starter; or
2. interpret selecting the backend as permission to generate a CMake-less pure-stub Scikit template.

The first is the smaller compatibility-preserving fix. The second is coherent but expands the semantic meaning of the selector and deserves explicit maintainer agreement.

## Acceptance risks

Nothing here guarantees merge.

The main risks are social/product-scope risks, not technical feasibility:

- PR 19671 is stale relative to current main and may need substantial rebasing;
- maintainers may prefer the original author to update the existing PR rather than accept a competing patch;
- they may prefer a smaller backend subset in the first fix;
- they may make a different Scikit or Flit policy choice;
- they may decide that some invalid backend combinations should fail later rather than at `uv init`.

Those are normal review decisions. None requires a large runtime mechanism.

## Recommended upstream framing, if and when authorized

Do not lead with the internal abstraction discussion.

Lead with the concrete correction to the earlier evidence:

1. the common `foo-stubs` source semantics are valid across several third-party backends;
2. Hatch/Poetry/PDM/setuptools only need small generated config;
3. Flit needs 4.x because support genuinely begins there;
4. Maturin is an incompatible template;
5. Scikit is a template-policy question, not a backend-capability failure;
6. ordinary projects are untouched.

Then ask maintainers whether they would prefer the existing PR to be updated with that backend-aware template behavior or whether a fresh current-main candidate would be useful.

That gives maintainers control over patch ownership and scope instead of presenting a large replacement implementation uninvited.

## Internal recommendation

Proceed toward a **minimal current-main prototype**, but keep it controlled/internal until:

- the independent #476 challenge reports or fails to find a material counterexample;
- the remaining #459 Scikit/Maturin execution receipt is either completed or explicitly classified as unnecessary for the chosen policy; and
- there is explicit authorization for any further canonical upstream interaction.

The prototype should optimize for a small diff and exact generated-template tests, not for maximal internal abstraction purity.
