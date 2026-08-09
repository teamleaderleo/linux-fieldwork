# UV simple-stub initialization: variant comparison

State: `INTERNAL DESIGN COMPARISON — NO PRODUCT CHANGE`

Date: 2026-08-09

Related internal work: #458, #459, #475, #476, `teamleaderleo/uv#54`.

External context:

- https://redirect.github.com/astral-sh/uv/issues/19663
- https://redirect.github.com/astral-sh/uv/pull/19671

No upstream mutation is authorized by this record.

## Question

Compare the surviving design variants against the same criteria instead of letting each research correction silently replace the previous one.

Criteria:

1. generated artifact correctness for the simple `foo-stubs` scaffold;
2. preservation of explicit user intent and existing non-stub behavior;
3. backend compatibility surface;
4. production-code complexity and long-term maintenance burden;
5. alignment with current UV CLI/template semantics;
6. amount of new policy hidden inside the bug fix.

## Variant A — upstream shared suffix special case

The current upstream PR applies the hyphenated stub directory and runtime-script suppression broadly from the package name.

### Strengths

- very small conceptual patch;
- fixes the reported `uv_build` mismatch directly;
- uses the correct simple stub path for the original reproducer.

### Losses

- exact-head testing showed the shared layout is not sufficient for third-party backend templates;
- Hatch, Poetry, Flit and Maturin need different handling;
- build success alone hid incorrect artifacts on some backends;
- it has no `--bare` qualification and no backend capability policy.

### Disposition

**Incomplete as a cross-backend `uv init` fix.** Keep as origin/provenance, not the current internal recommendation.

## Variant B — `uv_build`-only containment (`teamleaderleo/uv#54`)

Only `uv_build` receives the stub scaffold; third-party backends retain the old normalized runtime package.

### Strengths

- smallest regression containment;
- demonstrated an all-backend green init/build matrix;
- isolates the mechanism that caused the public candidate's cross-backend failures.

### Losses

- a user asking for `foo-stubs` gets a real stub distribution with one backend and an ordinary runtime package with another;
- later backend research proved Hatch, Poetry, PDM, setuptools, Flit 4 and Scikit can represent the requested simple stub scaffold;
- green build status is achieved partly by changing the meaning of the generated project.

### Disposition

**Best control, not best product semantics.** Preserve as a negative/containment comparator.

## Variant C — narrow simple-stub scaffold plus backend adapters (#475 after #476)

When UV is generating its normal package source tree and the project name maps to the conventional `*-stubs` form, infer a simple stub scaffold, then adapt the selected backend.

Common generated source:

```text
src/foo-stubs/__init__.pyi
```

with no generated runtime console script.

`--bare` remains outside the inference.

### Strengths

- artifact-correct across every backend that can represent the simple scaffold;
- keeps the suffix rule local to `uv init` generation rather than making it a permanent distribution ontology;
- backend deltas stay in existing backend-template owners;
- ordinary project names stay on current paths;
- PDM/setuptools preserve their existing backend requirements via explicit stable configuration;
- Maturin rejection is limited to the source-generating scaffold rather than custom/bare layouts.

### Costs

- several backend-specific TOML branches are required;
- Flit needs a conditional version requirement;
- Scikit still has a product-policy fork;
- a pure suffix heuristic can conflict with an explicitly requested packaged application.

### Disposition

**Current baseline winner.** Remaining work should refine precedence and the Scikit policy, not reopen the broad backend capability question.

## Variant D — provenance-aware simple-stub scaffold

Refine Variant C so explicit application intent outranks the project-name heuristic.

Suggested precedence for source-generating project initialization:

```text
bare/custom                      -> no scaffold inference
explicit --app                  -> runtime application scaffold
otherwise name maps to *-stubs  -> simple stub scaffold
otherwise                        -> existing runtime scaffold
```

### Source finding

Current UV still has the raw `app` boolean while resolving `InitArgs`. It first maps `(app, lib)` to an `InitProjectKind`, then applies `--package` overrides. Both default packaged applications and explicit `--app --package` ultimately become `InitProjectKind::ApplicationWithLibrary`.

So explicit-app provenance is **available cheaply at settings resolution but is discarded before project generation**.

Preserving the distinction would require carrying one additional piece of state past `InitSettings::resolve` (for example an `explicit_app` boolean or an equally small scaffold-intent value). Adding a dedicated project-kind variant solely for provenance would be a worse factoring.

### Strengths

