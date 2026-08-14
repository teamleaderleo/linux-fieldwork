# Thunkgen const-repack corruption root cause — 2026-08-14

## Finding

The Vulkan allocator destroy failure is caused earlier, during the successful create call.

For a repackable pointer parameter such as:

```cpp
const VkAllocationCallbacks* pAllocator
```

host-side thunk generation currently calls a helper named `get_type_name_with_nonconst_pointee`. That helper removes top-level qualifiers and, for pointer types, explicitly strips `const` from the pointee before emitting the `repack_wrapper` template argument.

Conceptually, generated code becomes:

```cpp
auto a_N = make_repack_wrapper<VkAllocationCallbacks*>(args->a_N);
```

instead of preserving the source type:

```cpp
auto a_N = make_repack_wrapper<const VkAllocationCallbacks*>(args->a_N);
```

`repack_wrapper` itself already uses non-const internal host storage via:

```cpp
using PointeeT = std::remove_cv_t<std::remove_pointer_t<T>>;
```

so stripping the public pointee constness in thunkgen is unnecessary for storage.

More importantly, `repack_wrapper::~repack_wrapper()` uses the template type `T` to decide whether automatic exit repacking may write back into guest memory:

```cpp
if constexpr (!std::is_const_v<std::remove_pointer_t<T>>) {
  ...
  *orig_arg.get_pointer() = to_guest(*data);
}
```

Because thunkgen changed `const VkAllocationCallbacks*` into `VkAllocationCallbacks*`, this guard sees a mutable pointee and performs an exit writeback into application-owned memory that arrived through a const pointer.

`VkAllocationCallbacks` has all callback-bearing members marked `custom_repack` in the experiment. Its experimental `fex_custom_repack_exit` returns `false`, asking generic exit conversion to proceed. Generic `to_guest` has no automatic conversion for those custom callback members, so the writeback produces zero callback fields.

This exactly explains the runtime sequence already observed:

1. `vkCreateBuffer(..., &cb, ...)` enters custom repack with the real guest allocator callback addresses.
2. Allocation callback executes successfully through host trampolines.
3. On thunk return, the generated wrapper treats the const pointee as mutable and exit-repacks into the original guest `VkAllocationCallbacks` object.
4. The application object is thereby zeroed in callback-bearing members.
5. `vkDestroyBuffer(..., &cb)` later enters custom repack with every allocator field already nil.
6. Native destroy crashes before any guest free callback.

## Source evidence

At product SHA `71afe476751deac24adabd1adb575fd2337b6e0a`:

- `ThunkLibs/Generator/gen.cpp` explicitly strips pointee constness before the `make_repack_wrapper<...>` emission.
- `ThunkLibs/include/common/Host.h` already strips cv only for its internal storage, while using `T`'s pointee constness to suppress automatic exit writeback.
- `ThunkLibs/libvulkan/libvulkan_interface.cpp` declares both `vkCreateBuffer` and `vkDestroyBuffer` as ordinary generated thunks. Their Vulkan allocator parameter has the same `const VkAllocationCallbacks*` type, so the create/destroy asymmetry comes from mutation caused by the first call rather than differing function annotations.

## Proposed minimal correction

Preserve pointee constness in the generated `repack_wrapper` template argument. Internal repack storage can remain mutable because `repack_wrapper::PointeeT` already removes cv.

Then test the exact allocator cross-call probe with these assertions:

- the guest `VkAllocationCallbacks` bytes are unchanged after `vkCreateBuffer`;
- create and destroy repacks both receive the original guest callback addresses and user pointer;
- the same native host trampoline identities are reused where the callback cache promises reuse;
- `vkDestroyBuffer` reaches the host/guest free callback and returns;
- native control remains green.

A second const-repackable type should be added as a generator-level regression test so the fix is not Vulkan-specific.
