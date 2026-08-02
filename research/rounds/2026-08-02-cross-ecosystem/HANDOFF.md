# Handoff — cross-ecosystem candidate round

Handoff date: 2026-08-02  
State: `ACTIVE — UV SOURCE HOLD; CONTROLLED RUNS QUEUED`  
External contact authorized: `false`  
External contact made: `none`

## Linux Fieldwork state

```text
repository: teamleaderleo/linux-fieldwork
branch: investigation/cross-ecosystem-round-2026-08-02
branch base: 6cc74d846c50b9bbb88247e8a128b67e8c174c1e
```

## Active owned candidate — UV

```text
repository: teamleaderleo/uv
base: 1da26a68629be6ae5fd7f924a7d49ff54763a7df
source branch: fieldwork/uv-lock-requirements-diagnostic
source head: ba55497fe83ea9bb07c04452f8ba190fa4440a05
internal source PR: #12
source state: HOLD / REPAIR

current-source execution PR: #15
focused run: 30754710006 — queued at last check
ordinary CI: 30754710091 — queued at last check

parse-first experiment PR: #13
experiment head: f0673123cbabe859c12fe6baacc1fff872060f17
focused run: 30755038821 — queued at last check
```

The current source models exact `uv.lock` and native `<script>.lock` producer names without reading lock contents. It repairs Unix non-UTF-8 path handling and uses producer-backed tests.

Review found a stronger false-positive boundary: because recognition runs before requirements parsing, a valid `action.py.lock` requirements file is rejected whenever neighboring `action.py` is valid PEP 723. Source PR #12 now records the defect and supersedes its earlier acceptance.

PR #13 encodes a parse-first alternative with a provenance-carrying requirements source variant. It adds controls for the valid same-name collision, missing paths, and constraint routing. The constructor is also used by requirements-syntax exclusion files; constraints and overrides remain separate.

First incomplete step: read run `30755038821` by first failing step, then run `30754710006`. If the experiment passes, revise source #12 and create a clean exact-source rerun. No result is claimed from queued state.

Workspace:

```text
investigations/uv-lock-requirements-diagnostic/
```

## Active capability investigation — WGPU/Naga

```text
repository: teamleaderleo/wgpu
base: 2eddc8c7b2fedd4267f5004745a8bc42974e17a0
branch: fieldwork/naga-f16-bitcast-probe
current head: b39e1822d3317e1b2ab41108211adf048314fa7d
internal draft PR: #4
current focused run: 30752907389
state: queued
```

First run:

```text
run: 30752645663
job: 91509299657
artifact: 8834957333
artifact digest: sha256:aa8fb7e33a743b70026e709f8ed2167ba20351eba0ee1035435e73fe6d6c8da9
```

The first run proved current Naga accepts the originally reported `vec2<f16> → u32` direction. Its red result belonged to a stale expected-failure classifier. The repaired run records both directions neutrally.

First incomplete step: read run `30752907389`. Retire the issue internally if the reverse direction also passes; otherwise narrow the investigation to that asymmetry.

Workspace:

```text
investigations/wgpu-naga-f16-bitcast/
```

## Active overlap review — systemd

```text
canonical issue: systemd/systemd#43214
active canonical PR: systemd/systemd#43217
active PR head checked: d32993d1f67ec1b42719c89eeda9425042df57ce
controlled product branch: none
```

A durable `systemd-analyze verify` fixture covers repeated spaces, line-continuation indentation, and an empty-colon-field compatibility control.

First incomplete step: execute the fixture against canonical baseline and the active PR in disposable checkouts, then compare parsing and serialization behavior.

Workspace:

```text
investigations/systemd-bind-path-whitespace-overlap/
```

## Screened overlap and negative results

- OpenTelemetry JS #6967: active canonical PR #6969; review target, no duplicate.
- ripgrep #3222: active canonical PR #3224 plus a duplicate; no new patch.
- Workerd #176: obsolete against current cached CI implementation.
- Execa: apparent bugs already closed; async iterator documentation not portable across supported Node versions.
- UV #15996: active PR #19388 covers the lock paths and Android.
- libarchive: completed controlled evidence; active canonical overlap remains.

## Separate UV follow-up

Issue `astral-sh/uv#16209` remains a strong separate owned unit. BusyBox disagrees with the `realpath --` form in relocatable console and activation scripts. Preserve historical symlink behavior and test spaces, relative invocation, moved environments, symlinks, and leading-dash paths.

## Resume order

1. UV parse-first experiment result and source repair.
2. UV current-source run for comparative evidence.
3. WGPU neutral capability matrix and stale/narrow decision.
4. systemd active-PR compatibility execution.
5. Start the separate UV BusyBox unit only after the diagnostic source state is explicit.

## Cleanup state

No local repository checkout survived; the runtime could not resolve `github.com`. Controlled CI owns build products and temporary fixture cleanup. No credential, package installation, service, mount, device, or canonical upstream state was created.

## Publication boundary

The UV and WGPU pull requests are internal drafts on controlled forks. No canonical upstream communication has been authorized or made.
