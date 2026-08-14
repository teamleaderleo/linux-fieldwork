# FEX Thunk Lifetime Decision Brief — 2026-08-14

Status: internal Fieldwork decision brief. No upstream contact is authorized by this document.

## Recommendation

| Question | Recommendation | Reason |
| --- | --- | --- |
| What should contain the current unload hazard with the smallest review surface? | Selective whole-wrapper `DF_1_NODELETE` for affected generated shared guest thunks. | It preserves every wrapper-local executable reference and already has exact mapping/footprint evidence. |
| How should FEX preserve normal public-wrapper unload long term? | Generate a per-library process-resident bridge directly from thunkgen analysis. | Vulkan, GL, and DRM evidence now covers retained indirect calls, direct callbacks, moved reload, and generator-discovered nested callbacks. |
| How should future CustomIR dispatch stop reaching retired guest mappings? | Make retirement index/evict CustomIR or synthetic mapped blocks across all relevant thread caches. | The stale holder-to-target case is independently reproduced; exact retirement repairs future rebinding. |
| How should retained application callbacks survive owner teardown races? | Stable descriptor/trampoline identity, revoke new entries, then drain active executions before reclaiming target/state. | A deterministic full-FEX race changed from exit 139 to exit 0 only when active execution was drained. |
| Should identical callback signatures be deduplicated globally across thunk libraries now? | Defer global dedup. Start per library. | Per-library bridges are proven and keep annotations/custom semantics locally auditable. The footprint benefit of global dedup has not been measured. |
| Should native-first Vulkan proc routing or Vulkan allocator callback semantics be folded into this change? | Keep them as separate findings/proposals. | They are routing and semantic-marshalling problems, respectively, and can consume bridge primitives later. |

## What changed the long-term recommendation

The resident bridge began as a plausible Vulkan-specific experiment. It now has several independent pieces of evidence:

1. **Vulkan retained PFNs:** wrapper close and forced moved reload leave the resident invoker usable.
2. **Vulkan host-to-guest callbacks:** callback unpackers remain callable after wrapper unmap.
3. **GL:** retained indirect calls and GLX callbacks survive close/moved reload with the public wrapper unloadable.
4. **DRM nested callbacks:** thunkgen-derived callback-member conversion produced three unique callback signatures, delivered the real guest callback, and kept only the private bridge resident.
5. **Direct thunkgen output:** the bridge can be emitted from generator analysis itself. The production concept no longer depends on parsing or patching emitted C++.

That crosses the threshold for treating the resident bridge as a general thunk-generator design target instead of a Vulkan-only cleanup.

## Evidence ladder

### Immediate containment

Whole-wrapper `NODELETE` keeps the affected guest wrapper mapped after logical close. Exact mapping accounting on the Vulkan experiment matched the remaining wrapper mapping footprint. This is the strongest low-risk containment because it avoids needing a perfect escape analysis before the crash class is contained.

### Unload-preserving bridge

The direct Vulkan thunkgen bridge proof is:

- branch `diagnostic/thunkgen-resident-bridge-output-20260814`;
- head `7d63f276ecd2c1030afdce3b359fb976c50f7274`;
- run `31783988882`;
- job `94715684246`;
- artifact `real-vulkan-direct-thunkgen-bridge-31783988882`, id `9212870738`;
- artifact SHA256 `ec63a6031f8a8e18fad44894be983b924f57a54791b3a4c3f5e89f758c996443`.

The bridge contained callback/signature machinery and omitted ordinary public API packers. The wrapper depended on the bridge, the wrapper remained unloadable, the bridge carried `NODELETE`, and retained PFN use survived close/reload/moved reload.

### Generated nested callbacks

The DRM branch `ci/agent-b-drm-nested-resident-bridge-20260814` completed run `31782481709` successfully. Its generated nested callback conversion produced three unique bridge callback signatures. The runtime matrix was:

- native: 0;
- pristine FEX reference: 132;
- generated local-unpacker reference: 0;
- generated resident-unpacker candidate: 0.

The candidate delivered the real DRM guest callback with expected values. ELF inspection kept `libdrm-guest.so` unloadable, made it depend on `libfex-drm-bridge.so`, and placed `NODELETE` on the bridge.

### Future dispatch retirement

CustomIR guest targets can evade the ordinary guest-code-range index, allowing compiled holders to retain stale H→T relationships after mapping retirement. Exact mapped-block retirement and exact all-thread cache eviction repair future rebinding. This is a FEX retirement correctness issue independent of bridge residency.

