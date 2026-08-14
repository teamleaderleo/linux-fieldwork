# Current direction checkpoint — 2026-08-14

The investigation has moved from a Vulkan-specific unload workaround to a narrower reusable rule:

> Keep the ordinary guest wrapper unloadable. Move only guest executable addresses that escape wrapper lifetime into a small process-resident companion owned by that thunk library.

Current demonstrated shapes:

- Vulkan: dynamic native PFN callers and persistent X11 callback unpackers.
- GL: dynamic PFN callers, X11 callback unpackers, and an ordinary wrapper-local allocator callback target that also escaped.
- CUDA: generated nested/deferred callback unpacker; isolated FEX trampoline trace proves the local `GuestUnpacker` lies in retired wrapper mappings while the resident `GuestUnpacker` lies outside them and survives moved reload with no callback re-registration.
- DRM: generated nested callback-member conversion/execution.
- Wayland: custom runtime protocol-signature listener family; synchronous retained-registration-only A/B passes, and the full currently recognized 41-signature 64-bit resident dispatcher preserves that moved-reload result.

Preferred generator path is direct thunkgen bridge output, not reverse-parsing the ordinary generated guest inl.

The direct generator role/accessor gate is green:

- GL: 736 caller-only signatures;
- Vulkan: 476 caller-only signatures;
- deterministic fixture: one unpacker-only signature and one canonical signature that merges callback + indirect registrations into caller+unpacker;
- bridge definitions and wrapper accessors agree by stable canonical-signature SHA-256 identity.

The next active gate is CUDA using these direct role-aware bridge/accessor outputs with **no text extractor**, while retaining the exact already-proven pre-close / physical unload / forced moved reload / no-reregister / `GuestUnpacker` ownership discriminator.

Whole-wrapper NODELETE remains a useful containment/reference configuration, not the preferred unload-preserving design. In the existing six-wrapper A/B it retained 2.5 MiB more RSS/PSS after close, 1.594 MiB more mapped thunk VA, and 31 more thunk mappings than stock unload behavior.

Still separate from this bridge split:

- true concurrent unload quiescence/leases;
- native-PFN alias owner stacks and incompatible ABI collapse;
- explicit owner/generation/tombstone policy if bridge retirement is later required rather than process residence;
- 32-bit Wayland `wl_array` callback relocation;
- the separate Vulkan pNext const-memory issue.
