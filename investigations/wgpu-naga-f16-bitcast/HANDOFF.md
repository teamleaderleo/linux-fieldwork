# Handoff — WGPU/Naga f16 bitcast investigation

Handoff date: 2026-08-02  
State: `ACTIVE — CURRENT CAPABILITY RERUN QUEUED`  
External contact authorized: `false`  
External contact made: `none`

## Exact stopping point

```text
controlled repo: teamleaderleo/wgpu
base branch: trunk
base commit: 2eddc8c7b2fedd4267f5004745a8bc42974e17a0
probe branch: fieldwork/naga-f16-bitcast-probe
current probe head: b39e1822d3317e1b2ab41108211adf048314fa7d
internal draft PR: #4
current focused run: 30752907389
current run state: queued
```

## First run and classification

Initial probe head:

```text
91c59563534f6f239e6b35ce216ff5fca570e299
run: 30752645663
job: 91509299657
conclusion: failure
artifact: 8834957333
artifact digest: sha256:aa8fb7e33a743b70026e709f8ed2167ba20351eba0ee1035435e73fe6d6c8da9
```

Setup, Rust toolchain, cache, shell syntax, and locked `naga-cli` build all passed. The normal repository Shaders workflow also passed.

The focused job failed because the probe encoded the canonical issue's January behavior as an expected failure. The artifact proved current Naga now accepts the originally reported direction:

```text
scalar-control   status 0   accepted
vec-to-scalar    status 0   accepted
```

Both stdout files contained `Validation successful`; stderr was empty. The script stopped before executing `u32 → vec2<f16>` because its stale expectation required the second case to fail.

Owner: probe classifier / stale issue assumption, not repository source or build.

## Repair

Commit `b39e1822d3317e1b2ab41108211adf048314fa7d` converts the script into a neutral capability matrix:

- all three cases execute before classification;
- scalar control must succeed;
- f16 cases are recorded as `accepted`, `unable-to-cast`, or `unexpected-failure`;
- only an unexpected failure makes the probe red;
- exact outputs and identities remain retained.

## First incomplete step

Read focused run `30752907389` and retain its artifact. The decisive unknown is the reverse direction:

```text
u32 → vec2<f16>
```

If both f16 directions are accepted, retire canonical issue #8896 as stale in the internal record and keep the controlled branch as closeout evidence. If only the reverse direction fails, narrow the investigation to that exact asymmetry before any implementation work.

## Next safe actions

1. retain run `30752907389` logs and artifact ID/digest;
2. record all three statuses and diagnostics;
3. compare current behavior with the exact canonical issue reproducer;
4. locate the source transition only after the current capability is known;
5. close the internal fork PR if the issue is fully stale;
6. otherwise map only the still-failing direction;
7. keep canonical upstream contact at zero until explicit authorization.

## Cleanup state

The first runner completed and uploaded its partial artifact. The probe temporary directory was removed through its trap. No GPU, driver, device, credential, or persistent external state was used.
