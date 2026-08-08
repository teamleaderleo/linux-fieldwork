# UV stub-only backend lower-bound execution

State: `EXECUTED — DESIGN INPUT`

Date: 2026-08-09

Related internal work: #459, #460, #475, #476.

No product candidate changes. No canonical upstream interaction.

## Question

Do stub-only PDM and setuptools scaffolds really need the newer backend versions that added automatic behavior, or can UV preserve its existing backend requirements by generating explicit backend configuration?

Fixed package contract:

```text
distribution: foo-stubs
source:       src/foo-stubs/__init__.pyi
runtime console script: absent
```

## Final hosted receipt

```text
carrier: teamleaderleo/linux-fieldwork#460
head: f21b2f158fe47c06e5f81369be1f08fb727b982c
workflow: Research 459 stub backend lower bounds
run: 31282617646
job: 93166265545
conclusion: success
runner: Ubuntu 24.04.4 / ubuntu-24.04 image 20260720.247.2
Python: 3.9.25
uv build frontend: 0.11.29
```

The frontend version is only the PEP 517 driver for this fixture. Backend versions are pinned per case below.

## Result

| Case | Backend/config | Wheel result |
|---|---|---|
| PDM negative control | `pdm-backend==2.1.4`, no package config | build succeeds but wheel is metadata-only; `foo-stubs/__init__.pyi` absent |
| PDM explicit | `pdm-backend==2.1.4` + `includes = ["src/foo-stubs"]` | correct wheel; `foo-stubs/__init__.pyi` present; no console script |
| setuptools negative control | `setuptools==61.0.0`, no package-data config | build succeeds but wheel omits `foo-stubs/__init__.pyi` |
| setuptools explicit | `setuptools==61.0.0` + wildcard `*.pyi` package data | correct wheel; `foo-stubs/__init__.pyi` present; no console script |

## PDM

Minimal positive configuration:

```toml
[tool.pdm.build]
includes = ["src/foo-stubs"]

[build-system]
requires = ["pdm-backend"]
build-backend = "pdm.backend"
```

The executed discriminator pinned `pdm-backend==2.1.4` to prove the older code path rather than allowing current automatic stub discovery to hide the result.

Negative control wheel at 2.1.4:

```text
foo_stubs-0.1.0.dist-info/METADATA
foo_stubs-0.1.0.dist-info/RECORD
foo_stubs-0.1.0.dist-info/WHEEL
```

Positive explicit-config wheel at 2.1.4:

```text
foo-stubs/__init__.pyi
foo_stubs-0.1.0.dist-info/METADATA
foo_stubs-0.1.0.dist-info/RECORD
foo_stubs-0.1.0.dist-info/WHEEL
```

The result proves that the release which added *automatic* `*-stubs` discovery is not a necessary UV feature floor. Explicit `tool.pdm.build.includes` is sufficient on this older backend.

### PDM design consequence

Prefer generated explicit config while preserving UV's existing `pdm-backend` requirement unless another compatibility constraint appears. Requiring `pdm-backend>=2.4.4` would buy automatic discovery that the generated config no longer needs.

## setuptools

The first lower-bound attempt used:

```toml
[tool.setuptools.package-data]
"foo-stubs" = ["*.pyi"]
```

Setuptools 61.0.0 rejected that key at `pyproject.toml` schema validation because package-data keys had to be a Python module name or the predefined wildcard `*`. That failure was configuration-owned, not evidence that setuptools 61 could not package the stub tree.

The repaired positive configuration is:

```toml
[tool.setuptools.package-data]
"*" = ["*.pyi"]

[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"
```

Negative control wheel at 61.0.0:

```text
foo_stubs-0.1.0.dist-info/METADATA
foo_stubs-0.1.0.dist-info/RECORD
foo_stubs-0.1.0.dist-info/WHEEL
foo_stubs-0.1.0.dist-info/top_level.txt
```

Positive wildcard-config wheel at 61.0.0:

```text
foo-stubs/__init__.pyi
foo_stubs-0.1.0.dist-info/METADATA
foo_stubs-0.1.0.dist-info/RECORD
foo_stubs-0.1.0.dist-info/WHEEL
foo_stubs-0.1.0.dist-info/top_level.txt
```

No console script is present.

### setuptools design consequence

Prefer explicit wildcard `.pyi` package data while preserving UV's existing `setuptools>=61` requirement. A `>=69` floor is unnecessary for this scaffold: 69 added convenient implicit `.pyi` inclusion, but UV can state the needed package-data contract directly.

## Revised backend-policy principle

Do not use the version that introduced *automatic* stub behavior as a minimum unless UV actually relies on that automatic behavior.

For a generated project, explicit backend configuration is preferable when it:

1. produces the correct PEP 561 wheel;
2. keeps the backend requirement no stricter than the current template;
3. is stable backend configuration rather than implementation trivia;
4. avoids changing the project's build-Python compatibility unnecessarily.

On the current evidence, that principle applies to PDM and setuptools. Flit remains different because the relevant stub-package capability itself landed in Flit 4 rather than merely becoming automatic there.

## Evidence boundary

This execution uses the issue's deliberately minimal single-file stub fixture on Linux/Python 3.9. It proves the package-root path and absence of runtime console scripts for the exact configurations above. It does not by itself claim every nested/partial-stub layout or every backend release behaves identically.

The next distinct question is the broader #459 Scikit/Maturin execution matrix, not another PDM/setuptools version-floor probe.
