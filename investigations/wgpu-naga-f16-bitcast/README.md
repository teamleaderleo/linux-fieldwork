# WGPU/Naga `vec2<f16> ↔ u32` bitcast investigation

State: `ACTIVE — CURRENT CAPABILITY RERUN QUEUED`  
Canonical issue: `gfx-rs/wgpu#8896`  
External contact authorized: `false`  
External contact made: `none`

## Question

Is canonical issue #8896 still current in either direction, or has Naga gained support since the January 2026 report?

## Reported behavior

The issue reports rejection of:

```wgsl
bitcast<u32>(value: vec2<f16>)
```

with `Unable to cast`. The reverse `u32 → vec2<f16>` belongs to the same total-bit-width capability.

## Exact controlled identities

```text
repository: teamleaderleo/wgpu
base branch: trunk
base commit: 2eddc8c7b2fedd4267f5004745a8bc42974e17a0
probe branch: fieldwork/naga-f16-bitcast-probe
current probe head: b39e1822d3317e1b2ab41108211adf048314fa7d
internal draft PR: teamleaderleo/wgpu#4
current focused run: 30752907389
current run state: queued
```

The branch changes two evidence files and no product source:

- `contrib/fieldwork/naga_f16_bitcast_probe.sh`
- `.github/workflows/fieldwork-naga-f16-bitcast.yml`

## First executed result

Initial head `91c59563534f6f239e6b35ce216ff5fca570e299` ran as workflow `30752645663`, job `91509299657`.

Setup, toolchain, locked Naga CLI build, and the repository's normal Shaders workflow passed. Focused artifact `8834957333` with digest `sha256:aa8fb7e33a743b70026e709f8ed2167ba20351eba0ee1035435e73fe6d6c8da9` recorded:

```text
scalar f32 → u32:        accepted, status 0
vec2<f16> → u32:         accepted, status 0
stdout:                  Validation successful
stderr:                  empty
```

The focused job failed only because the probe encoded the issue's old rejection as an expected result. It stopped before the reverse case.

This is a fixture/classifier result and a meaningful product finding: the originally reported direction is no longer failing on the controlled current head.

## Current probe contract

Commit `b39e1822d3317e1b2ab41108211adf048314fa7d` now executes all three shaders and records each as:

- `accepted`;
- `unable-to-cast`;
- `unexpected-failure`.

Only the scalar control or an unexpected failure makes the probe red. The probe retains exact shaders, stdout/stderr, hashes, repository and source blobs, toolchain identity, and built binary digest. Temporary fixtures are removed through a trap.

## Current decision boundary

The reverse case is the only unresolved discriminator:

```wgsl
bitcast<vec2<f16>>(value: u32)
```

If run `30752907389` accepts it, retire the canonical issue as stale in the internal record and close the controlled evidence carrier. If it remains rejected, narrow the investigation to a one-direction asymmetry before mapping implementation layers.

## Cleanup

The first runner uploaded its partial receipt and removed temporary state. No GPU, driver, device, credential, or persistent external state was used.

## Next step

Read run `30752907389`, retain its artifact and exact statuses, and choose `RETIRED` or a narrowly restated investigation. Do not start a broad IR refactor before that result.
