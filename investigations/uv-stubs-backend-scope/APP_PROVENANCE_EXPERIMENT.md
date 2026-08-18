# UV simple-stub initialization: explicit-app provenance experiment

State: `PROVENANCE IS CHEAP, BUT NOT RECOMMENDED AS THE BUG-FIX ESCAPE HATCH`

Date: 2026-08-09

Related internal work: #458, #459, #475, #476, `teamleaderleo/uv#81`, `teamleaderleo/uv#84`.

External context only:

- https://redirect.github.com/astral-sh/uv/issues/19663
- https://redirect.github.com/astral-sh/uv/pull/19671

No canonical upstream interaction is authorized by this record.

## Question

Should explicit `--app` outrank the conventional `*-stubs` name heuristic when UV is generating a packaged source tree?

The proposed precedence was:

```text
bare/custom                      -> no scaffold inference
explicit --app                  -> runtime application scaffold
otherwise name maps to *-stubs  -> simple stub scaffold
otherwise                        -> existing runtime scaffold
```

This was intended as a non-bare escape hatch for the legal-but-unusual case of a runtime distribution whose name ends in `-stubs`.

## Source ownership

Current source pin reviewed:

```text
astral-sh/uv@dd0584d560a4693b5713a78be54304123ada3e77
```

`InitSettings::resolve` still has the raw `app` boolean, but current resolution deliberately collapses explicit `--app` and the default packaged-application path into `InitProjectKind::ApplicationWithLibrary`.

The final project/package name is resolved later in `commands::init`: when `--name` is absent, UV derives the package name from the final target directory. Therefore stub-vs-runtime scaffold inference cannot safely be completed in `InitSettings::resolve`; only CLI provenance can be retained there.

Two small provenance factorizations were executed internally:

1. capture `args.app` locally in `run_project` before settings resolution;
2. retain `explicit_app: bool` in `InitSettings` and pass it through normal dispatch.

Neither requires a new `InitProjectKind` variant.

## Hosted factoring receipt

Internal UV carrier #84 executed from the already-green Scikit-support simple-stub base:

```text
base: 1993c1e81ec8446d2db76308c4d516fdf23d5162
run: 31290172540
job: 93185874136
conclusion: success for the original init-focused gates
```

The original gates included formatting, `cargo check -p uv`, the explicit-app generation test, the shared simple-stub backend test, ordinary Scikit app/library tests, and the ordinary packaged-application test.

Raw production cost versus the common base:

### Local capture

```text
crates/uv/src/commands/project/init.rs  +7/-1
crates/uv/src/lib.rs                    +5/-0
```

Production total: **12 additions, 1 deletion (13 changed-line operations)**. The behavioral test adds 124 lines.

### `InitSettings` field

```text
crates/uv/src/commands/project/init.rs  +7/-1
crates/uv/src/lib.rs                    +1/-0
crates/uv/src/settings.rs               +2/-0
```

Production total: **10 additions, 1 deletion (11 changed-line operations)**. The same behavioral test adds 124 lines.

So preserving provenance is mechanically cheap, and the `InitSettings` form is marginally smaller by raw line count. This does not decide whether the behavior should exist.

## First semantic correction: `--app` is currently default-equivalent

Current UV documentation says applications are the default target for `uv init` and “can also be specified with the `--app` flag.” In current settings resolution, both:

```text
uv init foo
uv init --app foo
```

become the same packaged application kind unless another packaging option changes the result.

Therefore making explicit `--app` outrank `-stubs` would **introduce a new semantic distinction** between commands that UV currently documents and implements as equivalent. It would not merely preserve an existing distinction.

## Second correction: a naive runtime override breaks `uv_build`

The executed provenance prototypes only changed scaffold inference:

```rust
let simple_stub = !explicit_app
    && matches!(self, Self::ApplicationWithLibrary | Self::Library)
    && simple_stub_package_module_dir(name).is_some();
```

For `uv init --app --name foo-stubs` with the default backend this generates the ordinary runtime tree:

```text
src/foo_stubs/__init__.py
```

and a console script.

That is **not enough** for a valid project. `uv_build` independently infers stub-package semantics from `project.name` alone. Its current source explicitly documents this behavior and even notes potential false positives for regular packages whose names end in `-stubs`. With no build-backend override, a distribution named `foo-stubs` is routed to:

