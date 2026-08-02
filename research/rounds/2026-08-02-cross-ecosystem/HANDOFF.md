# Handoff — cross-ecosystem candidate round

Handoff date: 2026-08-02  
State: `ACTIVE — TWO CONTROLLED RUNS QUEUED`  
External contact authorized: `false`  
External contact made: `none`

## Linux Fieldwork state

```text
repository: teamleaderleo/linux-fieldwork
branch: investigation/cross-ecosystem-round-2026-08-02
branch base: 6cc74d846c50b9bbb88247e8a128b67e8c174c1e
complete branch head immediately before this handoff commit:
c93519914cafd17b2f3b35e16e6f791ac9e7f10a
```

## Active owned candidate — UV

```text
repository: teamleaderleo/uv
base: 1da26a68629be6ae5fd7f924a7d49ff54763a7df
branch: fieldwork/uv-lock-requirements-diagnostic
head: a67f97bec7782c6f60aceefb2a9bcd7045582015
internal draft PR: #12
CI run: 30752526287
state: queued
```

The candidate recognizes existing exact `uv.lock` and script locks paired with a valid PEP 723 sibling, while preserving arbitrary `.lock` requirements files. It uses no lockfile-content guessing.

First incomplete step: classify run `30752526287` and repair only the first owning layer.

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

## Resume order

1. UV CI result and exact candidate repair.
2. WGPU neutral capability matrix and stale/narrow decision.
3. systemd active-PR compatibility execution.
4. Continue broad screening only after those exact run results are retained; prefer a new owned source candidate over another overlap review.

## Cleanup state

No local repository checkout survived. The downloaded WGPU artifact was inspected in an ephemeral container directory. Controlled CI owns build products and temporary fixture cleanup. No credential, package installation, service, mount, device, or canonical upstream state was created.

## Publication boundary

The UV and WGPU pull requests are internal drafts on controlled forks. No canonical upstream communication has been authorized or made.
