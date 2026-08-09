# UV simple-stub initialization: upstream acceptance shape

State: `INTERNAL REVIEW STRATEGY — NO UPSTREAM MUTATION`

Date: 2026-08-09

External context:

- [uv issue 19663](https://redirect.github.com/astral-sh/uv/issues/19663)
- [uv PR 19671](https://redirect.github.com/astral-sh/uv/pull/19671)

Controlled current-main candidate: `teamleaderleo/uv#82`.

## Thesis

The most reviewable fix is a narrow `uv init` scaffold rule, not a general backend compatibility framework and not a global claim that every `*-stubs` distribution is permanently stub-only.

> When UV is generating its normal packaged/library source layout and the canonical project name maps to `*-stubs`, infer the common simple-stub scaffold. Adapt the selected backend with the small generated configuration needed for that tree, or reject the selected source-generating template when the focused product policy cannot honestly represent it.

Preserve `--bare` and custom layouts outside that inference. Ordinary project names stay unchanged.

## Why this is upstream-plausible

The live upstream discussion already accepts the basic special-case direction and identifies backend-specific consequences:

- Hatch needs explicit package selection;
- Poetry needs explicit package mapping;
- Flit has dedicated stub support;
- Maturin is the wrong generated template for a pure stub-only package.

The review problem is therefore scope and template policy, not whether UV may recognize the conventional generated scaffold.

## Narrow framing

Do not lead with “`*-stubs` is a new project kind.”

Use:

> UV maps the project name to a default generated package layout. For the conventional `foo-stubs` case, that default mapping should generate the simple PEP 561 stub package instead of a normalized runtime package.

This framing leaves namespace stubs, partial stubs, arbitrary distribution→import mappings, and richer mixed distributions outside the patch.

## Preserve custom surfaces

### `--bare`

Do not reject `foo-stubs --bare --build-backend scikit` or `maturin` merely because of the name.

Bare initialization intentionally skips UV-owned source layout. The user may provide a custom native, multi-package, partial-stub, or otherwise richer project.

### Do not invent an explicit-`--app` escape in this patch

The provenance experiment showed that retaining the raw flag is cheap, but the behavior is not a clean bug-fix safeguard:

- `--app` is documented as an explicit spelling of the default application target;
- a naive runtime `foo-stubs` override still conflicts with `uv_build`'s independent name-based stub inference;
- making it build correctly would add another `uv_build` `module-name` adapter;
- it would not provide a corresponding runtime-library escape.

If UV later needs a regular-package override for names ending in `-stubs`, that should be a separate explicit module/scaffold-control feature. Keep this patch focused.

## Keep implementation smaller than the design history

The selected implementation does not need:

- another `InitProjectKind` variant;
- a `PackageScaffold` enum;
- a capability registry;
- trait hierarchies;
- a public `--stub-only` flag;
- resolver/installer/lockfile changes.

An executed representation comparison showed the current local `simple_stub: bool` is better than a two-case scaffold enum. `BareWithBuildSystem` has no package scaffold, so `Runtime | SimpleStub` would mislabel that path unless another state/`Option` were introduced.

The boolean precisely answers the only required question: whether simple-stub template adaptation applies.

## Selected backend behavior

| Backend | Focused first-fix behavior |
|---|---|
| `uv_build` | direct generated stub tree |
| Hatch | `packages = ["src/foo-stubs"]` |
| Poetry | `{ include = "foo-stubs", from = "src" }` |
| Flit | conditional `flit_core>=4,<5` |
| PDM | `includes = ["src/foo-stubs"]`; preserve current requirement |
| setuptools | `"*" = ["*.pyi"]`; preserve `>=61` |
| Scikit-build-core | reject generated simple-stub scaffold; preserve `--bare` |
| Maturin | reject generated simple-stub scaffold; preserve `--bare` |

### Scikit qualification

Do not say scikit-build-core is incapable of packaging the stub tree.

Fieldwork proved that this works at UV's current backend floor:

```toml
[tool.scikit-build]
minimum-version = "build-system.requires"
wheel.cmake = false
wheel.packages = ["src/foo-stubs"]
```

Both support and reject product variants were materialized and passed the same focused tests. The selected first-fix policy is conservative rejection because current UV documentation presents Scikit as an extension-module starter and the rejection version preserves that template identity with a smaller semantic surface.

The CMake-less support candidate remains useful evidence if maintainers explicitly prefer backend identity over starter-family continuity.

### Maturin qualification

Reject only the generated simple-stub path. Artifact/source evidence says the pure fixture is outside Maturin's intended project kind, but `--bare` remains valid for custom projects.

## Likely production footprint

A review-friendly patch should remain recognizable as:

1. compute one local `simple_stub` predicate after final name/project-kind resolution;
2. validate selected rejected backends before filesystem/VCS initialization;
3. suppress generated runtime script metadata for the stub path;
4. render normal build-system declarations plus small explicit backend stub config;
5. write `src/foo-stubs/__init__.pyi` and return before runtime/native source generation.

Explicit backend helpers/match arms are preferable to a generic table because the required TOML changes are structurally different.

## Test shape

Prefer UV-native tests for the templates UV owns:

- exact generated `pyproject.toml` snippets/config;
- `src/foo-stubs/__init__.pyi` exists;
- normalized runtime `src/foo_stubs/__init__.py` is absent;
- `[project.scripts]` is absent on the simple-stub path;
- default `uv_build` project builds successfully;
- Scikit/Maturin selected rejection happens before project/VCS side effects;
- `--bare` controls succeed;
- ordinary packaged/native templates remain unchanged.

Fieldwork's hosted backend matrix is the artifact evidence for third-party backends. UV does not need a permanent networked matrix in its normal CI to make this fix reviewable.

## Current controlled candidate

`teamleaderleo/uv#82` is based on exact upstream-main commit:

```text
dd0584d560a4693b5713a78be54304123ada3e77
```

Its current diff is limited to:

- `crates/uv/src/commands/project/init.rs`;
- `crates/uv/tests/project/init.rs`.

It already uses the selected boolean representation and conservative Scikit/Maturin rejection policy.

The earlier temporary execution machinery is not part of the stable product diff.

## Acceptance risks

Nothing guarantees merge. Remaining risk is ordinary review/product preference:

- upstream PR #19671 is stale and may be preferred as the ownership vehicle;
- maintainers may choose the proven Scikit-support variant instead of conservative rejection;
- maintainers may prefer a different diagnostic or test split;
- they may choose to land only part of the backend adapter matrix initially.

None of these require a larger architecture.

## Recommended upstream framing, if authorized

Lead with the narrow, executed result:

1. the original hyphenated stub layout is correct in intent but incomplete across backend templates;
2. Hatch/Poetry/PDM/setuptools need only generated configuration;
3. Flit needs 4.x conditionally for the stable clean scaffold;
4. Scikit is technically capable, but the focused candidate conservatively preserves UV's current extension-template family and rejects generated stubs while keeping `--bare`;
5. Maturin rejects only the generated simple-stub path;
6. ordinary projects are unchanged;
7. the suffix is a default-scaffold heuristic, not a universal distribution ontology;
8. the implementation is one local predicate plus explicit existing backend/source branches, not a new framework.

Then ask whether maintainers prefer updating the existing PR or using a fresh current-main patch. Do not create unsolicited canonical competition without authorization.

## Internal next step

Architecture research is saturated. Continue with candidate-quality work on #82: exact diff review, diagnostics, source-branch hygiene, and focused test receipts. Reopen architecture only if upstream source materially changes or a concrete new compatibility case invalidates the selected boundary.

No canonical upstream interaction was made.
