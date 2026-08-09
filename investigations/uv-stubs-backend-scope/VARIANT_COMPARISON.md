# UV simple-stub initialization: variant comparison

State: `INTERNAL DESIGN COMPARISON — NO PRODUCT CHANGE`

Date: 2026-08-09

Related internal work: #458, #459, #475, #476, `teamleaderleo/uv#54`, `teamleaderleo/uv#81`, `teamleaderleo/uv#84`.

External context:

- https://redirect.github.com/astral-sh/uv/issues/19663
- https://redirect.github.com/astral-sh/uv/pull/19671

No upstream mutation is authorized by this record.

## Question

Compare the surviving design variants against the same criteria instead of letting each research correction silently replace the previous one.

Criteria:

1. generated artifact correctness for the simple `foo-stubs` scaffold;
2. preservation of existing CLI behavior;
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

## Variant C — narrow simple-stub scaffold plus backend adapters

When UV is generating its normal package source tree and the project name maps to the conventional `*-stubs` form, infer a simple stub scaffold, then adapt the selected backend.

Common generated source:

```text
src/foo-stubs/__init__.pyi
```

with no generated runtime console script. `--bare` remains outside the inference.

### Strengths

- artifact-correct across every backend that can represent the simple scaffold;
- keeps the suffix rule local to `uv init` generation rather than making it a permanent distribution ontology;
- backend deltas stay in existing backend-template owners;
- ordinary project names stay on current paths;
- PDM/setuptools preserve their existing backend requirements via explicit stable configuration;
- Flit 4 is conditional only where the capability is required;
- Maturin rejection is limited to the source-generating scaffold rather than custom/bare layouts;
- matches the concrete upstream use cases, which are asking for actual typing-stub distributions.

### Costs

- several small backend-specific TOML branches are required;
- Scikit remains a product-policy fork: support its valid CMake-less form or preserve UV's current extension-starter identity and reject;
- project-name suffix remains a scaffold convention rather than a universal PEP 561 distribution identity.

### Disposition

**Current winner for this bug fix.** The broad backend-capability question and the explicit-`--app` precedence question are closed; Scikit policy and exact review/test shape remain.

## Variant D — explicit-`--app` provenance override

This variant refined C so explicit `--app` would force a runtime packaged application even when the project name maps to `*-stubs`:

```text
bare/custom                      -> no scaffold inference
explicit --app                  -> runtime application scaffold
otherwise name maps to *-stubs  -> simple stub scaffold
otherwise                        -> existing runtime scaffold
```

### What the experiment proved

Raw provenance is cheap to retain. Internal UV carrier #84 ran two factorizations from the green Scikit-support base:

- local capture in `run_project`: 12 production additions, 1 deletion;
- `explicit_app` on `InitSettings`: 10 production additions, 1 deletion.

Both passed the original init-focused gates. The `InitSettings` form is marginally smaller, but that mechanical result does not justify the behavior.

### Why the variant lost

1. **`--app` is currently default-equivalent.** UV documents applications as the default target and says they can also be specified with `--app`. Giving the explicit spelling a new suffix-override meaning introduces a distinction where current UV intentionally has none.

2. **The naive runtime override is not artifact-correct with `uv_build`.** `uv_build` independently infers stub-package semantics from the project name. Generating `src/foo_stubs/__init__.py` for `--app foo-stubs` still makes the default backend expect `src/foo-stubs/__init__.pyi` at build time.

3. **A complete runtime override needs another `uv_build` adapter.** It could emit:

   ```toml
   [tool.uv.build-backend]
   module-name = "foo_stubs"
   ```

   but that turns the supposed one-bit compatibility escape into another backend-specific product rule.

4. **`--app` is not a general false-positive escape.** It would help runtime applications named `*-stubs` while a runtime library with the same unusual distribution name would still be inferred as a stub scaffold under `--lib`.

5. **`--bare` already supplies the expert/custom-layout escape** for unusual distribution→module mappings without inventing asymmetric semantics for `--app`.

The init-only experiment commits are preserved under research refs; the misleading candidate refs were reset to the known-green Scikit-support base. See `APP_PROVENANCE_EXPERIMENT.md`.

### Disposition

**Demoted to negative/control research; do not include in this bug fix.** If maintainers later want a first-class false-positive escape from the suffix convention, investigate an explicit module/scaffold control as a separate feature.

