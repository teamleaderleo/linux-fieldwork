# Selective guest-thunk NODELETE scope audit

## Question

If ELF `DF_1_NODELETE` is used as the narrow guest-wrapper lifetime repair, which FEX-2608 guest thunk wrappers have source-level evidence that they publish executable guest addresses into FEX/native state whose lifetime can exceed an ordinary application `dlclose`?

Exact product revision audited: FEX-2608 `e869aa644a16e4332cdc15c1ea0b4d13d482385d`.

This note is intentionally narrower than the generic arbitrary-guest-target callback problem. `NODELETE` keeps the wrapper itself resident; it does not revoke or lifetime-manage an unrelated guest DSO used as a callback target.

## Strong NODELETE candidates

### Vulkan

`ThunkLibs/libvulkan/Guest.cpp` has both relevant bridge directions.

Dynamic Vulkan proc lookup links a native host function address to a generated guest `CallHostFunction<...>` entrypoint. The generated target is executable code inside `libvulkan-guest.so`. FEX's CustomIR bridge can therefore retain an executable dependency on the wrapper after the application's loader reference is dropped.

Vulkan initialization also publishes host-callable X11 helper trampolines. Their `CallbackUnpack<...>::Unpack` entrypoints are template instantiations inside the Vulkan guest wrapper. Even when the ultimate X11 guest target remains mapped, unloading the Vulkan wrapper can remove the unpacker that FEX's host trampoline still names.

Conclusion: **NODELETE justified.**

### GL

`ThunkLibs/libGL/libGL_Guest.cpp` implements `glXGetProcAddress` by obtaining a native function pointer and calling `LinkAddressToFunction(native_pointer, guest_invoker)`. `guest_invoker` comes from `GetCallerForHostFunction`, i.e. a `CallHostFunction<...>` instantiation in `libGL-guest.so`.

Its `OnInit()` also publishes guest malloc/X11 targets together with `CallbackUnpack` entrypoints owned by the GL guest wrapper.

Conclusion: **NODELETE justified.**

### CUDA

`ThunkLibs/libcuda/libcuda_Guest.cpp` implements `cuGetProcAddress_v2`; `MakeGuestCallable()` uses `LinkAddressToFunction()` to associate a native CUDA function pointer with a wrapper-owned guest `CallHostFunction<...>` invoker.

Conclusion: **NODELETE justified.**

### Wayland client

`ThunkLibs/libwayland-client/Guest.cpp` converts guest listener functions into native-callable host trampolines through `AllocateHostTrampolineForGuestFunction`. The helper supplies a wrapper-owned `CallbackUnpack<...>::Unpack` entrypoint, and `wl_proxy_add_listener` stores the resulting native callback table in the host-side Wayland proxy until the listener is replaced or the proxy is destroyed.

That is an explicit lifetime longer than the call which creates the trampoline and can exceed an application's independent loader reference to the thunk wrapper.

Conclusion: **NODELETE justified.**

## Why EGL is not independently required by this rule

FEX-2608's `ThunkLibs/libEGL/libEGL_Guest.cpp` implements `eglGetProcAddress` by forwarding directly to `glXGetProcAddress`.

The dynamic executable bridge created for such a lookup is therefore owned by the GL thunk path, not by an EGL-local `CallHostFunction` target. Keeping GL resident protects this specific dependency; marking EGL NODELETE as well is not justified by the get-proc path alone.

Conclusion: **no independent NODELETE requirement found for this wrapper-owned-address rule.**

## Why DRM stays a separate issue

The FEX-2608 DRM interface passes `drmEventContext` as compatible layout and exposes `drmHandleEvent`. That structure contains application callback pointers. This raises a callback-conversion/lifetime question, and there is separate Fieldwork/FEX research for it.

However, the DRM guest wrapper does not show the same custom pattern as Vulkan/GL/Wayland where it explicitly publishes a wrapper-owned `CallbackUnpack` entrypoint or dynamic `CallHostFunction` invoker into longer-lived native state.

Adding NODELETE to DRM would therefore conflate two problems and could hide a callback-marshalling defect without repairing it.

Conclusion: **do not add DRM solely on the evidence used for this policy. Audit/fix its callback conversion separately.**

## asound and VDSO

The FEX-2608 asound guest source is essentially generated thunks plus `LOAD_LIB(libasound)`. Its interface includes dynamic-loading functions and some unsupported/stubbed callback APIs, but this audit found no custom wrapper-owned executable bridge comparable to Vulkan, GL, CUDA, or Wayland.

VDSO is special-purpose thunk machinery rather than a normal dynamically selected graphics/compute wrapper, and no comparable published wrapper-owned bridge was identified here.

Conclusion: **no NODELETE requirement established by this audit.**

## Result

The source-justified selective set at FEX-2608 is:

```text
NODELETE: vulkan, GL, cuda, wayland-client
normal:   EGL, drm, asound, VDSO
```

This matches the independently exercised selective build policy in the owned FEX research fork.

## Boundary of the repair

This policy solves the narrow class where FEX/native bridge state depends on executable code owned by the guest thunk wrapper itself. It does **not** solve the generic case where a retained host trampoline points at an arbitrary guest callback target in another DSO that legitimately unloads.

That broader case still needs explicit owner identity, revocation/rebinding, and safe transition/quiescence semantics if real unload/reload support is required.