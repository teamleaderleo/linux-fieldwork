# Handoff — UV stubs-package backend boundary

Handoff date: 2026-08-03  
State: `ACTIVE — SCOPED 16-CASE MATRIX QUEUED`  
External contact authorized: `false`  
External contact made: `none`

## Completed evidence

### Original mismatch

```text
controlled PR: teamleaderleo/uv#23
source: 79bbface771210df216b738e9bdc7df95e5a9e6b
run: 30759500353
job: 91527374992
result: success
```

`uv init --package foo-stubs` generated an underscore runtime package and console script; `uv_build` rejected the project because it expected the hyphenated `.pyi` stub-only layout.

### Public candidate backend review

```text
controlled PR: teamleaderleo/uv#28
run: 30800503994
baseline source: 3d00ce70244d8b5660e8c02136568a9147dc97e8
public candidate: 082af3c5eb95bbc0f0173ebc67965919c14e1a0a
baseline job: 91643730813
candidate job: 91643730741
```

Artifacts:

```text
baseline: 8853588265
  digest: sha256:d51fc9f3d74ce805a9e27982b36cbc4f8442bf1d75b86465b02932a4481d63be
candidate: 8855188807
  digest: sha256:ce26ada1e43fca71735ce1f956038aa3b4fee3cd292bb49dc3553b4867119e63
```

Public candidate result:

```text
uv_build       success
Hatch          failure
Flit           failure
PDM            success
Poetry         failure
setuptools     success
Maturin        failure
Scikit-build   success
```

Do not route the public candidate as written. Its hyphenated directory selection and console-script suppression are broader than the backend contract that requires them.

## Current controlled experiment

```text
repository: teamleaderleo/uv
base branch: fieldwork/19671-public-candidate-base
base/head source: 082af3c5eb95bbc0f0173ebc67965919c14e1a0a
branch: fieldwork/19671-uv-backend-scope
head: b49c4c0e92cb05dc86ae87776c6103fcca457e6b
internal draft PR: #30
focused run: 30851211326
focused state at handoff: queued
ordinary CI: 30851211543
ordinary CI state at handoff: pending
```

Carrier files:

```text
.github/fieldwork/19671-scope/apply_backend_scope.py
.github/fieldwork/19671-scope/backend_matrix.sh
.github/workflows/fieldwork-uv-19671-backend-scope.yml
```

The branch is stacked on the exact public candidate and commits no additional product source. The workflow applies a one-file disposable repair to `crates/uv/src/commands/project/init.rs`.

## Scoped design

The disposable patch:

1. resolves the selected backend before deciding whether to add `[project.scripts]`;
2. defines the special stub-only behavior only when the backend is `ProjectBuildBackend::Uv`;
3. suppresses the application script only in that case;
4. chooses the hyphenated `.pyi` module directory only in that case;
5. preserves the previous underscore `.py` generation for all non-UV backends.

`ProjectBuildBackend` derives `PartialEq`, so the backend comparison is source-valid.

## Matrix

The focused workflow covers:

```text
kinds:
  --package
  --lib

backends:
  uv
  hatch
  flit
  pdm
  poetry
  setuptools
  maturin
  scikit
```

Every one of the 16 projects must initialize and build successfully.

Expected layouts:

```text
uv + package/lib:
  src/foo-stubs/__init__.pyi
  no src/foo_stubs/__init__.py
  no project script

non-UV + package:
  src/foo_stubs/__init__.py
  no hyphenated package
  project script present

non-UV + lib:
  src/foo_stubs/__init__.py
  no hyphenated package
  no project script
```

Additional gates:

- exact base, head, and source blob;
- exactly one modified product file;
- `cargo fmt --all --check`;
- `cargo check -p uv`;
- native `init::init_package_stubs` and `init::init_package` tests;
- final source fence and artifact retention.

## First incomplete step

Read focused run `30851211326` in this order:

1. exact source identity and text transformation;
2. rustfmt;
3. `cargo check -p uv`;
4. existing native init tests;
5. package rows, beginning with `uv` then previously failing Hatch/Flit/Poetry/Maturin;
6. library rows;
7. source-fence cleanup and artifact ID/digest.

If green, retain the exact patch and matrix. Do not immediately claim a universal stub-only design for non-UV backends: the current scoped result is a compatibility repair, not proof that the underscore runtime package is the ideal PEP 561 layout for those backends.

## Publication boundary

No canonical UV comment, review, reaction, email, or pull request is authorized. Keep all results internal.

## Cleanup state

All product modifications and generated projects are confined to disposable hosted runners. No local checkout, package index state, credential, or canonical repository state is retained.
