# WGPU/Naga `vec2<f16> ↔ u32` bitcast investigation

State: `ACTIVE — EXECUTABLE BASELINE PROBE QUEUED`  
Canonical issue: `gfx-rs/wgpu#8896`  
External contact authorized: `false`  
External contact made: `none`

## Question

What exact Naga layers must change to support the WGSL-defined shape-changing bitcasts between one 32-bit scalar and two 16-bit float lanes, without admitting invalid conversions or breaking backend lowering?

## Reported behavior

The canonical issue reports that Naga rejects:

```wgsl
bitcast<u32>(value: vec2<f16>)
```

with `Unable to cast`, although WGSL permits the bit reinterpretation because both sides contain 32 bits. The reverse direction, `u32 → vec2<f16>`, belongs to the same capability.

## Exact controlled identities

```text
repository: teamleaderleo/wgpu
base branch: trunk
base commit: 2eddc8c7b2fedd4267f5004745a8bc42974e17a0
evidence branch: fieldwork/naga-f16-bitcast-probe
evidence head: 91c59563534f6f239e6b35ce216ff5fca570e299
internal draft PR: teamleaderleo/wgpu#4
focused run: 30752645663
run state at handoff: queued
```

The branch changes two evidence files and no product source:

- `contrib/fieldwork/naga_f16_bitcast_probe.sh`
- `.github/workflows/fieldwork-naga-f16-bitcast.yml`

## Probe contract

The probe builds the exact workspace `naga-cli` with the locked dependency graph and executes three shaders:

1. scalar `f32 → u32` bitcast must validate successfully;
2. `vec2<f16> → u32` must currently fail with `Unable to cast`;
3. `u32 → vec2<f16>` must currently fail with `Unable to cast`.

It retains:

- exact generated shaders;
- stdout and stderr for each case;
- status and output SHA-256 values;
- repository head;
- Naga CLI, validator, and IR Git blobs;
- Rust and Cargo versions;
- built Naga binary SHA-256.

The temporary fixture directory is removed through a trap.

## Why implementation is not selected yet

The current Naga IR represents `Expression::As` using a target scalar kind and an optional conversion width. That is enough for shape-preserving conversions and bitcasts, but it does not directly represent a target whose scalar kind and vector shape both differ from the source.

A prior contributor began changing the expression to carry a full target `Scalar` and an explicit conversion flag, then stopped because the change affects:

- WGSL and other frontends;
- validator legality rules;
- IR type resolution;
- WGSL, SPIR-V, MSL, HLSL, and GLSL lowering;
- serialization and diagnostics;
- distinctions between matrix conversion and bitcast legality.

The reporter later moved away from the operation because browser support and NaN behavior were problematic, but the canonical issue remains open and tagged as correctness across Naga layers.

## Next technical map

After the exact probe completes:

1. identify where WGSL parsing lowers `bitcast<T>` to `Expression::As`;
2. map validator checks in `naga/src/valid/expression.rs`;
3. map resolved type construction for `Expression::As`;
4. enumerate every backend match arm and whether its target language can express both directions;
5. inspect serialization compatibility and snapshot expectations;
6. decide whether a narrow special expression, a full target-type refactor, or explicit packing/unpacking lowering is the smallest coherent design.

## Compatibility controls required before source work

- scalar and shape-preserving bitcasts remain accepted;
- mismatched total bit widths remain rejected;
- matrices remain rejected for bitcast but keep existing conversion behavior;
- `vec2<f16> ↔ u32` round-trips through every supported backend that claims f16 support;
- NaN payload behavior is recorded rather than assumed;
- unsupported target backends fail explicitly instead of generating invalid source;
- serialized IR compatibility is reviewed.

## Cleanup

No local WGPU checkout was created because the runtime could not resolve `github.com`. The controlled runner will own build products and fixture cleanup. No GPU, driver, device, credential, or external state is required by the probe.

## Current decision

Retain as a medium investigation. Do not start a broad `Expression::As` refactor until the exact baseline receipt and complete backend map are durable.
