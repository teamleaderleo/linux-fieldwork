# Current direction checkpoint — 2026-08-14

The investigation has moved from a Vulkan-specific unload workaround to a narrower reusable rule:

> Keep the ordinary guest wrapper unloadable. Move only guest executable addresses that escape wrapper lifetime into a small process-resident companion owned by that thunk library.

Current demonstrated shapes:

- Vulkan: dynamic native PFN callers and persistent X11 callback unpackers.
- GL: dynamic PFN callers, X11 callback unpackers, and an ordinary wrapper-local allocator callback target that also escaped.
- CUDA: generated nested/deferred callback unpacker; direct FEX trampoline trace proves local `GuestUnpacker` lies in retired wrapper mappings while resident `GuestUnpacker` lies outside them and survives moved reload.
- DRM: generated nested callback-member conversion/execution.
- Wayland: custom protocol-signature listener family; revised synchronous retained-listener A/B is in progress.

Preferred generator path is direct thunkgen bridge output, not reverse-parsing the ordinary generated guest inl.

The generator must preserve bridge role (`needs_caller`, `needs_unpacker`) through canonical-signature deduplication. GL proved a caller-only signature must not automatically instantiate callback-unpacker machinery.

Whole-wrapper NODELETE remains a useful containment/reference configuration, not the preferred unload-preserving design.

Still separate from this bridge split:

- true concurrent unload quiescence/leases;
- native-PFN alias owner stacks and incompatible ABI collapse;
- explicit owner/generation/tombstone policy if bridge retirement is later required rather than process residence.
