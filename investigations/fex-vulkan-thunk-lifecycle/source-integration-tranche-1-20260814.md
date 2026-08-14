# Source integration tranche 1 — per-library resident guest bridges — 2026-08-14

## Branch

`teamleaderleo/FEX:integration/per-library-resident-bridges-f3ab-20260814`

Base:

`f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`

The integration branch was produced by workflow run `31793881369` only after applying the validated transforms together and building the combined host/guest target set in one workspace.

## Clean-branch rule

The materializer stages only `ThunkLibs/**`, writes a source patch, resets to the exact product commit, applies that patch onto a fresh integration branch, and commits from there.

Therefore the integration branch does **not** carry the diagnostic workflows, synthetic endpoints, trace hooks, or `LinuxFieldwork` scripts used to establish causality.

Those remain on the diagnostic branches.

## Integrated generator work

The branch contains the direct resident-bridge generator seam:

- guest bridge definitions output;
- guest bridge accessor output;
- orthogonal `needs_caller` / `needs_unpacker` registration roles;
- canonical-signature role OR-ing;
- stable signature-hash-based bridge symbol identity;
- explicit function-pointer registration normalized to function prototype representation;
- typed wrapper helpers for resident callers and resident callback unpackers.

It also contains the generic `callback_member` capability required by CUDA nested callback structures, but deliberately does **not** include the separate DRM library annotation experiment in this first tranche.

## Integrated build helper

The source branch contains the common per-library `add_guest_bridge(...)` packaging helper.

The helper:

- creates a library-local guest companion through `add_guest_lib`;
- sets NODELETE only on the companion;
- links the ordinary wrapper to it;
- optionally depends on direct bridge generation;
- propagates library-specific dependency/include targets;
- gives the wrapper `$ORIGIN` lookup for its local companion.

It does not choose bridge roles or lifetime semantics.

## Integrated libraries

### Vulkan

The unloadable Vulkan wrapper uses direct generated resident PFN callers.

`libfex-vulkan-bridge.so` owns:

- direct generated PFN caller code;
- the fixed XSync callback unpacker;
- the fixed XGetVisualInfo callback unpacker;
- the fixed XDisplayString callback unpacker.

The real close/moved-reload PFN helper validation was green before materialization.

### CUDA

The unloadable CUDA wrapper uses direct generated bridge accessors.

`CUDA_HOST_NODE_PARAMS_st` callback field is handled by generated `callback_member` logic so the caller-owned structure is copied and its callback field receives a host trampoline whose concrete `GuestUnpacker` comes from `libfex-cuda-bridge.so`.

The isolated retained-registration-only moved-reload trace established:

- wrapper-local unpacker -> retired wrapper mapping -> exit 139;
- resident direct-generated unpacker -> outside retired mappings -> callback succeeds after moved reload.

### Wayland

The unloadable Wayland wrapper keeps protocol parsing, listener table memory, and proxy bookkeeping.

`libfex-wayland-client-bridge.so` owns the currently recognized 41-signature 64-bit listener-unpacker dispatcher.

The synchronous retained-registration-only moved-reload test established callback 41 before close and callback 42 after moved reload through the old retained host trampoline.

## Combined build gate

Before the source-only branch was pushed, the materializer configured one transformed tree and built:

Host/generator side:

- thunkgen;
- Vulkan host thunk;
- CUDA host thunk;
- Wayland client host thunk.

Guest side:

- Vulkan wrapper + companion;
- CUDA wrapper + companion;
- Wayland client wrapper + companion.

For each wrapper/companion pair it checked:

- wrapper is not NODELETE;
- wrapper NEEDED the local companion;
- wrapper RUNPATH contains `$ORIGIN`;
- companion is NODELETE.

This catches cross-library generator/helper/CMake interactions that the earlier isolated carriers could not.

## Deliberately not in tranche 1

- GL direct/helper conversion — runtime evidence exists, but direct-helper conversion is being validated separately before inclusion;
- DRM library callback annotations — generator capability exists, library integration remains a separate tranche;
- 32-bit Wayland host `wl_array` packer + resident unpacker compatibility;
- concurrent unload quiescence;
- PFN alias/generation ownership;
- companion retirement;
- separate Vulkan pNext const-memory work.

## Status

Tranche 1 is the first fork-local source branch where the resident-bridge proposal is represented as actual FEX source rather than workflow-time transforms, while preserving the clean exact-product provenance and keeping all causal instrumentation outside the source branch.