### In-flight application callbacks

A deterministic full-FEX callback race proved the point where invalidation stops helping: once an invocation has selected a reclaimable application target, revoking future entries cannot retract that execution. The descriptor-only path exited 139; descriptor plus active-execution drain exited 0.

That result makes quiescence part of any callback ownership design that permits target/state reclamation while native callers can race teardown.

## Current implementation boundary

### Put in the resident bridge

- signature-derived indirect guest callers;
- generated host-to-guest callback unpackers;
- generated unpackers used by nested callback-bearing aggregates;
- escaping generated executable helpers whose lifetime belongs to the thunk family;
- explicit custom bridge seams for libraries such as Wayland when required.

### Keep in the unloadable wrapper

- public API packers and exports;
- wrapper-local data/code whose address cannot escape;
- normal wrapper constructor/load behavior;
- API-facing glue that follows the wrapper generation.

### Handle through callback ownership

- application callback target;
- application user data;
- registration/revocation state;
- active-execution accounting or equivalent epoch mechanism;
- teardown rollback if owner retirement fails.

### Keep as separate semantic work

- Vulkan native-first proc-address routing;
- `VkAllocationCallbacks` ownership/marshalling/suppression;
- other stateful helper semantics that cannot be derived from a function signature alone.

## Packaging path

The existing FEX guest-thunk CMake flow already creates each guest shared library and installs 64-bit products to `${DATA_DIRECTORY}/GuestThunks/` and 32-bit products to `GuestThunks_32/`. It also supports private target dependencies between guest thunk libraries.

The direct production path is therefore small in concept:

1. thunkgen emits ordinary guest and bridge outputs from one interface analysis;
2. CMake builds `${NAME}-guest` and `${NAME}-guest-bridge`;
3. the wrapper privately links the bridge, producing `DT_NEEDED`;
4. only the bridge receives `NODELETE`;
5. both install into the normal bitness-specific GuestThunks directory.

The remaining packaging proof is a production-layout install/rootfs smoke test showing that the private bridge is discovered exactly where packaged FEX expects it.

## CUDA status

The latest CUDA-derived resident-bridge workflow, run `31786582378` at head `2dae03d1bd5038a5d3baa4dbc37145c7383f9782`, completed the generator callback-member step, built FEX/local CUDA thunk output, and built the derived resident CUDA bridge. It then failed while preparing the local/resident amd64 rootfs images, so the moved-reload runtime matrix was skipped.

Treat CUDA as pending runtime coverage. The failure currently identifies a harness/rootfs boundary, not an architectural result.

## Evidence limits

The exact historical Apple M5 teardown failure still lacks a direct exact-stack trace from this investigation. Exact FEX-2608 Ubuntu/Fedora/X11 `vulkaninfo` probes in the available hosted environment did not reproduce it.

The executable-lifetime mechanism itself is separately demonstrated through deliberately retained executable references, physical wrapper unmap, moved reload, generated nested callbacks, CustomIR retirement, and a deterministic callback teardown race.

## What would change the recommendation

### Replace selective `NODELETE` as immediate containment if

- a smaller fix demonstrates the same escape coverage across affected thunk families with equally strong mapping and runtime evidence;
- whole-wrapper residency has unacceptable measured memory cost in real workloads.

### Replace per-library resident bridges as the long-term target if

- production loader namespaces make bridge identity/visibility unreliable;
- installed private dependency discovery cannot be made deterministic;
- 32-bit guest generation exposes incompatible ABI behavior;
- real multi-library footprint measurements show a large enough cost to justify a shared process bridge immediately;
- cross-library annotation collisions prove that the proposed adapter identity cannot be made safe.

### Weaken the callback drain requirement if

- FEX can prove by ownership protocol that reclamation only occurs after the native side has ceased all possible callback entry;
- the target is itself process-resident and therefore no reclaimable application code/state remains behind the adapter.

## Next experiments with decision value

1. Finish the CUDA installed-rootfs/moved-reload matrix.
2. Run production-layout install/package smoke tests for a generated bridge through the normal GuestThunks path.
3. Exercise `LM_ID_NEWLM` with the generated bridge and document namespace identity explicitly.
4. Run a moved-owner DRM callback case with revocation/drain, because it tests application callback ownership instead of immutable signature adapters.
5. Measure resident bytes and duplicate signature counts across a combined Vulkan+GL+DRM process.
6. Validate 32-bit thunkgen bridge output for a supported callback-bearing thunk family.

Everything else can wait behind those because these are the probes most likely to alter the current decision.