- respects the CLI contract that explicit `--app` requests an application and packaged applications normally receive a console entry point;
- supplies a non-bare escape hatch for the legal-but-unusual case of an ordinary runtime distribution whose project name ends in `-stubs`;
- keeps default `uv init foo-stubs`, `--package foo-stubs`, `--lib foo-stubs`, and backend-implied packaging eligible for stub inference.

### Costs

- one extra internal provenance value must cross the settings→init boundary;
- this edge is not part of the original reported bug;
- the extra state is only justified if UV wants explicit CLI intent to outrank naming convention.

### Disposition

**Preferred refinement if implemented without widening the type model.** One provenance bit is a smaller compatibility cost than silently overriding explicit `--app` semantics.

## Scikit thunderdome

Artifact capability is no longer disputed. The exact simple scaffold builds correctly with:

```toml
[tool.scikit-build]
minimum-version = "build-system.requires"
wheel.cmake = false
wheel.packages = ["src/foo-stubs"]
```

The two surviving policies are therefore product choices.

### Scikit-S — support the simple stub scaffold

For inferred simple stubs, omit CMake, pybind11 and C++ starter files and generate the explicit CMake-less adapter.

**Pros**

- follows the same "scaffold semantics first, backend adapter second" rule as Hatch/Poetry/PDM/setuptools;
- honors the user's selected backend;
- artifact correctness is executed, not hypothetical.

**Cons**

- `--build-backend scikit` no longer always means UV's current extension-module starter family;
- requires conditional suppression of several existing Scikit prerequisites, not only one TOML key.

### Scikit-R — reject the source-generating simple stub combination

Keep Scikit's existing UV template meaning as a CMake/pybind11 extension starter. Tell the user to choose another backend for the generated simple stub scaffold. Keep `--bare --build-backend scikit` available.

**Pros**

- smaller production delta;
- preserves the current documented extension-template family;
- avoids making one backend selector select radically different starter files based on project name.

**Cons**

- rejects a backend combination that is technically valid and artifact-proven;
- gives Scikit different precedence from the other configurable backends;
- weakens the otherwise coherent adapter model.

### Current comparison

**Semantic winner: Scikit-S. Review-minimization winner: Scikit-R.**

This is the one remaining choice that evidence alone cannot settle. A future internal prototype comparison should measure the actual production/test diff rather than arguing only from prose.

## Flit thunderdome

### Flit-C — conditional 4.x for inferred simple stubs

Keep ordinary projects on the current requirement and use Flit 4 only where stub support is required.

### Flit-G — upgrade the general Flit template to 4.x

Move all new Flit projects to 4.x as part of this patch.

### Result

**Flit-C wins for this bug fix.** The general upgrade changes unrelated compatibility and build-Python floors. It can be considered independently later.

## Maturin result

No meaningful product variant remains for the generated simple stub scaffold:

- pure-stub capability is unsupported by the backend contract and artifact probe;
- generate a clear init-time rejection before Cargo/PyO3 starter files;
- preserve `--bare --build-backend maturin` so custom/mixed layouts remain possible.

## Current ranking

1. **Variant D: provenance-aware narrow simple-stub scaffold**, with conditional Flit 4 and explicit adapters.
2. **Variant C: narrow simple-stub scaffold without explicit-app provenance**, if maintainers prefer fewer internal state changes.
3. **Variant B: `uv_build`-only containment**, retained as a green regression control.
4. **Variant A: unadapted shared suffix special case**, incomplete across current backend templates.

Within Variant C/D, Scikit remains the only genuine unresolved policy fork.

## Implementation-maintenance guardrails

Whichever variant survives, reject any implementation that grows into:

- repeated suffix checks scattered through source generation and backend rendering;
- a runtime/backend capability registry;
- a permanent claim that a finished `*-stubs` distribution contains only stubs;
- global backend upgrades that are not required by the selected scaffold;
- special cases in resolver/installer/lockfile paths.

A maintainable patch should still be recognizable as:

```text
resolve existing project kind
retain explicit app provenance only if desired
infer simple stub scaffold on the generated-package path
render existing backend template with a small stub delta
write either the normal runtime source or the simple stub source
```

## Reopen triggers

Reopen this comparison only if:

1. a current-main source change alters argument provenance or backend-template ownership;
2. maintainers explicitly define whether `scikit` means backend identity or extension-starter family;
3. an implementation prototype shows Scikit-S is materially larger/riskier than the design model predicts;
4. a concrete `--app --package foo-stubs` compatibility case argues against explicit-intent precedence;
5. a backend deprecates one of the explicit configuration mechanisms used by Variant C/D.

Otherwise further PEP 561 ecosystem exploration is outside the current bug-fix decision.
