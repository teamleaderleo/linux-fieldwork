# uv stubs package initialization and build-backend mismatch

State: `ACTIVE — EXECUTION QUEUED`  
Worker or variant: `LF-R02`  
Public contact authorized: `false`

## Bounded question

Does current uv generate a stubs-package project that its own build backend cannot build, and which component owns the naming contract?

## Exact identities

| Item | Value |
| --- | --- |
| Public repository | `astral-sh/uv` |
| Exact public base | `79bbface771210df216b738e9bdc7df95e5a9e6b` |
| Controlled repository | `teamleaderleo/uv` |
| CI base | `ci/uv-20734-base@f86ccacae9f69d4e77e91ae0e6659772cdb46707` |
| Research branch | `research/uv-20734-stubs-init-mismatch` |
| Research head | `60915b1952f4655d4c0223f4fa43b65e68a2633b` |
| Internal draft PR | `teamleaderleo/uv#23` |
| Focused Actions run | `30759500353` |
| Last observed state | queued |

## Current source map

Initializer owner:

- `crates/uv/src/commands/project/init.rs`
- package generators derive `module_name` from `PackageName::as_dist_info_name()`;
- the generated package directory is `src/<module_name>`;
- the generated file is `__init__.py`.

Build-backend owner:

- `crates/uv-build-backend/src/lib.rs`
- `find_module_path_from_package_name()` recognizes a project name ending in `-stubs`;
- it strips the suffix, normalizes the stem, then constructs `<stem>-stubs`;
- it requires `__init__.pyi` in that directory.

For `foo-stubs`, these rules disagree:

```text
initializer:    src/foo_stubs/__init__.py
build backend:  src/foo-stubs/__init__.pyi
```

## Execution discriminator

The controlled script:

1. builds exact current uv;
2. runs `uv init --package <temp>/foo-stubs`;
3. records the generated file tree and `pyproject.toml`;
4. proves `src/foo_stubs/__init__.py` exists;
5. proves `src/foo-stubs/__init__.pyi` does not exist;
6. runs `uv build`;
7. expects failure with `Expected a Python module at: src/foo-stubs/__init__.pyi`;
8. removes the temporary directory.

The test is intentionally execution-only. A successful run proves the mismatch, not the final repair.

## Design controls

Before selecting a source candidate, determine:

- the canonical import-package spelling for a PEP 561 stubs-only distribution named `foo-stubs`;
- whether `uv init` should generate a stubs-only package automatically from the project suffix;
- whether a regular package named with `-stubs` must remain possible through explicit configuration;
- whether the generated project should contain only `.pyi`, or `.py` plus `py.typed`;
- whether an explicit `module-name` should override suffix inference unchanged;
- whether source distributions and wheels preserve the same layout.

Required negative controls include ordinary hyphenated package names, explicitly configured module names, namespace packages, and a manually correct stubs-only tree.

## Stop and promotion rules

Promote after the exact run completes and the packaging contract identifies one owner. Stop source work if current upstream changes or an equivalent PR resolves the mismatch. Split into initializer and build-backend variants if compatibility evidence supports more than one valid layout.

## Authority

Controlled branches, internal draft PRs, GitHub Actions, source reading, and Fieldwork records are authorized. No public Astral interaction has occurred.
