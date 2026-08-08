## Question

Independently challenge the design direction in internal draft PR #475. Do not assume its proposed model is correct.

The claim to test is:

> A `*-stubs` name should select stub-only project semantics first; the selected backend should then provide direct support, backend-specific config/version floors, or reject the combination.

## What to challenge

- whether `*-stubs` is the right semantic boundary for `uv init`;
- conditional versus global backend version-floor changes, especially Flit 4 and setuptools 69;
- whether Scikit-build should be rejected under UV's existing CMake/pybind11 selector or supported with a pure-stub variant;
- whether Maturin should be rejected during init rather than failing at build time;
- whether any backend contradicts the common `src/foo-stubs/__init__.pyi` / no-runtime-script model;
- whether the implementation can remain one project-kind decision plus a backend capability adapter rather than scattered suffix special cases.

## Evidence

Read #458, #459, and `investigations/uv-stubs-backend-scope/DESIGN_DIRECTION.md`. A useful review should try to produce a counterexample, source contradiction, or smaller model, not simply endorse the proposal.

The #459 Scikit/Maturin hosted execution rows are being rerun after fixing expected-failure handling. Keep source-backed conclusions separate from artifact-complete proof until that receipt lands.

External context only: https://redirect.github.com/astral-sh/uv/issues/19663 and https://redirect.github.com/astral-sh/uv/pull/19671.

Internal research only. No product candidate changes and no canonical upstream interaction without separate authorization.
