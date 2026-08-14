# Host/guest thunk lifetime asymmetry

## Finding

FEX-2608 already treats the host half of a thunk library as process-lifetime state, while the guest dynamic loader is allowed to physically unload and reload the guest wrapper.

The guest-side `LOAD_LIB` / `LOAD_LIB_INIT` constructor always invokes the built-in `fex:loadlib` thunk. `ThunkHandler_impl::LoadLib()` then `dlopen()`s `<name>-host.so`, resolves its export initializer, stores exported functions in the process-owned thunk registry, and records the name in `Libs`.

The returned host `dlopen()` handle is not retained for later close, and FEX-2608 has no symmetric host-thunk unload function.

Therefore a physical guest-wrapper close/reopen can do this:

```text
guest generation 1 constructor
  -> host dlopen reference +1
  -> host thunk/registry persists

guest wrapper physically unmaps
  -> host reference remains

guest generation 2 constructor
  -> host dlopen reference +1 again
  -> same process-owned host state remains
```

Repeated guest physical generations can consequently ratchet host loader references without creating a genuine symmetric host/guest generation model.

With `DF_1_NODELETE` on the shared guest wrapper, later logical reopen reuses the same physical guest object. Its constructor does not rerun, so the guest side stops repeatedly feeding new host `dlopen()` references into a host lifetime that FEX never unwinds.

This is a separate argument for process-resident guest thunks from the stale-code crash itself: NODELETE aligns both halves of the implementation with the lifetime contract FEX already implements.

## Guest teardown-state audit

A repository-wide code search under `ThunkLibs` at the reviewed tree found:

- zero explicit `__attribute__((destructor))` thunk-library hooks;
- zero `thread_local` declarations.

Reviewed handwritten guest wrappers likewise expose no symmetric FEX unload notification:

- ALSA: generated glue plus `LOAD_LIB(libasound)`;
- DRM: generated glue plus allocation/string ownership shims and `LOAD_LIB(libdrm)`;
- EGL: `eglGetProcAddress` delegates to GL, then `LOAD_LIB(libEGL)`;
- GL: generated proc-address invoker table plus one-time X11/malloc bridge initialization;
- CUDA: generated proc-address invoker table plus `LOAD_LIB(libcuda)`;
- Vulkan: generated proc-address invoker table plus one-time X11 bridge initialization;
- Wayland: one-time interface mirror initialization plus long-lived callback trampoline creation.

Implicit C++ static destructors still exist where static C++ objects are used, so NODELETE changes their finalization timing to process exit. The audit found no designed intermediate thunk-unload protocol that depends on those destructors running at an application `dlclose()`.

## Consequence

Intermediate physical guest-wrapper reclamation should not be assumed to be part of FEX's existing thunk API contract.

If a future compatibility test proves that a particular wrapper must reset constructor/static/TLS state on logical close/reopen, that library is a candidate for the resident-bridge-sidecar design. Until such a counterexample exists, generic shared-wrapper NODELETE is the simpler coherent lifetime policy.
