# UV stub-only backend floors: Python compatibility cross-check

State: `ACTIVE DESIGN EVIDENCE — REOPENS TWO VERSION-FLOOR RECOMMENDATIONS`

Date: 2026-08-09

This is an adjacent-context check for the design in internal PR #475. It asks whether a backend feature floor that makes a stub scaffold work also changes the Python versions on which that scaffold can be built from source.

External references in this record use redirect form where they point to GitHub.

## Why this matters

UV still supports Python 3.6–3.9 as Tier 2 project/runtime versions. A generated build-system requirement is executed by the Python interpreter doing the source build, so raising a backend requirement can silently make a project that claims an older `requires-python` range unbuildable from source on that range.

The first design pass proposed capability floors:

- Flit 4 for stub-only support;
- PDM Backend >=2.4.4 for automatic `*-stubs` discovery;
- setuptools >=69 for implicit `.pyi` inclusion.

Those feature floors have their own Python floors:

| Backend capability | Backend Python requirement | Consequence |
|---|---|---|
| Flit 4 | Python >=3.8 | Stub-only Flit cannot preserve build-from-source compatibility on Python 3.6/3.7. |
| PDM Backend 2.4.4 | Python >=3.9 | A direct-support floor would drop Python 3.7/3.8 build compatibility relative to older PDM Backend releases. |
| setuptools 69 | Python >=3.8 | Raising UV's current `setuptools>=61` floor would drop Python 3.7 build compatibility. |

Sources:

- UV Python support: https://docs.astral.sh/uv/reference/policies/python/
- Flit 4 release history: https://flit.pypa.io/en/stable/history.html
- PDM Backend 2.4.4 metadata: https://pypi.org/project/pdm-backend/2.4.4/
- setuptools 69.0.0 metadata: https://pypi.org/project/setuptools/69.0.0/
- setuptools 61.0.0 metadata: https://pypi.org/project/setuptools/61.0.0/

## Setuptools: explicit config may be better than a version floor

The earlier #459 conclusion correctly found that setuptools 68.2.2 can discover the `foo-stubs` directory but does not include the sole `.pyi` implicitly, while 69 adds implicit `.pyi`/`py.typed` package-data patterns.

The compatibility question is whether UV actually needs that implicit behavior.

Setuptools 61 source already contains PEP 561-aware package discovery. In flat-layout discovery it explicitly accepts a root package name ending in `-stubs`; in src-layout it uses the PEP 420 package finder over the source tree.

Source:

- https://redirect.github.com/pypa/setuptools/blob/v61.0.0/setuptools/discovery.py

Setuptools 61 `build_py` also already honors explicit `package_data` patterns for every discovered package and copies matching files into that package's build directory.

Source:

- https://redirect.github.com/pypa/setuptools/blob/v61.0.0/setuptools/command/build_py.py

That supports an alternative stub scaffold which preserves UV's existing backend floor:

```toml
[tool.setuptools.package-data]
"foo-stubs" = ["*.pyi"]

[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"
```

If the wheel probe confirms this at the current lower bound, this is likely preferable to `setuptools>=69` because it expresses the needed file contract directly and does not unnecessarily require Python >=3.8 for source builds.

The existing repaired #459 carrier already tests the same explicit package-data mechanism at setuptools 68.2.2. A lower-bound execution case should be added before choosing between explicit config and a version-floor policy.

## PDM: automatic discovery is not the only path

PDM Backend 2.4.4 added automatic recognition of `*-stubs` directories containing `__init__.pyi`. That is useful direct support, but it may not be the minimum backend capability UV needs.

PDM Backend 2.1.4 source already supports explicit build includes:

```toml
[tool.pdm.build]
includes = ["src/foo-stubs"]
```

Its file collector uses user-specified includes directly and recursively collects files under an included directory. Its wheel collector removes the configured `src/` package-dir prefix while preserving the remaining relative path. With the fixed fixture, that source path therefore maps naturally as:

```text
src/foo-stubs/__init__.pyi
    -> foo-stubs/__init__.pyi
```

Sources:

- explicit include collection: https://redirect.github.com/pdm-project/pdm-backend/blob/2.1.4/src/pdm/backend/base.py
- wheel `src/` prefix removal: https://redirect.github.com/pdm-project/pdm-backend/blob/2.1.4/src/pdm/backend/wheel.py
- `src` package-dir default and `includes` setting: https://redirect.github.com/pdm-project/pdm-backend/blob/2.1.4/src/pdm/backend/config.py

PDM Backend 2.1.4 supports Python >=3.7, while 2.4.4 requires Python >=3.9.

This creates a plausible alternative policy:

```toml
[tool.pdm.build]
includes = ["src/foo-stubs"]

[build-system]
requires = ["pdm-backend"]
build-backend = "pdm.backend"
```

That would trade automatic discovery for explicit generated configuration and potentially preserve more of UV's existing Python compatibility surface.

This needs an executed wheel probe before replacing the 2.4.4-floor recommendation. Source evidence says the path collector should work; the design record should not promote it to artifact-proven until the wheel is inspected.

## Flit is different

Flit 3.x does not have an equivalent explicit package-table escape hatch for this stub-only behavior. Stub package support itself landed in Flit 4, and Flit 4 requires Python >=3.8.

So the compatibility choice is real rather than merely a choice between implicit and explicit configuration:

- for Python >=3.8, use Flit 4 for a genuine stub-only scaffold;
- for a project that must be buildable from source on Python 3.6/3.7, the current Flit backend cannot honestly satisfy both the stub-only project contract and that build-Python range.

A future UV candidate should decide whether to reject that combination, constrain the generated project, or document the build-backend minimum clearly. A global Flit 4 template upgrade is especially not neutral because UV still has Tier 2 support for Python 3.6/3.7.

## Poetry context

Current UV already requires `poetry-core>=2,<3`. Poetry Core 2.0 requires Python >=3.9, and current 2.4.1 requires Python >=3.10. This is an existing backend-template compatibility boundary rather than something introduced by stub-only support.

That makes Poetry useful as a control: UV does not currently guarantee that every backend selector supports every Python version UV itself can manage. Still, a new stub-only implementation should avoid raising backend Python floors unnecessarily when explicit configuration can express the same package contract.

## Revised design hypothesis

Do not equate “backend gained automatic stub support at version X” with “UV should require version X.”

Prefer the smallest backend contract that produces the correct wheel while preserving the existing template's compatibility surface:

- Hatch: explicit package selection; no new floor identified.
- Poetry: explicit package selection; existing Poetry Core 2.x floor remains.
- Flit: real feature floor at 4.x; no known 3.x configuration substitute.
- PDM: test explicit `tool.pdm.build.includes` on older compatible backend before choosing a 2.4.4 floor.
- setuptools: test explicit package-data at the existing `>=61` floor before choosing a 69 floor.
- Maturin/Scikit: rejection/template-semantics question unchanged by this pass.

## Reopen trigger and stop condition

This cross-context pass is complete when the two explicit-config alternatives are executed and their wheel payloads inspected:

1. `pdm-backend==2.1.4` (or the oldest intentionally supported candidate) plus `includes = ["src/foo-stubs"]`;
2. `setuptools==61.0.0` plus `"foo-stubs" = ["*.pyi"]` package data.

If either fails, keep the higher capability floor and record the failure owner. If both succeed, update PR #475's backend policy table so version floors are used only where they are genuinely required.

No product candidate was changed and no canonical upstream interaction was made.
