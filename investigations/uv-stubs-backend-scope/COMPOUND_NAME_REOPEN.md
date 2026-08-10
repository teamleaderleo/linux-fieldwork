# UV simple-stub compound-name normalization reopen

External context only:

- https://redirect.github.com/astral-sh/uv/issues/19663
- https://redirect.github.com/astral-sh/uv/pull/19671
- https://redirect.github.com/astral-sh/uv/blob/main/crates/uv-normalize/src/package_name.rs
- https://redirect.github.com/astral-sh/uv/blob/main/crates/uv-build-backend/src/lib.rs
- https://redirect.github.com/pypa/flit/blob/main/flit_core/flit_core/config.py
- https://redirect.github.com/python-poetry/poetry-core/blob/main/src/poetry/core/masonry/utils/package_include.py
- https://redirect.github.com/pypa/hatch/blob/master/backend/src/hatchling/builders/config.py
- https://redirect.github.com/pdm-project/pdm-backend/blob/main/src/pdm/backend/config.py
- https://redirect.github.com/pypa/setuptools/blob/main/setuptools/command/build_py.py

State: `NARROW REOPEN — COMPOUND MODULE NAME WAS NOT COVERED BY foo-stubs FIXTURE`

Date: 2026-08-10

Related: #475, #521, controlled UV candidate `teamleaderleo/uv#82`.

No canonical upstream interaction is authorized or performed by this record.

## Finding

The existing artifact fixture `foo-stubs` hides a normalization step because its runtime stem `foo` contains no separators.

For canonical distribution name:

```text
foo-bar-stubs
```

current `uv_build` derives the stub module directory by normalizing the **stem** and preserving only the PEP 561 suffix hyphen:

```text
foo_bar-stubs
```

Therefore the generated source contract is:

```text
src/foo_bar-stubs/__init__.pyi
```

The current #82 candidate instead uses `PackageName::as_str()` for the generated stub directory, which yields:

```text
src/foo-bar-stubs/__init__.pyi
```

That is a candidate defect for compound names.

## Primary-source alignment

### UV

`PackageName` canonicalizes runs of `-`, `_`, and `.` to a canonical hyphenated distribution name. `as_dist_info_name()` replaces those canonical hyphens with underscores.

`uv_build::find_module_path_from_package_name` strips the final `-stubs`, converts the remaining stem through `PackageName::as_dist_info_name()`, then appends literal `-stubs`.

### Flit 4

Current Flit contains an explicit `normalize_pkg_name` rule:

```python
if name.endswith('-stubs'):
    return name[:-6].replace('-', '_') + '-stubs'
return name.replace('-', '_')
```

So Flit independently derives the same `foo_bar-stubs` module name from project `foo-bar-stubs`.

### Poetry Core

Poetry's explicit package include uses the configured literal include path. Its `PackageInclude.is_stub_only()` recognizes the selected package when its root package name ends in `-stubs` and its files are `.pyi`/`py.typed`.

Therefore an explicit include of `foo_bar-stubs` from `src` is the direct adapter for the corrected generated tree.

### Hatchling

Hatchling's `packages` setting is an explicit list of relative paths. It normalizes path spelling, then uses the selected path as its include basis. Therefore the adapter should name the corrected path `src/foo_bar-stubs`.

### PDM Backend

`[tool.pdm.build] includes` is an explicit path/glob list and PDM's package-directory logic treats `src/...` includes as source-root selections. Therefore the adapter path should likewise follow the generated directory: `src/foo_bar-stubs`.

### setuptools

Setuptools includes `.pyi` and `py.typed` as implicit data-file patterns in current `build_py`; the existing compatibility-floor research uses an explicit wildcard package-data rule for older supported versions. The generated directory still needs the corrected `foo_bar-stubs` spelling even though the TOML adapter does not embed the package path.

## Correct implementation shape

Do not derive backend adapter paths independently from the distribution name. Derive one generated module-directory value and reuse it everywhere.

Conceptually:

```rust
fn simple_stub_module_dir(package: &PackageName) -> Option<String> {
    package
        .as_dist_info_name()
        .strip_suffix("_stubs")
        .map(|stem| format!("{stem}-stubs"))
}
```

Then use the returned `foo_bar-stubs` for:

- common source generation;
- Hatch `packages = ["src/<module-dir>"]`;
- Poetry `packages = [{ include = "<module-dir>", from = "src" }]`;
- PDM `includes = ["src/<module-dir>"]`.

Flit and `uv_build` need no path table once source generation follows the same rule. Setuptools retains wildcard `*.pyi` package data.

## Execution receipt pending

Internal PR #522 runs two controls against exact current #82 head `64f94a41fd7c472224d340337dd4b6cab2a7d3fd`:

1. record the candidate as-is for `foo-bar-stubs`;
2. rename only the generated module directory to `foo_bar-stubs`, update the explicit Hatch/Poetry/PDM path selectors, then build and inspect wheels across all six supported Python backends.

The result should determine whether this is purely a shared path-derivation correction or whether another backend-specific naming exception exists.
