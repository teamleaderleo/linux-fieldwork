# UV simple-stub initialization: reconciled design direction

State: `EVIDENCE-SATURATED INTERNAL DIRECTION — CONTROLLED PRODUCT CANDIDATE EXISTS`

Date: 2026-08-09

Research inputs: Linux Fieldwork #458, #459, #476 and follow-up prototype comparisons.

Controlled product candidate: `teamleaderleo/uv#82`.

Canonical upstream bug: [astral-sh/uv#19663](https://redirect.github.com/astral-sh/uv/issues/19663)

Current upstream candidate: [astral-sh/uv#19671](https://redirect.github.com/astral-sh/uv/pull/19671)

Further canonical upstream mutation authorized by this record: `false`

## Working conclusion

The bug should be fixed as a **narrow generated-scaffold rule**, not as a universal model of PEP 561 distributions.

When UV is generating its normal packaged/library source layout and the canonical project name maps to `*-stubs`, infer the common simple-stub scaffold:

```text
src/foo-stubs/__init__.pyi
```

Do not generate a runtime `main()` or `[project.scripts]` entry.

Then adapt the selected backend template with the smallest explicit configuration needed for that generated tree, or reject a source-generating backend/template combination when the selected product policy says UV cannot honestly generate that scaffold.

For ordinary project names, existing behavior stays unchanged.

## Scope boundary

The project-name suffix is a **UV scaffold heuristic**, not a permanent content invariant.

Do not claim that every `*-stubs` distribution:

- contains only `.pyi` files;
- uses a root `__init__.pyi` layout;
- has the same distribution and import-package name;
- lacks helper runtime/plugin code.

Namespace stubs, partial stubs, arbitrary distribution→import mappings, and richer mixed distributions are outside this bug fix.

### Preserve `--bare`

`--bare` deliberately leaves source layout to the user. A `foo-stubs` project must therefore remain allowed with `--bare --build-backend ...`, including Scikit and Maturin.

Backend rejection applies only to UV's **source-generating simple-stub scaffold**, not to the package name globally.

### Do not overload explicit `--app`

The explicit-app provenance experiment is resolved negatively for this bug fix.

Raw provenance is cheap to retain, but:

- UV documents applications as the default target and `--app` as an explicit spelling of that default;
- a naive runtime override for `foo-stubs` still conflicts with `uv_build`'s independent name-based stub inference;
- a complete runtime override would require another generated `uv_build` `module-name` rule;
- `--app` would not provide a coherent escape for runtime libraries named `*-stubs`.

Keep `--bare` as the existing custom-layout escape. If UV later wants a first-class suffix false-positive override, design an explicit module/scaffold control separately.

See `APP_PROVENANCE_EXPERIMENT.md`.

## Architecture

Keep `InitProjectKind` unchanged.

The current implementation should compute one local predicate after resolving the final project name:

```rust
let simple_stub = matches!(self, Self::ApplicationWithLibrary | Self::Library)
    && is_simple_stub_project(name);
```

Then use that value through existing project-init/template boundaries.

### Boolean wins over a new scaffold enum

An executed representation experiment converted the green implementation to:

```rust
enum PackageScaffold {
    Runtime,
    SimpleStub,
}
```

and passed compile/tests, but the rewrite added 39 lines / changed 22 existing lines and misrepresented `BareWithBuildSystem`: that path uses backend rendering while generating **no package scaffold**, so calling it `Runtime` is false.

An honest enum would require a third state or `Option<PackageScaffold>`, adding machinery the bug does not need.

Therefore keep the local `simple_stub: bool`. It means exactly “apply the simple-stub adaptation here” and naturally covers bare rendering with `false`.

See `SCAFFOLD_TYPE_EXPERIMENT.md`.

### Keep backend adapters explicit

Do not add a backend capability registry/table for this patch.

The backend deltas are structurally different:

- Hatch package selection;
- Poetry `packages` mapping;
- PDM `includes`;
- setuptools package data;
- Flit requirement floor;
- Scikit/Maturin selected rejection policy.

Explicit match arms/helpers keep the generated TOML visible and exhaustive. A generic table would mainly hide the same branching.

## Evidence-backed backend policy

Research target:

```text
project/distribution: foo-stubs
source:               src/foo-stubs/__init__.pyi
generated runtime CLI: absent
```

### `uv_build`

Direct support for the generated simple-stub tree.

### Hatch

Generate:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/foo-stubs"]
```

### Poetry

Generate:

```toml
[tool.poetry]
packages = [{ include = "foo-stubs", from = "src" }]
```

### PDM

Preserve UV's existing backend requirement and generate:

```toml
[tool.pdm.build]
includes = ["src/foo-stubs"]
```

Lower-bound hosted evidence proves this works without raising the PDM floor.

### setuptools

Preserve `setuptools>=61` and generate:

```toml
[tool.setuptools.package-data]
"*" = ["*.pyi"]
```

The wildcard is intentional for compatibility with older supported pyproject schema behavior.

### Flit

Use Flit 4.x **conditionally** for the simple-stub scaffold. Keep the ordinary Flit template on its existing requirement.

Stable clean `.pyi`-only package support begins in Flit 4; the older apparent workaround relied on accidental behavior and a runtime `__init__.py`.

Follow-up #483 confirmed the resulting build-host Python-floor policy is not a reason to globally upgrade or reject this conditional template.

### Scikit-build-core

Backend capability is proven: a CMake-less explicit package configuration produces the correct wheel at UV's current `scikit-build-core>=0.12` floor.

Both real internal policies were prototyped and passed the same focused gates:

- support via `wheel.cmake = false` + explicit `wheel.packages`;
- reject the source-generating simple-stub combination while preserving `--bare`.

The normalized internal thunderdome selected **conservative rejection for the first focused fix** because it preserves UV's documented Scikit extension-module starter family and reduces semantic/test surface. This must be described as a UV template-policy choice, **not backend incapability**.

The support variant remains proven fallback evidence if maintainers prefer backend identity to dominate starter-family continuity.

### Maturin

Reject the source-generating simple-stub scaffold before Cargo/PyO3 starter side effects. Preserve `--bare` for custom/mixed layouts.

Artifact and source evidence agree that the pure simple-stub fixture is outside Maturin's intended project kind.

## Selected matrix

| Backend | Selected first-fix behavior |
|---|---|
| `uv_build` | direct simple-stub scaffold |
| Hatch | explicit wheel package config |
| Poetry | explicit package mapping |
| Flit | conditional 4.x |
| PDM | explicit `includes`; preserve existing requirement |
| setuptools | wildcard `.pyi` package data; preserve `>=61` |
| Scikit-build-core | reject generated simple-stub scaffold; preserve `--bare` |
| Maturin | reject generated simple-stub scaffold; preserve `--bare` |

## Backend-floor principle

Prefer stable explicit generated configuration over a higher backend floor when it produces the correct artifact and preserves UV's compatibility surface.

Raise a floor only when the capability itself is genuinely absent or unstable on the current range.

For this bug:

- PDM: no new floor;
- setuptools: no new floor;
- Flit: conditional 4.x required for the simple-stub scaffold;
- Scikit: no new floor would be needed even for the proven support fallback.

## Selected generation order

```text
1. resolve existing InitProjectKind
2. resolve canonical final project name
3. resolve selected backend
4. compute simple_stub once on packaged/library source-generating paths
5. if simple_stub, validate selected backend before filesystem/VCS side effects
6. render project metadata
7. suppress runtime script metadata when simple_stub
8. render build-system plus explicit simple-stub backend config
9. generate src/foo-stubs/__init__.pyi, or existing runtime/native source
```

## Test contract

UV-native tests should focus on what UV owns:

- generated `pyproject.toml` config for each affected backend;
- exact `src/foo-stubs/__init__.pyi` path;
- absence of normalized runtime `src/foo_stubs/__init__.py` on the stub path;
- absence of `[project.scripts]` for the simple-stub scaffold;
- `uv_build` end-to-end build success;
- early rejection/no-side-effect checks for selected Scikit/Maturin policy;
- successful `--bare` controls;
- ordinary project/native-template tests unchanged.

Fieldwork's hosted matrix remains the artifact evidence for third-party backends; the production test suite does not need to become a permanent networked live-backend compatibility matrix.

## Controlled product candidate

`teamleaderleo/uv#82`, branch `fix/simple-stub-scaffold-current`, is based on exact upstream-main commit:

```text
dd0584d560a4693b5713a78be54304123ada3e77
```

The current candidate already uses the selected local boolean and explicit backend helpers/arms. The representation experiment therefore validates its factoring and calls for no product rewrite.

## Non-goals

Do not widen this patch into:

- namespace/partial stub scaffolding;
- arbitrary distribution→import mapping;
- a public `--stub-only` mode;
- a hidden `--app` suffix override;
- dynamic backend capability detection;
- a backend feature registry;
- a new `PackageScaffold` hierarchy solely for this two-way adaptation;
- resolver/installer/lockfile special cases.

## Remaining work

The broad design is no longer open-ended. Remaining work is candidate-quality work:

1. keep #82 synchronized with exact upstream source if upstream main moves materially;
2. tighten diagnostics/snapshots as needed;
3. verify source-branch hygiene and test receipts;
4. prepare a concise upstream-ready explanation only if explicit canonical interaction is authorized.

No canonical upstream interaction was made.