## Scikit thunderdome

Artifact capability is no longer disputed. The exact simple scaffold builds correctly with:

```toml
[tool.scikit-build]
minimum-version = "build-system.requires"
wheel.cmake = false
wheel.packages = ["src/foo-stubs"]
```

Two real source/test candidates were materialized from the same current-main base and both passed formatting, `cargo check`, the simple-stub backend test, and the existing ordinary Scikit app/library tests.

### Scikit-S — support the simple stub scaffold

For inferred simple stubs, omit CMake, pybind11 and C++ starter files and generate the explicit CMake-less adapter.

**Pros**

- follows the same "scaffold semantics first, backend adapter second" rule as Hatch/Poetry/PDM/setuptools;
- honors the selected backend;
- artifact correctness is executed, not hypothetical;
- avoids creating a new unsupported-combination failure path.

**Cons**

- `--build-backend scikit` no longer always means UV's current extension-module starter family;
- current docs would need to mention the conditional pure-stub template.

### Scikit-R — reject the source-generating simple stub combination

Keep Scikit's existing UV template meaning as a CMake/pybind11 extension starter. Tell the user to choose another backend for the generated simple stub scaffold. Keep `--bare --build-backend scikit` available.

**Pros**

- preserves the current documented extension-template family most literally;
- avoids making one selector choose substantially different starter files based on project name.

**Cons**

- rejects a backend combination that is technically valid and artifact-proven;
- gives Scikit different precedence from the other configurable backends;
- requires an early-failure contract and corresponding no-side-effect tests.

### Prototype result

The executed reject→support policy difference was only:

```text
crates/uv/src/commands/project/init.rs | 15 ++++++++----
crates/uv/tests/project/init.rs        | 45 +++++++---------------------------
2 files changed, 19 insertions(+), 41 deletions(-)
```

So implementation size does **not** justify rejection. This is now a genuine policy choice:

- backend-adapter consistency favors **Scikit-S**;
- preservation of today's documented extension-starter identity favors **Scikit-R**.

See `SCIKIT_IMPLEMENTATION_COST.md` and `PROTOTYPE_THUNDERDOME.md`.

## Flit result

**Conditional Flit 4 wins.** Keep ordinary projects on the current Flit requirement and use 4.x only for the inferred simple-stub scaffold. A general Flit-template upgrade changes unrelated compatibility and belongs in separate work.

## Maturin result

No meaningful product variant remains for the generated simple stub scaffold:

- pure-stub capability is unsupported by the backend contract and artifact probe;
- generate a clear init-time rejection before Cargo/PyO3 starter files;
- preserve `--bare --build-backend maturin` so custom/mixed layouts remain possible.

## Current ranking

1. **Variant C: narrow simple-stub scaffold plus backend adapters.**
2. **Variant B: `uv_build`-only containment**, retained as a green regression control.
3. **Variant A: unadapted shared suffix special case**, incomplete across current backend templates.
4. **Variant D: explicit-app provenance override**, retained only as negative/control research for a possible future explicit module/scaffold feature.

Within Variant C, Scikit is the only genuine unresolved backend policy fork.

## Implementation-maintenance guardrails

Reject any implementation that grows into:

- repeated suffix checks scattered through source generation and backend rendering;
- a runtime/backend capability registry;
- a permanent claim that a finished `*-stubs` distribution contains only stubs;
- global backend upgrades that are not required by the selected scaffold;
- special cases in resolver/installer/lockfile paths;
- hidden override semantics on `--app` solely to handle suffix false positives.

A maintainable bug fix should still be recognizable as:

```text
resolve existing project kind and final project name
if source-generating packaged mode and name maps to *-stubs:
    use the simple-stub scaffold
render the selected backend template with its small stub delta
write either normal runtime source or the simple stub source
```

## Reopen triggers

Reopen this comparison only if:

1. a current-main source change alters backend-template ownership;
2. maintainers explicitly define whether `scikit` means backend identity or extension-starter family;
3. a concrete runtime `*-stubs` compatibility case motivates a dedicated explicit module/scaffold override;
4. a backend deprecates one of the explicit configuration mechanisms used by Variant C.

Otherwise further PEP 561 ecosystem exploration is outside the current bug-fix decision.
