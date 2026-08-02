# WGPU/Naga `vec2<f16> ↔ u32` bitcast investigation

State: `RETIRED — CURRENT NAGA ACCEPTS BOTH DIRECTIONS`  
Canonical issue: `gfx-rs/wgpu#8896`  
External contact authorized: `false`  
External contact made: `none`

## Question

Is canonical issue #8896 still current in either direction, or has Naga gained support since the January 2026 report?

## Answer

The report is stale against the controlled current WGPU/Naga source. Current Naga accepts both WGSL shape-changing bitcasts covered by the issue family:

```wgsl
bitcast<u32>(value: vec2<f16>)
bitcast<vec2<f16>>(value: u32)
```

No product patch is needed on the tested head.

## Exact controlled identities

```text
repository: teamleaderleo/wgpu
base branch: trunk
base commit: 2eddc8c7b2fedd4267f5004745a8bc42974e17a0
probe branch: fieldwork/naga-f16-bitcast-probe
probe head: b39e1822d3317e1b2ab41108211adf048314fa7d
internal draft PR: teamleaderleo/wgpu#4
focused run: 30752907389
focused job: 91509997426
focused conclusion: success
artifact: 8835144866
artifact digest: sha256:b507a9437f6f67de315317c79f4301b830388afd0072d66fcc5431a5615c8778
```

The runner checked out a generated merge with repository head recorded in the receipt as:

```text
825261dada66abdca4aafbc978b806a06c01cafc
```

Source identities retained by the probe:

```text
naga-cli blob: 5d5383b217f3dd4574e34b0ae735ccbda5dd55ed
validator blob: 18188200e38db828e247299317fd6dc70a5a5649
IR blob: e30c9f1bc5d38e59d7c3883f4962c263e65b24a0
rustc: 1.93.1
cargo: 1.93.1
naga binary SHA-256: 9206fc6b43f4dcd9681ec34b055c26f86a35cf46989b6bf43335b0c53755326c
```

## Exact capability matrix

```text
scalar-control   status 0   accepted
vec-to-scalar    status 0   accepted
scalar-to-vec    status 0   accepted
```

Every stdout file contained `Validation successful`. Every stderr file was empty.

The uploaded output digests were identical for the three successful cases:

```text
stdout SHA-256: 090e6f3602fcf35219e94c59dad7da0af1b4b0d1f0b44dbef3b37637b5129023
stderr SHA-256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

## Repository controls

On the same probe head, the ordinary fork workflows also completed successfully:

- Shaders;
- Publish;
- Lazy;
- Docs;
- cargo-generate;
- CTS;
- CI.

The focused probe therefore did not pass by bypassing a generally broken branch.

## Earlier harness correction

Initial run `30752645663` failed only because the first probe encoded the issue's historical rejection as an expected outcome. It had already proved `vec2<f16> → u32` was accepted, then stopped before the reverse case. Commit `b39e1822d3317e1b2ab41108211adf048314fa7d` converted the script to a neutral capability matrix, and run `30752907389` completed all cases.

Owner of the first red result: stale probe expectation, not Naga source.

## Decision

Retire this investigation as a current negative result. Preserve the exact receipt because it prevents an unnecessary broad `Expression::As` refactor and documents that both directions work on the tested source.

Do not contact canonical upstream merely to report that the issue appears stale without explicit authorization.

## Cleanup

The runner uploaded the exact receipt and removed its temporary fixture directory. No GPU, driver, device, credential, service, or persistent external state was used.
