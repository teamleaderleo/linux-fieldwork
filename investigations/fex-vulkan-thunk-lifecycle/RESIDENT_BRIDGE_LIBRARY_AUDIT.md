# Resident bridge library audit

Date: 2026-08-14

## Purpose

Identify whether the successful Vulkan split-resident bridge is a Vulkan-specific workaround or a reusable thunk-library pattern.

The first non-Vulkan audit is enough to answer that question: current `libGL` has the same two escaped executable-address classes.

Reviewed source: `71afe476751deac24adabd1adb575fd2337b6e0a`.

## libGL dynamic host function pointers

`ThunkLibs/libGL/libGL_Guest.cpp` builds:

```cpp
const std::unordered_map<std::string_view, uintptr_t> HostPtrInvokers = std::invoke([]() {
#define PAIR(name, unused) Ret[#name] = reinterpret_cast<uintptr_t>(GetCallerForHostFunction(name));
  std::unordered_map<std::string_view, uintptr_t> Ret;
  FOREACH_internal_SYMBOL(PAIR);
  return Ret;
#undef PAIR
});
```

`glXGetProcAddress` obtains a native host function pointer and then does:

```cpp
LinkAddressToFunction((uintptr_t)Ret, TargetFuncIt->second);
```

So the same ownership relation exists as Vulkan:

```text
native H from host GL
    -> guest CallHostFunction<signature> adapter
         currently compiled into libGL guest wrapper
```

If the wrapper can physically unload while FEX retains H dispatch state, this is the same executable-lifetime class as the proven Vulkan defect.

## libGL fixed callback unpackers

`OnInit()` also publishes fixed wrapper-owned unpacker addresses:

```cpp
fexfn_pack_GL_SetGuestMalloc(
  (uintptr_t)malloc_wrapper,
  (uintptr_t)CallbackUnpack<decltype(malloc_wrapper)>::Unpack);

fexfn_pack_GL_SetGuestXSync(
  (uintptr_t)XSync,
  (uintptr_t)CallbackUnpack<decltype(XSync)>::Unpack);

fexfn_pack_GL_SetGuestXGetVisualInfo(
  (uintptr_t)XGetVisualInfo,
  (uintptr_t)CallbackUnpack<decltype(XGetVisualInfo)>::Unpack);

fexfn_pack_GL_SetGuestXDisplayString(
  (uintptr_t)XDisplayString,
  (uintptr_t)CallbackUnpack<decltype(XDisplayString)>::Unpack);
```

Again this matches Vulkan's X11 setup:

- actual callback targets belong to the main guest process/libX11 or another owner;
- fixed `CallbackUnpack<signature>::Unpack` glue is currently wrapper-owned;
- host-side state can retain the unpacker address beyond wrapper lifetime.

## Conclusion

The resident companion bridge is immediately applicable beyond Vulkan.

At minimum, a generalized generator/CMake mechanism should support:

```text
libGL guest wrapper (unloadable)
    glXGetProcAddress policy / wrapper state
    public generated wrappers
    registration

libfex-GL-bridge.so (resident)
    GetCallerForHostFunction-generated signature adapters
    CallbackUnpack fixed unpackers for malloc/X11 callbacks
```

This is the same ownership split already proven for Vulkan.

## Audit priority

1. `libGL` — direct pattern match; first non-Vulkan runtime candidate.
2. Other wrappers using `GetCallerForHostFunction` for dynamically returned native pointers.
3. Other wrappers passing fixed `CallbackUnpack` addresses or guest callbacks to host code that may retain them.
4. Wrappers with neither pattern need no resident bridge merely because they are thunk libraries.

The goal is **selective escaped-glue residency**, not blanket companion DSOs for every wrapper.

## Implementation implication

This strengthens the case for generator-native metadata rather than source-specific post-processing:

- thunkgen already knows which generated API signatures have `GetCallerForHostFunction` adapters;
- thunkgen already knows unique callback/function-pointer signatures;
- GuestLibs centrally owns wrapper construction.

A generic companion mechanism can therefore be opt-in based on generated escaping signatures, with Vulkan and GL as the first concrete users.

No upstream FEX interaction was made. All source/code here is research-only on owned surfaces.