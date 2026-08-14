# FEX human rewrite queue — 2026-08-14

Status: internal handoff aid. This file marks which findings are stable enough for a human to independently re-derive and rewrite, and which still contain meaningful design choices. It is not an upstream submission queue.

## Classification

Use three buckets:

- **DETERMINATE FIX** — the bug and local invariant narrow the implementation enough that there is little meaningful product-design freedom. Human work is mainly understanding, independently re-deriving, writing the smallest fix, and choosing the cleanest regression.
- **BOUNDED DESIGN CHOICE** — the bug/invariant is clear, but there are multiple reasonable implementation techniques or policy choices that maintainers may prefer differently.
- **RESEARCH — DO NOT REWRITE YET** — evidence is useful, but product ownership or policy is still moving enough that a human rewrite would likely be wasted effort.

## Rewrite now

### A. Thunkgen const-pointee repack

**Class: DETERMINATE FIX**

Branch reference: `teamleaderleo/FEX:linux-fieldwork/thunkgen-preserve-const-repack`

Stable invariant:

> A generated wrapper for `const T*` may convert the pointed-to value for the host call, but wrapper teardown must not copy converted host state back into caller-owned const guest input.

Why this is nearly forced:

- thunkgen currently strips pointee constness before selecting `repack_wrapper`;
- `repack_wrapper` uses pointee constness to decide whether exit copyback is permitted;
- preserving the original type restores the semantics already expressed by the API declaration;
- the targeted generator regression and Vulkan allocator runtime discriminator both pass.

Human rewrite request:

1. read `repack_wrapper` entry/exit behavior;
2. reproduce why `const T*` becomes writable today;
3. independently write the minimal generator correction;
4. add the smallest semantic regression that proves const qualification survives generation;
5. keep Vulkan allocator evidence as causal motivation, not as Vulkan-specific implementation logic.

Expected rewrite size: small.

### B. Vulkan dynamic callback proc routing

**Class: DETERMINATE FIX, split into two claims**

Branch reference: `teamleaderleo/FEX:fix/vulkan-callback-proc-routing`

Stable invariants:

1. A dynamically queried Vulkan function with an existing callback-safe FEX custom host implementation must reach that implementation rather than expose the native ARM callback-taking entrypoint to the x86 guest.
2. FEX must not report a Vulkan command as available when native GIPA/GDPA rejects it for the requested scope.

The exact coding details can vary, but the behavioral obligations are tightly constrained by native Vulkan semantics and existing FEX custom wrappers.

Human rewrite request:

1. independently inventory `custom_host_impl` versus `LookupCustomVulkanFunction()`;
2. reproduce direct-vs-GIPA behavior for debug-report/debug-utils;
3. write the smallest routing correction;
4. separately derive native-first availability handling, including GIPA/GDPA self-query behavior;
5. decide whether the inventory-sync prevention test should accompany the fix or follow separately.

Do not combine with instance-pNext handling or thunk lifetime.

### C. MREMAP destination translation invalidation

**Class: DETERMINATE FIX, pending one clean candidate-local gate**

Branch reference: `teamleaderleo/FEX:candidate/fex2608-mremap-destination-codecache`

Stable invariant:

> When `mremap` places/replaces executable bytes at a destination address, translated code cached for the old contents of that destination must be invalidated before execution continues there.

The diagnostic split already shows stale destination translation survives `MREMAP_FIXED` replacement until explicitly invalidated. The candidate adds destination invalidation beside existing source invalidation.

Human rewrite request after the final clean A/B lands:

1. read current `mremap` invalidation logic;
2. independently reproduce source-vs-destination cache behavior;
3. write the minimal destination invalidation correction;
4. explicitly leave owner-claim/generation retirement out of this patch.

## Rewrite after one design decision

### D. Vulkan `vkCreateInstance` callback-bearing pNext handling

**Class: BOUNDED DESIGN CHOICE**

Branch reference: `teamleaderleo/FEX:fix/vulkan-instance-pnext-callback-restoration`

Stable bugs:

- debug-utils callback-bearing instance-create pNext nodes are not covered by the existing suppression policy and can reach native callback invocation;
- the existing splice can mutate caller-visible pNext links.

Stable behavioral requirement:

> Under the current suppression policy, callback-bearing temporary instance-create nodes must not be allowed to invoke guest callbacks through native ARM code, and guest-visible input must be unchanged when the call returns.

Open implementation choice:

- temporarily splice and restore links;
- construct a copied/filtered chain;
- another maintainable representation preserving input immutability.

Human rewrite request:

1. confirm Vulkan pNext lifetime/ownership expectations;
2. compare splice+restore against copy/filter in complexity, allocation, exception/early-return safety, and project style;
3. choose the implementation you can defend;
4. retain consecutive callback-node and read-only/input-integrity regressions.

## Read architecture now; rewrite later

### E. Per-library resident guest companions

**Class: BOUNDED DESIGN CHOICE, strongly converged invariant**

Clean source material currently exists for Vulkan/CUDA/Wayland and a clean GL tranche.

Stable invariant:

> Guest executable helpers whose addresses intentionally escape the lifetime of an ordinary guest thunk wrapper need executable lifetime at least as long as the state that retains them.

Current preferred policy:

- ordinary public wrapper remains unloadable;
- only escaped executable helper families move into a small library-local companion;
- companion is process-resident (`DF_1_NODELETE`);
- generated caller and callback-unpacker roles are emitted directly by thunkgen;
- custom semantic helpers remain library-owned escape points.

Why not request a full human rewrite yet:

- the design is converging but still absorbing GL/DRM/32-bit/custom cases;
- source tranches are still moving;
- naming/API/build-helper details are legitimate maintainer design territory.

Human task for now: learn the invariant, generator role split (`needs_caller` / `needs_unpacker`), ELF ownership boundary, and packaging model. Defer a clean-room implementation until the source delta stops changing materially.

### F. Selective whole-wrapper NODELETE

**Class: BOUNDED POLICY / CONTAINMENT**

This remains a valid and simple containment/reference configuration. It is no longer the preferred unload-preserving architecture when escaped executable code can be isolated in a resident companion.

Human rewrite only if we intentionally want to propose the containment policy itself. Otherwise keep it as:

- known-good workaround;
- regression/reference arm;
- fallback for libraries not yet split safely.

## Do not rewrite yet

### G. Application callback generation leases

**Class: RESEARCH — DO NOT REWRITE YET**

Strong evidence now exists, including a real libdrm retained callback with a resident generated unpacker and an unloadable application callback target. The product identity model is still open: VMA OwnerID versus load-generation identity/dependency sets, multi-callback aggregation, and broader destructive mapping operations.

### H. H->T owner-generation / generalized VM lifetime

**Class: RESEARCH — DO NOT REWRITE YET**

Keep reducing into bounded obligations. The mremap destination-code-cache bug has already split out successfully; other owner-generation and in-flight transition obligations should reach the same level of isolation before human implementation work begins.

## Practical rewrite order

1. const-pointee repack;
2. Vulkan proc-address callback routing / availability;
3. Vulkan instance pNext handling after choosing splice-vs-copy policy;
4. MREMAP destination invalidation after its final clean A/B;
5. architecture study of resident companions;
6. only later, if the implementation settles, independently design/write the resident-companion change.

The purpose of this queue is to keep clear correctness patches from waiting behind deeper design research while also preventing a human from spending time rewriting code whose ownership model is still changing.
