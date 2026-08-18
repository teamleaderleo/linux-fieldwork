# UV simple-stub Scikit prototype thunderdome

State: `BOTH VARIANTS GREEN — POLICY DIFFERENCE IS SMALL`

Date: 2026-08-09

Related internal work: #458, #459, #475, #476, `teamleaderleo/uv#54`, `teamleaderleo/uv#81`.

External context only:

- https://redirect.github.com/astral-sh/uv/issues/19663
- https://redirect.github.com/astral-sh/uv/pull/19671

No canonical upstream mutation is authorized by this record.

## Purpose

Materialize the two surviving Scikit policies from the same exact current-main source and the same common simple-stub implementation, then compare actual source/test deltas rather than prose estimates.

The two policies are:

- **Scikit-S:** support the inferred simple stub scaffold with scikit-build-core's explicit CMake-less wheel configuration;
- **Scikit-R:** preserve UV's current Scikit extension-template meaning and reject the source-generating simple-stub combination, while keeping `--bare` available.

## Exact source and carrier

Public source base:

```text
astral-sh/uv@dd0584d560a4693b5713a78be54304123ada3e77
```

Disposable owned-fork execution carrier:

```text
teamleaderleo/uv#81
workflow: Fieldwork 19671 Scikit thunderdome v2
run: 31289301879
job: 93183658365
runner: Ubuntu 24.04.4
pinned Rust: 1.97.1
```

The first carrier run `31289261824` failed before candidate publication because the pinned toolchain did not have `rustfmt` installed. That was a harness-only failure. The v2 carrier installed the matching `rustfmt` component and is the authoritative receipt.

## Publication fence

Each variant started independently from the exact public base. A candidate branch was pushed only after all of these passed:

```text
cargo fmt --all
git diff --check
cargo check --locked -p uv
cargo test --locked -p uv --test project init::init_package_stubs_backends -- --exact
cargo test --locked -p uv --test project init::init_app_build_backend_scikit -- --exact
cargo test --locked -p uv --test project init::init_lib_build_backend_scikit -- --exact
```

The last two tests are pre-existing ordinary Scikit extension-template tests. Keeping them green prevents either prototype from "winning" by silently changing normal Scikit projects.

## Source-only candidates

### Scikit-S — support

```text
branch: candidate/19671-simple-stubs-scikit-support
head: 1993c1e81ec8446d2db76308c4d516fdf23d5162
parent: dd0584d560a4693b5713a78be54304123ada3e77
```

Exactly two source/test files change:

- `crates/uv/src/commands/project/init.rs`
- `crates/uv/tests/project/init.rs`

The shared simple-stub implementation generates `src/foo-stubs/__init__.pyi`, suppresses the generated runtime script, applies the known Hatch/Poetry/PDM/setuptools adapters, uses Flit 4 only for this scaffold, and rejects Maturin before creating project/VCS state.

For Scikit, it adds:

```toml
[tool.scikit-build]
minimum-version = "build-system.requires"
wheel.cmake = false
wheel.packages = ["src/foo-stubs"]

[build-system]
requires = ["scikit-build-core>=0.12"]
build-backend = "scikit_build_core.build"
```

The stub branch omits `pybind11`, the C/C++/CMake cache keys, `CMakeLists.txt`, `src/main.cpp`, `_core.pyi`, and the runtime wrapper. Ordinary Scikit projects still use the existing extension template and passed their existing tests.

### Scikit-R — reject

```text
branch: candidate/19671-simple-stubs-scikit-reject
head: 7547ae20fbebc2bc3077a3a3b66839a0b38a3ed1
parent: dd0584d560a4693b5713a78be54304123ada3e77
```

It shares the same simple-stub implementation and backend adapters, but adds an early Scikit compatibility diagnostic before `create_dir_all`/VCS initialization. Its focused test proves:

- source-generating `foo-stubs + scikit` fails;
- the target project directory is not left behind;
- `--bare --build-backend scikit` still succeeds with no generated `src` tree.

Ordinary Scikit extension projects also passed their pre-existing app/library tests.

## Authoritative direct policy diff

The v2 job compared the two published branches directly after both were green.

From Scikit-R to Scikit-S:

```text
crates/uv/src/commands/project/init.rs | 15 ++++++++----
crates/uv/tests/project/init.rs        | 45 +++++++---------------------------
2 files changed, 19 insertions(+), 41 deletions(-)
```

The production delta is structurally just:

1. remove Scikit from the early rejection block; and
2. add one guarded `ProjectBuildBackend::Scikit if simple_stub` build-system arm containing the CMake-less configuration.

The common prerequisite function already returns early for `Scikit + simple_stub`; in Scikit-S that suppresses `CMakeLists.txt`, while in Scikit-R the branch is unreachable after validation.

The test delta reflects different contracts rather than production complexity:

- Scikit-S is one success row in the existing backend table, with required CMake-less keys and forbidden native-template keys;
- Scikit-R needs explicit failure/no-side-effect assertions plus a successful `--bare` escape-hatch control.

## Result

The prototype falsifies the claim that Scikit-S is materially more invasive to implement or maintain.

Both variants:

- stay entirely inside `uv init` source/tests;
- preserve ordinary Scikit extension behavior;
- require no Scikit version-floor change;
- use no new compatibility registry or cross-crate subsystem;
- compile and pass the same focused gates.

The actual production-policy difference is small enough that implementation size should not decide the choice.

## What still differs

### Scikit-S advantages

- follows the same "simple scaffold first, backend adapter second" rule as Hatch/Poetry/PDM/setuptools;
- honors a user's explicit selection of scikit-build-core when that backend can represent the requested scaffold;
- avoids rejecting a technically valid, artifact-proven combination;
- does not introduce a new failure path for that backend.

### Scikit-R advantages

- preserves today's UV documentation and template promise most literally: current docs introduce Scikit under extension-module projects and say it generates CMake/C++ starter files;
- avoids making one `--build-backend scikit` selector choose two substantially different starter families based on the inferred project scaffold;
- has the smaller conceptual change to the existing Scikit template identity.

### New cost exposed by the prototype comparison

Rejection is not free. To make it a clean `uv init` contract, validation needs to run before project-directory/VCS side effects and that failure behavior needs explicit tests.

Support is not free either. The current docs would become incomplete if they continued to imply that every Scikit init generates an extension-module starter; a supported stub branch should be documented as a conditional template exception.

## Current policy ranking

The code experiment does not create an evidence-based technical winner.

- **Backend-adapter consistency:** Scikit-S wins.
- **Preservation of today's documented template identity:** Scikit-R wins.
- **Implementation-size / cross-cutting-risk argument:** effectively a tie; the difference is too small to justify rejection by itself.
- **Failure-path complexity:** Scikit-S is slightly simpler because it does not create a new unsupported-combination path.
- **Documentation change:** Scikit-R is slightly simpler because current docs already describe the extension-only starter.

If optimizing for the likely smallest-review semantic change, Scikit-R has a narrow edge. If maintainers view `--build-backend` primarily as backend identity, Scikit-S is the cleaner product behavior.

This is now a maintainer/product-policy decision with both concrete implementations available internally, not an unanswered research or feasibility question.

## Important isolation from explicit-app provenance

These two prototypes intentionally isolate the Scikit choice. They implement the suffix-driven simple scaffold for current packaged source-generating kinds and do **not** yet carry explicit `--app` provenance through settings resolution.

Therefore they are Variant-C prototypes in `VARIANT_COMPARISON.md`, not the final provenance-aware Variant-D design. A separate small experiment can test the cost of carrying explicit `--app` intent without contaminating this Scikit comparison.

No public upstream contact was made.