```text
src/foo-stubs/__init__.pyi
```

So the init-focused carrier can go green while recreating the original build-time mismatch.

This is an important test-design correction: any runtime-override prototype must build the generated default-backend project, not merely inspect its source tree and `pyproject.toml`.

The successful #84 run is therefore a **factoring receipt and negative control**, not artifact proof for Variant D.

## `uv_build` has a technical escape

The backend exposes:

```toml
[tool.uv.build-backend]
module-name = "foo_stubs"
```

When `module-name` is explicit, `uv_build` resolves that module before falling back to package-name inference. Existing `uv_build` tests already prove an explicit module name overrides `project.name` for regular package builds.

Therefore a *complete* explicit-app runtime override is technically possible, but it needs another generated-backend adapter for the default backend:

```text
explicit --app + generated packaged mode + project name maps to *-stubs + uv_build
    -> runtime src/foo_stubs/__init__.py
    -> normal console script
    -> [tool.uv.build-backend] module-name = "foo_stubs"
```

The third-party runtime side is already covered by the old containment control: `teamleaderleo/uv#54` kept normalized runtime `foo_stubs` projects for non-`uv_build` backends and its hosted package/library matrix built successfully across the backend set. So `uv_build` is the special extra adapter for this runtime-override idea.

## Third correction: `--app` is not a general false-positive escape

Even with the `uv_build` module-name adapter, overloading `--app` solves only one class of false positive: runtime **applications** named `*-stubs`.

A legal runtime **library** distribution named `foo-stubs` would still be inferred as the simple stub scaffold under explicit `--lib`.

If UV wants a first-class way to override the suffix convention, the coherent product control would be a dedicated module/scaffold override (conceptually akin to an exposed module-name or no-stub-inference choice), not an application flag whose documented meaning is otherwise just the explicit form of the default.

For the current bug fix, `--bare` already provides a custom-layout escape hatch without inventing this asymmetric rule.

## Upstream use-case signal

The canonical issue is specifically about `uv init --package foo-stubs` producing a layout that disagrees with `uv_build`. The later independent user report is a genuine stub-package use case: generating typing information for an enclosed proprietary API so development can happen outside the proprietary application.

There is no concrete upstream compatibility report requiring a source-generated runtime project named `*-stubs`.

The canonical issue itself allows either rejecting incompatible backend-template combinations or generating a compliant stub layout.

## Branch hygiene after the stronger artifact finding

The #84 carrier originally published the init-only experiments under candidate-looking refs. After the missing `uv build` gate was identified, those commits were preserved under research-only names:

```text
research/19671-app-provenance-local-init-only
research/19671-app-provenance-settings-init-only
```

The misleading refs:

```text
candidate/19671-app-provenance-local
candidate/19671-app-provenance-settings
```

were force-reset to the known-green Scikit-support base:

```text
1993c1e81ec8446d2db76308c4d516fdf23d5162
```

Internal UV carrier #84 was then closed and explicitly classified as a negative/control receipt. The queued Fieldwork mirror #488 was closed as superseded because it used the same insufficient init-only contract.

## Final disposition

**Do not carry explicit `--app` provenance in the current bug fix. Variant C outranks Variant D.**

Reasons:

1. `--app` is documented as an explicit spelling of the default application mode, so giving it override semantics adds new policy.
2. The naive one-bit implementation is not artifact-correct with default `uv_build`; a complete version needs an additional `module-name` adapter.
3. `--app` would not be a general suffix false-positive escape because it does not cover runtime libraries.
4. `--bare` already preserves a custom-layout path for unusual distribution/module mappings.
5. The reported and independently confirmed user cases want actual stub distributions, not runtime `*-stubs` projects.
6. The small plumbing cost is therefore not a reason to add a new semantic distinction.

### Recommended bug-fix precedence

```text
bare/custom                     -> no scaffold inference
source-generating packaged mode
  + project name maps to *-stubs -> simple stub scaffold
otherwise                       -> existing runtime scaffold
```

If maintainers later want a regular-package escape from `uv_build`'s documented suffix false positives, investigate it as a separate explicit module/scaffold-control feature rather than smuggling that policy into `--app`.

No canonical upstream interaction was made.
