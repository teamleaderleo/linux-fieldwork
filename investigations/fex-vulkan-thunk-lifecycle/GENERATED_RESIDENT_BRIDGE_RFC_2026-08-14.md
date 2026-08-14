# RFC: Generated Resident Bridge for FEX Guest Thunks

Status: internal design proposal, 2026-08-14

Scope: generator/build/runtime design for the FEX fork. This document does not authorize upstream contact.

## Proposal

Extend thunkgen so one interface analysis can emit two guest-side products for a thunk library:

1. an ordinary unloadable public guest wrapper, such as `libvulkan.so.1` / `libvulkan-guest.so`;
2. a private process-resident bridge, such as `libfex-vulkan-bridge.so`.

The ordinary wrapper keeps API-facing packers and wrapper-local state. The bridge owns generated executable adapters whose addresses can escape wrapper lifetime.

Start with **one resident bridge per thunk library**. This policy matches the current evidence and keeps ABI annotations, custom seams, symbol visibility, and ownership review local to one thunk family. A later process-global bridge can deduplicate compatible adapters if measurements justify it.

## Why generator output is the correct boundary

The strongest early bridge experiments extracted or post-processed generated C++ to build a sidecar. That proved the lifetime model but left an awkward production path.

The later direct thunkgen experiment removed that weakness. A `-guest-bridge` output role was emitted from thunkgen analysis itself and produced a bridge containing the expected callback/signature machinery without ordinary public API packers. The Vulkan runtime matrix then used that directly generated bridge for retained PFNs, close/reload, and forced moved reload.

The generator already knows the information needed to classify most bridge entries:

- full function/callback signature;
- guest bitness;
- generator annotations;
- callback-bearing fields discovered inside aggregates;
- custom-host/custom-guest implementation tags;
- special per-library generator configuration.

That makes the generator the right place to emit stable bridge code and a deterministic adapter identity.

## Output roles

### Ordinary guest wrapper

The wrapper should contain:

- exported or private API packers (`fexfn_pack_*` and related API-facing entrypoints);
- constructor/load-library behavior associated with the public thunk wrapper;
- wrapper-local data whose lifetime follows the loaded public library;
- library-specific code that cannot escape and therefore benefits from normal unload behavior.

The wrapper should carry a normal dynamic dependency on its generated bridge and should remain free of `DF_1_NODELETE` once bridge coverage is complete for that thunk family.

### Resident bridge

The bridge should contain executable machinery whose identity belongs to FEX/generator ABI handling instead of a particular public-wrapper generation:

- indirect guest-call signature adapters/callers;
- host-to-guest callback unpackers;
- nested callback-member unpackers and their generated conversion helpers;
- stable bridge accessors used by wrapper code;
- special generated executable targets or metadata that can escape wrapper lifetime;
- explicit per-library custom callback seams when the library requires them.

The bridge should carry `DF_1_NODELETE` in the first implementation. The process-lifetime policy keeps bridge addresses stable through public-wrapper close/reopen and moved reload.

The bridge should avoid public API packers whose lifetime naturally follows the public wrapper.

## Role classification

Thunkgen can classify generated executable roles using these rules.

| Generated role | Lifetime placement |
| --- | --- |
| Indirect guest-call signature returned/stored outside wrapper | Resident bridge caller |
| Host-to-guest callback signature | Resident bridge unpacker |
| Callback-bearing aggregate member | Wrapper performs generated copy/repack; callback entry points come from resident bridge |
| Wrapper-local escaping executable helper | Per-library bridge helper/metadata |
| Wayland-style/custom callback table | Explicit custom resident allocation seam |
| Ordinary API entrypoint packer | Public wrapper |
| Pure wrapper-local helper with no escaping address | Public wrapper |

The classification should be inspectable in generated output and tests. Hidden inference that changes lifetime policy without a visible generated artifact will make review harder.

## Adapter identity

A resident adapter key must include every ABI-relevant property used by thunk generation. A textual C prototype alone is too weak.

At minimum, identity should account for:

