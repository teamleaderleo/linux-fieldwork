# UV stubs-package backend boundary

State: `ACTIVE — BACKEND CAPABILITY RESEARCH; UV-ONLY CANDIDATE PROVISIONAL`  
Canonical issue: [uv issue 19663](https://redirect.github.com/astral-sh/uv/issues/19663)  
Active public candidate: [uv PR 19671](https://redirect.github.com/astral-sh/uv/pull/19671)  
Existing public Fieldwork comment: [comment 5210595906](https://redirect.github.com/astral-sh/uv/pull/19671#issuecomment-5210595906)  
Maintainer follow-up: [comment 5217482196](https://redirect.github.com/astral-sh/uv/pull/19671#issuecomment-5217482196)  
Further external mutation authorized by this record: `false`

## Current question

A distribution named `foo-stubs` should be treated as a stub-only package unless a backend cannot represent that project kind. The target source shape is therefore:

```text
src/foo-stubs/__init__.pyi
```

with no generated runtime console script.

The unresolved part is backend policy:

```text
foo-stubs
  -> backend supports stub-only directly
  -> backend supports stub-only with explicit configuration
  -> backend does not support this project kind and should be rejected
```

Do not assume that a successful build of `src/foo_stubs/__init__.py` is the desired compatibility result. The earlier matrix measured build success, not whether the produced wheel was a correct PEP 561 stub-only distribution.

## Exact public candidate

```text
base: 3d00ce70244d8b5660e8c02136568a9147dc97e8
head: 082af3c5eb95bbc0f0173ebc67965919c14e1a0a
source file: crates/uv/src/commands/project/init.rs
source blob: c4a07138bf1ae1f09ffc8fdc276679e53c01bb4c
```

The public candidate:

1. suppresses `[project.scripts]` whenever the project name ends in `-stubs`;
2. selects a hyphenated module directory whenever the name ends in `-stubs`;
3. writes `__init__.pyi` and returns early only when the backend is `uv_build`.

The third choice is backend-scoped. The first two are not.

## Completed baseline reproducer

Controlled fork PR `teamleaderleo/uv#23` reproduced the original mismatch:

```text
source: 79bbface771210df216b738e9bdc7df95e5a9e6b
run: 30759500353
job: 91527374992
conclusion: success
```

Observed:

- `uv init --package foo-stubs` generated `src/foo_stubs/__init__.py`;
- the project declared `foo-stubs = "foo_stubs:main"`;
- `uv build` exited 2 because `uv_build` expected `src/foo-stubs/__init__.pyi`.

That branch was closed without merge after evidence transfer.

## Completed eight-backend regression matrix

Controlled fork PR `teamleaderleo/uv#28` compared exact baseline and public-candidate source:

```text
carrier head: 091c61d9a12060350a6cc0e80af7d67473d9d27f
run: 30800503994
baseline source: 3d00ce70244d8b5660e8c02136568a9147dc97e8
public candidate: 082af3c5eb95bbc0f0173ebc67965919c14e1a0a
baseline job: 91643730813 — success
candidate job: 91643730741 — success
baseline artifact: 8853588265
baseline digest: sha256:d51fc9f3d74ce805a9e27982b36cbc4f8442bf1d75b86465b02932a4481d63be
candidate artifact: 8855188807
candidate digest: sha256:ce26ada1e43fca71735ce1f956038aa3b4fee3cd292bb49dc3553b4867119e63
```

Result:

| Backend | Baseline build | Public candidate build |
|---|---:|---:|
| uv_build | failure | success |
| Hatch | success | failure |
| Flit | success | failure |
| PDM | success | success |
| Poetry | success | failure |
| setuptools | success | success |
| Maturin | success | failure |
| Scikit-build | success | success |

This remains useful evidence: PR 19671 changes shared initialization behavior and produces failing generated projects for Hatch, Flit, Poetry, and Maturin. It does **not** establish that the correct repair is to restore ordinary underscore runtime-package behavior for every non-UV backend.

## Provisional UV-only containment candidate

Current clean controlled candidate:

```text
repository: teamleaderleo/uv
internal draft PR: #54
base branch: fieldwork/19671-current-main-product-base
base: bab65d090d4f05d7dab432ac25304288ff1f2327
branch: candidate/19671-current-main-uv-backend-scope
head: 3e1fa232b6240e0d2617f399d3ca801c4760a30d
matrix run: 31013625610 — all 16 init/build rows passed
```

The candidate proves a narrow causal fact: containing the special layout/script behavior to `uv_build` removes the cross-backend build regressions.

It is **not the current implementation recommendation**. Its non-UV output deliberately preserves the old `foo_stubs/__init__.py` runtime-package shape and application script. Maintainer feedback indicates that at least some third-party backends can instead represent a genuine stub-only package with backend-specific configuration.

Keep PR #54 as a containment/control experiment until the capability research below completes.

## Maintainer guidance received

The maintainer follow-up identifies a more specific backend model:

- Hatch needs an explicit wheel package selection, beginning with:

  ```toml
  [tool.hatch.build.targets.wheel]
  packages = ["src/foo-stubs"]
  ```

- Poetry needs an explicit package declaration, beginning with:

  ```toml
  [tool.poetry]
  packages = [{ include = "foo-stubs" }]
  ```

  The exact `src/` form still needs verification.

- Flit should support stub-only packages; inspect and verify the current behavior associated with [Flit PR 742](https://redirect.github.com/pypa/flit/pull/742).
- Maturin does not support stub-only packages and is not an appropriate backend for that project kind; verify the current source/docs and determine the clean UV rejection boundary.

This feedback supersedes the earlier working assumption that all non-UV backends should retain ordinary runtime-package semantics.

## Parallel research lanes

Two bounded internal issues can be handed to separate workers without overlapping implementation authority:

- Linux Fieldwork #458 — Hatch, Poetry, and Flit;
- Linux Fieldwork #459 — PDM, setuptools, Scikit-build, and Maturin.

Both lanes must inspect **wheel contents**, not just process exit status. For every backend classify:

1. exact backend/version used by current UV initialization;
2. direct stub-only support versus explicit configuration versus unsupported;
3. minimal configuration;
4. build result;
5. actual wheel payload, requiring `foo-stubs/__init__.pyi` for a supported stub-only case;
6. whether a runtime script is absent;
7. source/docs explaining the behavior;
8. plausible UV behavior: generate directly, generate backend-specific configuration, or reject.

Do not modify the product candidate from either helper lane. Research and report first.

## Next decision

After #458 and #459 report, build one capability table:

| Backend | Stub-only support | Extra config | Correct UV init policy |
|---|---|---|---|
| uv_build | yes | none known | generate stub-only layout |
| Hatch | research | research | determine |
| Flit | research | research | determine |
| PDM | research | research | determine |
| Poetry | research | research | determine |
| setuptools | research | research | determine |
| Maturin | expected unsupported | n/a | verify rejection policy |
| Scikit-build | research | research | determine |

Only then choose whether PR #54 should be replaced by a backend-capability implementation, reduced to a narrower UV-only fix, or retained only as evidence.

## Publication boundary

The thread already contains the human-posted Fieldwork comment linked above. This record does not authorize another canonical UV comment, review, reaction, pull request, email, or other upstream mutation. Internal and controlled-fork work may continue. Any external GitHub references added to controlled-repository interaction surfaces must use `redirect.github.com`.