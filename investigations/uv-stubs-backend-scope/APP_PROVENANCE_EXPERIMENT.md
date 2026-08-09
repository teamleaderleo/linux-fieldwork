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

Two small provenance factorizations are being compared internally:

1. capture `args.app` locally in `run_project` before settings resolution;
2. retain `explicit_app: bool` in `InitSettings` and pass it through normal dispatch.

Neither requires a new `InitProjectKind` variant.

## First semantic correction: `--app` is currently default-equivalent

Current UV documentation says applications are the default target for `uv init` and “can also be specified with the `--app` flag.” In current settings resolution, both:

```text
uv init foo
uv init --app foo
```

become the same packaged application kind unless another packaging option changes the result.

Therefore making explicit `--app` outrank `-stubs` would **introduce a new semantic distinction** between commands that UV currently documents and implements as equivalent. It would not merely preserve an existing distinction.

## Second correction: a naive runtime override breaks `uv_build`

The first provenance prototype only changed scaffold inference:

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

So an init-only provenance test can go green while recreating the original build-time mismatch.

This is an important test-design correction: any runtime-override prototype must build the generated default-backend project, not merely inspect its source tree and `pyproject.toml`.

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

The current canonical issue is specifically about `uv init --package foo-stubs` producing a layout that disagrees with `uv_build`. The later independent user report is a genuine stub-package use case: generating typing information for an enclosed proprietary API so development can happen outside the proprietary application.

There is no concrete upstream compatibility report requiring a source-generated runtime project named `*-stubs`.

The canonical issue itself allows either rejecting runtime-template combinations or generating a compliant stub layout.

## Current disposition

The provenance idea remains a useful negative/control experiment, but it should be demoted below the suffix-driven Variant C for the current bug fix.

Reasons:

1. `--app` is documented as an explicit spelling of the default application mode, so giving it override semantics adds new policy.
2. The naive one-bit implementation is not artifact-correct with default `uv_build`; a complete version needs an additional `module-name` adapter.
3. `--app` would not be a general suffix false-positive escape because it does not cover runtime libraries.
4. `--bare` already preserves a custom-layout path for unusual distribution/module mappings.
5. The reported and independently confirmed user cases want actual stub distributions, not runtime `*-stubs` projects.

### Recommended bug-fix precedence

```text
bare/custom                     -> no scaffold inference
source-generating packaged mode
  + project name maps to *-stubs -> simple stub scaffold
otherwise                       -> existing runtime scaffold
```

If maintainers later want a regular-package escape from `uv_build`'s documented suffix false positives, investigate it as a separate explicit module/scaffold-control feature rather than smuggling that policy into `--app`.

## Hosted provenance prototype caveat

Internal UV carrier #84 was started before the `uv_build` build-contract hole was identified. Its initial gates check generated source/config plus existing regression tests, but do **not** build the explicit-app default-`uv_build` case. Any branches published by that carrier are therefore **init-only negative controls**, not artifact-valid product candidates.

The carrier result remains useful for measuring the raw cost of retaining CLI provenance, but it cannot promote Variant D by itself.

No canonical upstream interaction was made.