- guest bitness;
- parameter and return ABI layout;
- calling convention where relevant;
- generator annotations that alter packing or invocation;
- callback direction/role;
- any custom implementation tag that changes behavior.

The first per-library implementation can avoid cross-library collision questions by keeping symbols private to each bridge. If global dedup is explored later, this identity definition becomes a hard compatibility contract.

## Application callback ownership stays separate

A resident callback unpacker stabilizes FEX-owned executable code. It does not own the application callback target, application user data, or application object whose lifetime controls the callback.

For native APIs that retain application callbacks beyond the initiating guest-to-host call, the runtime/library-specific layer needs a stable descriptor or trampoline with explicit state, for example:

- active target and user-data identity;
- revoked state;
- in-flight execution count or equivalent epoch/quiescence mechanism;
- synchronization for unregister/owner teardown;
- rollback path when the expected owner retirement operation fails.

The callback entry sequence should acquire execution ownership before dereferencing a reclaimable application target. Teardown should revoke new entries, wait for active executions to leave, then permit target/state reclamation.

This is intentionally outside pure signature-adapter generation. Thunkgen can generate the stable resident unpacker and helper calls, while the API/runtime layer supplies the ownership policy.

## Nested callback-bearing aggregates

DRM provides the first generator-derived proof for this class.

The generated conversion path should:

1. detect callback-bearing members during interface analysis;
2. copy the input aggregate when mutation of the guest object itself would be incorrect;
3. replace callback function-pointer fields in the copied aggregate with host trampolines backed by resident guest unpackers;
4. pass the converted aggregate to the native API;
5. preserve per-field callback semantics and user data;
6. generate repack/copy-back behavior where the API direction requires it.

The completed DRM experiment found four callback-bearing `drmEventContext` fields and reduced them to three unique callback signatures. The resident variant delivered the real guest callback and kept only the private bridge resident.

## Build and install integration

FEX already builds guest thunk libraries through `ThunkLibs/GuestLibs/CMakeLists.txt`:

- `generate(NAME SOURCE_FILE)` invokes thunkgen and records generated output;
- `add_guest_lib(NAME SONAME)` creates the guest shared library;
- 64-bit guest thunk targets are installed under `${DATA_DIRECTORY}/GuestThunks/`;
- 32-bit guest thunk targets are installed under `${DATA_DIRECTORY}/GuestThunks_32/`;
- ordinary guest libraries already use private target dependencies where needed, such as EGL linking to the GL guest target.

A production bridge integration can extend that path directly:

1. make `generate()` request both ordinary `-guest` output and resident `-guest-bridge` output when a library needs a bridge;
2. add a `${NAME}-guest-bridge` shared-library target from the bridge output plus a small bridge runtime source/template if required;
3. link `${NAME}-guest` privately against `${NAME}-guest-bridge` so the wrapper records a normal `DT_NEEDED` dependency;
4. apply `-z nodelete` / equivalent dynamic flag to the bridge target only;
5. install both targets into the same bitness-specific `GuestThunks` directory;
6. keep bridge symbols private except for the generated wrapper-to-bridge accessors needed by that thunk family.

This path avoids a second private deployment tree and lets existing guest-thunk packaging carry the sidecar naturally. Package/rootfs tests still need to verify loader discovery from the installed layout.

## Loader and namespace behavior

The design requires explicit namespace testing because loader namespaces can create more than one wrapper generation and can affect dependency identity.

Initial requirements:

- a public wrapper loaded, closed, and reopened in the same namespace must reuse the resident bridge identity;
- a forced moved wrapper reload must use the same bridge executable entries;
- `dlmopen(LM_ID_NEWLM, ...)` tests must determine whether bridge identity is intended to be namespace-local or process-wide under glibc semantics;
- a disposable namespace must never overwrite longer-lived callback/native state with executable addresses that disappear when that namespace dies.

The earlier “pin only the base namespace” idea failed the last requirement: a NEWLM instance could still publish callback state and disappear. The bridge policy therefore has to follow the actual escaping dependency graph, not a preferred loader namespace.

## Direct thunkgen proof

The direct Vulkan bridge experiment used:

