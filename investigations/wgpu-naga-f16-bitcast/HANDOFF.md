# Handoff — WGPU/Naga f16 bitcast investigation

Handoff date: 2026-08-02  
State: `RETIRED — CURRENT NAGA ACCEPTS BOTH DIRECTIONS`  
External contact authorized: `false`  
External contact made: `none`

## Final controlled identity

```text
controlled repo: teamleaderleo/wgpu
base branch: trunk
base commit: 2eddc8c7b2fedd4267f5004745a8bc42974e17a0
probe branch: fieldwork/naga-f16-bitcast-probe
probe head: b39e1822d3317e1b2ab41108211adf048314fa7d
internal draft PR: #4
focused run: 30752907389
focused job: 91509997426
conclusion: success
artifact: 8835144866
artifact digest: sha256:b507a9437f6f67de315317c79f4301b830388afd0072d66fcc5431a5615c8778
```

## Final result

The exact receipt records:

```text
scalar-control   0   accepted
vec-to-scalar    0   accepted
scalar-to-vec    0   accepted
```

All three stdout files contain `Validation successful`. All three stderr files are empty.

The canonical issue's originally reported direction and its reverse both work on the tested current source. No Naga product implementation is selected or needed for this issue.

## Retained identities

```text
runner checkout head: 825261dada66abdca4aafbc978b806a06c01cafc
naga-cli blob: 5d5383b217f3dd4574e34b0ae735ccbda5dd55ed
validator blob: 18188200e38db828e247299317fd6dc70a5a5649
IR blob: e30c9f1bc5d38e59d7c3883f4962c263e65b24a0
naga binary SHA-256: 9206fc6b43f4dcd9681ec34b055c26f86a35cf46989b6bf43335b0c53755326c
stdout SHA-256: 090e6f3602fcf35219e94c59dad7da0af1b4b0d1f0b44dbef3b37637b5129023
empty stderr SHA-256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

Ordinary fork workflows Shaders, Publish, Lazy, Docs, cargo-generate, CTS, and CI also passed on the probe head.

## Earlier red run

Run `30752645663` failed because the probe assumed the issue's historical rejection was still current. It proved `vec2<f16> → u32` was accepted and stopped before the reverse case. The neutral matrix repaired the classifier, not Naga.

## Disposition

- internal investigation: retired;
- source patch: none;
- next technical step: none;
- useful retained result: current negative capability evidence;
- canonical upstream contact: still unauthorized and absent.

The internal WGPU evidence PR may be closed after this Fieldwork receipt is durable. Do not create an upstream comment merely to close the stale issue without explicit authorization.

## Cleanup state

The workflow completed, uploaded its receipt, and removed temporary shader fixtures. No GPU, driver, service, credential, device, or persistent external state remains.
