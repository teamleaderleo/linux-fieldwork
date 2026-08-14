# Common per-library guest bridge helper — final three-library validation — 2026-08-14

## Result

The research `add_guest_bridge(...)` helper has now passed the final shared revision across three distinct thunk-library packaging shapes on exact product source `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`.

The final helper revision:

- creates a library-local guest companion through the existing `add_guest_lib` machinery;
- keeps the ordinary guest wrapper unloadable;
- sets `DF_1_NODELETE` only on the companion;
- optionally depends on direct thunkgen bridge generation;
- links an already-created ordinary wrapper to the companion;
- propagates library-local include/dependency targets;
- adds wrapper `RUNPATH=$ORIGIN` so installed wrappers resolve companions beside themselves without relying on global loader paths.

It does **not** select bridge roles or infer escaped lifetime semantics.

## CUDA — generated caller + generated nested callback unpacker

Final shared-helper resident regression:

- workflow run `31793660072` — success;
- exact-product provenance gate passed;
- direct role-aware thunkgen output only; no text extractor;
- wrapper has no NODELETE;
- wrapper NEEDED `libfex-cuda-bridge.so`;
- wrapper RUNPATH includes `$ORIGIN`;
- bridge is NODELETE;
- generation-1 callback succeeds before unload;
- generation-1 wrapper physically unloads and its old mappings are reserved;
- generation 2 moves;
- generation 2 does not re-register the callback;
- retained callback reaches guest successfully;
- traced `GuestUnpacker` remains outside all retired wrapper mappings.

The local failure arm was already established on the same direct-generator mechanism: wrapper-owned unpacker lies in retired mappings and exits 139 after moved reload.

## Vulkan — generated dynamic PFN callers + fixed custom X11 unpackers

Final shared-helper workflow:

- run `31793272172` — success;
- exact-product provenance gate passed;
- wrapper has no NODELETE;
- wrapper NEEDED `libfex-vulkan-bridge.so`;
- wrapper RUNPATH includes `$ORIGIN`;
- bridge is NODELETE;
- real retained-PFN close probe exits 0 after physical wrapper unload;
- forced moved reload exits 0;
- generation 2 is observed;
- native PFN remains the same across reload;
- post-reload call returns successfully through the resident direct-generated caller.

The library-local companion also owns the three fixed X11 guest callback unpackers used by the Vulkan host thunk.

## Wayland — custom runtime-signature listener dispatcher

Final shared-helper workflow:

- run `31793198473` — success;
- exact-product provenance gate passed;
- full 41-signature 64-bit resident dispatcher is built through the common helper;
- wrapper has no NODELETE;
- wrapper NEEDED `libfex-wayland-client-bridge.so`;
- wrapper RUNPATH includes `$ORIGIN`;
- bridge is NODELETE;
- generation-1 callback value 41 succeeds;
- wrapper physically unloads;
- old mappings are reserved and generation 2 moves;
- generation 2 does not re-register the listener;
- generation-1 retained host trampoline delivers callback value 42 through the resident dispatcher;
- process exits 0.

## Packaging classes covered

These three consumers cover the helper modes required by the current proposal:

1. **generated-only bridge roles plus library-local type headers** — CUDA;
2. **generated roles plus custom fixed executable targets** — Vulkan;
3. **custom runtime-selected callback family without direct generated role dependency** — Wayland.

So the common helper is no longer a CMake sketch. Its target/dependency/NODELETE/$ORIGIN behavior has survived real lifetime regressions in every current packaging class.

## What remains outside the helper

The helper intentionally does not own:

- `needs_caller` / `needs_unpacker` analysis;
- callback-member semantics;
- library-specific escaped-target discovery;
- callback trampoline allocation policy;
- unload quiescence;
- native-PFN generation/alias ownership;
- companion retirement policy.

Those remain generator/runtime/library concerns.

## Source materialization gate

The next step is already running from the same exact-product diagnostic branch: apply the validated generator/helper/library transforms together, build all Vulkan/CUDA/Wayland host + guest targets in one workspace, verify the six wrapper/companion ELF boundaries, and only then push a clean source-only commit directly on top of `f3ab82a...` to:

`integration/per-library-resident-bridges-f3ab-20260814`

No diagnostic workflows or `LinuxFieldwork` files are intended to be part of that integration commit.
