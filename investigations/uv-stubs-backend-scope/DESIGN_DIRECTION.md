# UV stub-only initialization: reconciled design direction

State: `PROPOSAL FOR INTERNAL DEBATE — NO PRODUCT CHANGE`  
Date: 2026-08-09  
Research inputs: Linux Fieldwork #458 and #459  
Independent challenge: Linux Fieldwork #476  
Controlled containment candidate: `teamleaderleo/uv#54`  
Canonical upstream bug: [astral-sh/uv#19663](https://redirect.github.com/astral-sh/uv/issues/19663)  
Current upstream candidate: [astral-sh/uv#19671](https://redirect.github.com/astral-sh/uv/pull/19671)  
Further upstream mutation authorized by this record: `false`

## Working conclusion

A PEP 561 distribution named `foo-stubs` should keep stub-only package semantics regardless of the selected Python build backend.

The common generated source contract is:

```text
src/foo-stubs/__init__.pyi
```

with no generated runtime `main()` and no `[project.scripts]` entry.

Backend selection should then answer a separate question: what stable backend configuration expresses that project, is a newer backend genuinely required, or is the selected UV backend template incompatible with that project kind?

This supersedes both of the earlier broad shortcuts:

1. applying the same hyphenated source path to every backend without adaptation; and
2. limiting stub-only semantics to `uv_build` and silently turning `foo-stubs` back into an ordinary runtime package for third-party backends.

## Architectural boundary

Do **not** model `StubOnly` as another value of UV's existing `InitProjectKind` without a strong reason.

Current `InitProjectKind` describes scaffold shape such as packaged application, flat application, library, and bare project. Stub-only is a different dimension: it describes package content semantics.

Current UV source already centralizes the relevant operations in a small set of functions:

- project/build-system rendering;
- backend prerequisite generation;
- package source generation;
- project-script generation.

The cleaner implementation is therefore an orthogonal content classification derived once from the project name and passed through those existing choke points.

Illustratively only:

```rust
enum PackageContent {
    Runtime,
    StubOnly,
}
```

The exact type is not important. The invariant is that `-stubs` recognition happens once rather than as scattered suffix checks in backend branches.

## Executed backend evidence

The fixed target throughout the research is:

```text
distribution: foo-stubs
source:       src/foo-stubs/__init__.pyi
runtime CLI:  absent
```

### Hatch

Executed with `hatchling==1.31.0`.

Default project-name discovery fails on normalized `foo_stubs`. This succeeds:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/foo-stubs"]
```

The wheel contains `foo-stubs/__init__.pyi` and no runtime console entry point.

Classification: **support with explicit config**.

### Poetry

Executed with `poetry-core==2.4.1`.

Default discovery fails, and `{ include = "foo-stubs" }` without a source root fails for the fixed `src/` fixture. This succeeds:

```toml
[tool.poetry]
packages = [{ include = "foo-stubs", from = "src" }]
```

The wheel contains `foo-stubs/__init__.pyi` and no runtime console entry point.

Classification: **support with explicit config**.

### Flit

UV currently generates:

```toml
[build-system]
requires = ["flit_core>=3.2,<4"]
build-backend = "flit_core.buildapi"
```

That resolved to `flit_core==3.12.0` in the executed fixture and failed looking for `foo_stubs`.

The same project with:

```toml
[build-system]
requires = ["flit_core>=4,<5"]
build-backend = "flit_core.buildapi"
```

resolved to `flit_core==4.0.2`, built directly, and shipped `foo-stubs/__init__.pyi`.

Flit 4 is therefore a **real capability boundary**, not merely a convenience floor. The remaining policy choice is whether UV should use Flit 4 only for stub-only scaffolds or update the general Flit template.

### PDM

Current PDM has automatic `*-stubs` discovery, but requiring that newer feature is unnecessary for generated projects.

A hosted lower-bound discriminator on Python 3.9.25 proved:

```toml
[tool.pdm.build]
includes = ["src/foo-stubs"]

[build-system]
requires = ["pdm-backend==2.1.4"]
build-backend = "pdm.backend"
```

produces a wheel containing `foo-stubs/__init__.pyi` with no console script. The unconfigured `pdm-backend==2.1.4` control built a metadata-only wheel without the stub.

Receipt: run `31282617646`, job `93166265545`, carrier head `f21b2f158fe47c06e5f81369be1f08fb727b982c`.

Classification: **support with explicit config; no new backend floor required**.

Recommended generated adapter:

```toml
[tool.pdm.build]
includes = ["src/foo-stubs"]
```

Keep UV's existing PDM build requirement unless a separate reason exists to change it.

### setuptools

Setuptools 69 added implicit `.pyi` package-data inclusion, but a version-floor increase is also unnecessary for generated projects.

A hosted lower-bound discriminator on Python 3.9.25 proved:

```toml
[tool.setuptools.package-data]
"*" = ["*.pyi"]

[build-system]
requires = ["setuptools==61.0.0"]
build-backend = "setuptools.build_meta"
```

produces a wheel containing `foo-stubs/__init__.pyi` with no console script. The unconfigured `setuptools==61.0.0` control built a wheel that omitted the stub.

The wildcard key is intentional: setuptools 61's pyproject schema rejects a package-specific `"foo-stubs"` key because it is not a normal Python module name, but explicitly permits `"*"`.

Receipt: run `31282617646`, job `93166265545`, carrier head `f21b2f158fe47c06e5f81369be1f08fb727b982c`.

Classification: **support with explicit config; preserve `setuptools>=61`**.

Recommended generated adapter:

```toml
[tool.setuptools.package-data]
"*" = ["*.pyi"]
```

### Scikit-build-core

Two separate facts must not be collapsed:

1. scikit-build-core itself can package an explicit Python tree without CMake, using `wheel.cmake = false` and `wheel.packages = ["src/foo-stubs"]`;
2. UV's current `--build-backend scikit` template is specifically an extension-module starter: current source/tests generate `CMakeLists.txt`, pybind11 requirements, C++ source, and `_core.pyi`.

So the policy question is **UV template semantics**, not raw backend capability.

Current recommendation: reject `foo-stubs + scikit` under the existing extension-template contract. Supporting it should be an intentional new pure-stub Scikit template, not a silent semantic switch inside the current extension starter.

The repaired broad #459 execution carrier is still the remaining artifact-level check for this row. Until that receipt completes, keep this conclusion labeled source/template-backed rather than whole-matrix artifact proof.

### Maturin

Maturin's project model is a Rust/PyO3 extension package, and the upstream Maturin guidance for pure PEP 561 stub packages is to distribute them separately.

Current recommendation: reject a pure `foo-stubs` project with the Maturin template during `uv init`, before Cargo/PyO3 starter files are written.

This is an incompatibility row, not something to force into a passing pure-stub fixture.

## Reconciled backend policy

| Backend | Stub-only classification | Proposed UV adapter |
|---|---|---|
| `uv_build` | direct support | common stub tree; no extra config |
| Hatch | explicit config | `packages = ["src/foo-stubs"]` |
| Poetry | explicit config | `{ include = "foo-stubs", from = "src" }` |
| Flit | direct support only in 4.x | Flit 4.x requirement; decide conditional vs general upgrade |
| PDM | explicit config works on older backend | `includes = ["src/foo-stubs"]`; preserve existing requirement |
| setuptools | explicit config works at current UV floor | `"*" = ["*.pyi"]`; preserve `setuptools>=61` |
| Scikit-build-core | backend capable, current UV template semantic mismatch | reject current template or deliberately add a pure-stub template |
| Maturin | incompatible with pure stub-only project | reject during init |

## Design principle for backend floors

Prefer stable explicit generated configuration over raising a backend floor **when both produce the same correct artifact and explicit config preserves UV's existing compatibility surface**.

Raise the floor when the capability itself is absent in older versions.

That distinction now separates the rows cleanly:

- PDM: explicit config avoids a new floor.
- setuptools: explicit config avoids a new floor.
- Flit: older generated major version actually lacks the stub-package capability, so a 4.x decision remains necessary.

## Generation order

A future product implementation should conceptually follow this order:

```text
1. derive package-content semantics once
2. resolve/validate (content semantics, backend template)
3. render backend build-system and stub-specific adapter config
4. generate common stub-only source files for supported rows
5. generate runtime scripts/native starter files only for runtime rows
```

Validation should happen before Maturin/Scikit prerequisite files are written when the chosen combination is rejected.

## Test contract for a future candidate

For every supported stub-only backend, assert all of the following:

1. initialization succeeds;
2. `src/foo-stubs/__init__.pyi` exists;
3. `src/foo_stubs/__init__.py` is not generated as a compatibility substitute;
4. `[project.scripts]` is absent;
5. the backend adapter/config is exact;
6. `uv build` succeeds;
7. the wheel contains `foo-stubs/__init__.pyi`;
8. the wheel contains no generated runtime console script.

For rejected template combinations:

1. initialization fails before misleading native starter files are written;
2. the diagnostic names the incompatible template/project combination;
3. the diagnostic suggests choosing a compatible Python packaging backend without promising identical configuration across alternatives.

Negative controls should cover ordinary non-`-stubs` packaged applications and libraries for every backend so the orthogonal content path cannot alter existing runtime scaffolds.

## What `teamleaderleo/uv#54` still proves

The controlled `uv_build`-only candidate remains valuable as a containment experiment. Its all-backend green matrix proved that the public candidate's regressions came from changing shared source/script behavior without backend adaptation.

It should not be extended in place as the likely final implementation because its third-party backend behavior deliberately changes `foo-stubs` back into an ordinary runtime package.

If implementation is authorized later, build a fresh candidate from current UV main using the reconciled backend matrix rather than mutating #54 into a different design.

## Remaining debate

The evidence has narrowed the useful debate to a few genuine policy choices:

1. **Representation:** what is the smallest orthogonal content-semantic value that avoids scattered suffix checks?
2. **Flit:** use 4.x only for stub-only projects, or update UV's general Flit template?
3. **Scikit:** reject under today's extension-template semantics, or intentionally define a second pure-stub Scikit template?
4. **Diagnostics:** exact wording and timing for incompatible template/project combinations.
5. **Integration-test depth:** which backend wheel inspections belong in UV tests versus generated-tree/config snapshots.

PDM and setuptools version floors are no longer open design questions for this fixture: executed lower-bound evidence shows explicit configuration can preserve the existing UV requirements.

## Publication boundary

This is an internal design record. It grants no authority for another canonical UV comment, review, reaction, pull request, email, or other maintainer contact. Any third-party GitHub references written into controlled-repository interaction text must use `redirect.github.com`.