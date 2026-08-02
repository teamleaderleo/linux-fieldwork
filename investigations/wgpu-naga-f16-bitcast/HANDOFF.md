# Handoff — WGPU/Naga f16 bitcast investigation

Handoff date: 2026-08-02  
State: `ACTIVE — WAITING FOR CONTROLLED PROBE`  
External contact authorized: `false`  
External contact made: `none`

## Exact stopping point

```text
controlled repo: teamleaderleo/wgpu
base branch: trunk
base commit: 2eddc8c7b2fedd4267f5004745a8bc42974e17a0
probe branch: fieldwork/naga-f16-bitcast-probe
probe head: 91c59563534f6f239e6b35ce216ff5fca570e299
internal draft PR: #4
focused run: 30752645663
focused run state: queued
```

Other repository workflows were also queued for the same head. The focused probe is the first authoritative result for this investigation.

## Implemented work

No product implementation has been selected or written.

The controlled branch adds an executable probe that:

- builds `naga-cli` from the exact workspace;
- validates a scalar `f32 → u32` bitcast control;
- records expected current rejection of `vec2<f16> → u32`;
- records expected current rejection of `u32 → vec2<f16>`;
- requires the rejection diagnostic to contain `Unable to cast`;
- retains source, binary, environment, status, and output identities;
- removes its temporary fixture directory.

## First incomplete step

Read run `30752645663`. If it fails before the product checks, classify setup, toolchain, build, WGSL fixture syntax, CLI invocation, or artifact retention separately.

If it succeeds, retain the artifact ID and digest, then map the complete `Expression::As` change surface.

## Known design boundary

The current IR stores target scalar kind and optional conversion width, not a complete target scalar/vector type. Supporting this case may require an IR representation change. Do not patch only the validator unless every frontend, type resolver, serializer, and backend can correctly represent and lower the newly admitted expression.

## Next safe actions

1. retain exact focused run logs and artifacts;
2. verify both failing cases reach the same validator owner;
3. enumerate all `Expression::As` constructors and match arms;
4. identify existing total-bit-width helpers;
5. add table-driven legality tests before changing the IR;
6. choose the smallest coherent representation;
7. run Naga workspace and backend snapshot tests on the exact candidate;
8. keep canonical upstream contact at zero until explicit authorization.

## Stop and reassess when

- canonical WGPU lands equivalent support;
- WGSL specification changes the operation;
- one or more supported backends cannot preserve the required bits;
- NaN payload behavior creates a cross-backend semantic mismatch;
- the necessary change is better split into an IR preparatory refactor and a separate feature patch.
