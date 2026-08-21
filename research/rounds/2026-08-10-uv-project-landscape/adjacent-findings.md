# Adjacent UV findings — 2026-08-10

This supplements `selection.md` with later results from the same broad project-learning pass.

No canonical upstream interaction is authorized by this record. External GitHub references use `https://redirect.github.com/...`.

## 1. Invalid project environments are a command-boundary problem, not just a lock bug

Canonical context:

- https://redirect.github.com/astral-sh/uv/issues/19832
- https://redirect.github.com/astral-sh/uv/issues/21009

Fieldwork #519 executed a cross-command matrix on uv 0.11.19 and 0.12.3.

Receipt:

- run `31344395930`
- job `93323522140`
- Ubuntu 24.04.4
- artifact `uv-invalid-venv-519`
- artifact ID `9046816566`
- artifact SHA-256 `88b0292e2bf97e3d6a66354a9deed570daa4f47944a9b113e728dfaee7449d5b`

The result was identical on both releases.

For an absent or empty `.venv`, read-only/resolution commands (`lock`, `lock --check`, `lock --dry-run`, `lock --frozen`, `tree`, `export`, `workspace metadata`) succeed without modifying the environment path. `sync` and `run` create/populate it.

For a non-empty invalid `.venv` with no `pyvenv.cfg`, every tested command except `lock --frozen` fails with `InvalidProjectEnvironmentDir`. None modify `.venv`.

For a non-empty invalid `.venv` that contains a `pyvenv.cfg` but no Python executable, the read-only commands succeed and preserve the directory, while `sync` and `run` explicitly remove and recreate `.venv`.

The first design lesson is that the current protection is shared too early for some callers. Source comments in `existing_project_environment` describe the error as protection against deleting existing content later, but commands such as normal `lock`, `tree`, `export`, and unsynced `workspace metadata` never need to delete that project environment.

The second lesson is that the destructive-ownership heuristic is not literally "never delete a non-empty invalid directory": a `pyvenv.cfg` is treated as enough evidence that the path is a recreatable virtual environment.

### Existing source vocabulary supports a narrow factoring

Current source already has output modes that intentionally avoid interpreter discovery:

- `uv lock --frozen` uses `LockMode::Frozen` without `ProjectInterpreter::discover`;
- `uv export --frozen` sets `interpreter = None` before entering frozen lock mode;
- `uv workspace metadata --frozen` enters frozen lock mode before interpreter discovery;
- `uv tree` skips interpreter discovery when both `--frozen` and `--universal` are used, while non-universal tree output can legitimately require interpreter-derived marker information.

Therefore the useful abstraction is not "interpreter optional everywhere" and not "ignore invalid environments globally". It is closer to an **environment-consultation policy**:

- read-only/resolution callers may need an interpreter, but can ignore an unusable project environment and discover another interpreter;
- mutating callers must retain project-environment ownership validation before replacement.

A blanket change that makes `discover_existing` swallow `InvalidProjectEnvironmentDir` would erase the safety distinction for destructive callers. Adding `--active` only to `uv lock` would bypass the symptom without modeling the underlying ownership boundary.

Fieldwork #519 remains the durable classification carrier; execution PR #520 was closed evidence-only.

## 2. Registry negative caching has no obvious portable status/header heuristic

Canonical context:

- https://redirect.github.com/astral-sh/uv/issues/17619

Fieldwork #515 sampled negative simple-index behavior and then stopped without a product candidate.

Receipt:

- run `31342821064`
- job `93319290895`
- Ubuntu 24.04.4
- artifact `registry-404-cache-515`
- artifact ID `9046344960`
- artifact SHA-256 `4ae2c30d34c01f90284cf0a1c1cd935b4be871f6fba5e4df83b797591ac5c082`

Observed:

- PyPI and TestPyPI returned 404 with no explicit `Cache-Control`, while repeated requests visibly became CDN hits;
- piwheels returned 404 with validators (`ETag` / `Last-Modified`) but no explicit cache-control directive;
- the sampled PyTorch path returned 403 through CloudFront/S3;
- pypiserver defaults to a 303 fallback for a missing project and switches immediately to 200 after a wheel appears;
- pypiserver with `--disable-fallback` gives 404 then switches immediately to 200 after publication, again without an explicit cache-control directive.

This did not reveal one broadly safe client-side rule based on status plus ordinary cache headers. UV's current conservative no-persistent-negative-response policy is operationally defensible. A future narrower policy would need an explicit registry capability/opt-in or stronger freshness mechanism rather than generic 404 inference.

## 3. `[project]`-less projects are becoming a real project family

Canonical design thread:

- https://redirect.github.com/astral-sh/uv/issues/8582

The older question was whether UV would support dependency groups without a `[project]` table at all. That has moved forward substantially: project-less support exists and `uv lock` support subsequently landed (discussion points to https://redirect.github.com/astral-sh/uv/pull/19087).

The remaining questions are now more semantic:

1. what `uv init` shape should create a true non-package / project-less project;
2. whether a conventional group such as `dependency-groups.main` should be synced by default;
3. how Python-version requirements should be expressed when there is no package metadata.

The third item is not merely theoretical. A current report in the thread shows:

```toml
[dependency-groups]
dev = ["click"]

[tool.uv.dependency-groups]
dev = { requires-python = "==3.13.14" }
```

followed by `uv run --only-dev python -V` selecting Python 3.14 and warning that no workspace `requires-python` exists. In other words, group-level `requires-python` currently constrains the group but does not automatically become the workspace/interpreter requirement for a project-less project.

This is a genuine design gap, but it is already an active upstream design cluster. Fieldwork should observe and use it as context for future `uv init` work rather than opening an isolated competing patch without a sharper invariant.

## 4. Native authentication identity is also moving toward hierarchical matching

Canonical work:

- https://redirect.github.com/astral-sh/uv/pull/18907

The native-auth rewrite moves credential lookup away from exact service-URL/username identity toward realm (`scheme://host:port`) plus path-prefix specificity, while keeping legacy-format compatibility. This is intended to support username-less request lookup and multiple credentials in one realm, including Artifactory-style paths.

Useful future Fieldwork tests, if this work lands and produces ambiguity, would be:

- longest-prefix selection with overlapping paths;
- multiple usernames/credentials in one realm;
- old and new storage formats coexisting during migration;
- a credential stored for a parent path versus a more specific package/download URL.

Do not create a competing auth implementation while upstream still owns the transition.

## Selection effect

After these results, the broad selection state is:

- **live execution:** #504 Intel-macOS `--find-links` discriminator only;
- **completed evidence/contract research:** #508 tool identity, #515 negative-cache semantics, #519 invalid-project-environment command boundary;
- **observe:** project-less project semantics, content-addressed cache lifecycle, native-auth hierarchical matching, release PGO;
- **retired by intent/ownership:** #506 workspace group merging and #509 BusyBox `realpath --`.

The programme should continue preferring cross-layer questions that can overturn a product conclusion over opening one issue per interesting subsystem.