- FEX branch: `diagnostic/thunkgen-resident-bridge-output-20260814`;
- head: `7d63f276ecd2c1030afdce3b359fb976c50f7274`;
- workflow run: `31783988882`;
- job: `94715684246`;
- artifact: `real-vulkan-direct-thunkgen-bridge-31783988882`;
- artifact id: `9212870738`;
- artifact SHA256: `ec63a6031f8a8e18fad44894be983b924f57a54791b3a4c3f5e89f758c996443`.

The generated bridge contained the expected callback/signature registration machinery (`MAKE_CALLBACK_THUNK`, `FOREACH_internal_SYMBOL`) and omitted ordinary `fexfn_pack_` API packers. ELF inspection showed an unloadable Vulkan wrapper with `DT_NEEDED` on the resident bridge, while the bridge carried `NODELETE`.

The runtime matrix completed with wrapper close, retained PFN call, reload, and forced moved reload while preserving the resident invoker identity.

## Cross-library evidence

The architecture is now demonstrated across multiple callback/adapter forms:

- Vulkan dynamic PFNs and Vulkan X11 callbacks;
- GL retained indirect calls and GLX callbacks;
- DRM generator-discovered nested callback members.

CUDA has reached successful generator and resident-variant build stages in the current probe, but its latest workflow failed during rootfs preparation before the moved-reload runtime matrix. Treat CUDA runtime coverage as pending.

## Test contract

Every thunk family converted to a resident bridge should carry tests for the relevant subset below.

### ELF and packaging

- public wrapper lacks `NODELETE`;
- bridge carries `NODELETE`;
- wrapper has `DT_NEEDED` on the bridge;
- installed guest-thunk directory contains both products;
- wrapper finds the private bridge from the production rootfs/package layout;
- exported bridge surface is limited to intended accessors.

### Lifetime

- wrapper mapping disappears after final `dlclose()`;
- bridge mapping remains;
- retained indirect function/caller still executes;
- host-to-guest callback still executes through the bridge;
- moved wrapper reload changes wrapper code address and preserves bridge address identity;
- repeated close/reload remains stable.

### Generator coverage

- direct callback parameters;
- nested callback-bearing structs;
- duplicate signatures within one library;
- custom callback tables or raw callback-address seams;
- signature annotations that affect ABI handling;
- 32-bit guest output where the thunk family supports it.

### Namespace

- base namespace close/reload;
- one or more `LM_ID_NEWLM` instances;
- publication of native callback state from a disposable namespace;
- bridge identity/visibility expectations documented from measured behavior.

### Application callback race

For APIs that retain application callbacks:

- revoke with no in-flight callback;
- revoke while callback is in flight;
- owner unmap/reload after drain;
- failed owner unmap with registration rollback;
- new wrapper generation using the correct current callback target.

### Footprint

Measure:

- resident bytes per thunk-family bridge;
- duplicate adapter count within each bridge;
- duplicate signatures across common combinations such as Vulkan+GL+DRM;
- incremental cost of per-library residency versus a hypothetical shared bridge.

These measurements decide whether global dedup deserves another design round.

## Rollout order

1. Vulkan: strongest indirect-call and callback lifetime evidence, plus direct thunkgen bridge proof.
2. GL: already has split/generated resident callback evidence and exercises related graphics callback paths.
3. DRM: validates nested callback-member generation and retained callback conversion.
4. CUDA: finish the current runtime harness and moved-reload receipt.
5. Wayland: audit custom callback table/raw-address handling and define its explicit resident seam.
6. Audit the remaining thunk libraries for escaping executable addresses before expanding the policy mechanically.

## Decision points left open

The first implementation can proceed while these remain explicit follow-ups:

- exact glibc namespace identity policy for a resident dependency;
- 32-bit bridge output validation;
- resident footprint under realistic multi-thunk workloads;
- symbol/versioning policy for installed private bridges;
- whether a later process-global bridge provides enough dedup benefit to justify a cross-library ABI identity contract;
- whether any signature-derived bridge code ever needs process-lifetime reclamation.

The current evidence supports per-library direct thunkgen bridges without requiring answers to those later optimization questions.