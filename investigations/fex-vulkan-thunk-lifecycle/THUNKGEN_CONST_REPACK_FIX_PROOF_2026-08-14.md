# Thunkgen const-pointee repack fix proof — 2026-08-14

## Result

The minimal thunkgen correction that preserves pointee cv-qualification in the emitted `repack_wrapper<T>` template fixes the Vulkan allocator cross-call corruption end to end.

Carrier:

```text
repository: teamleaderleo/FEX
branch: ci/thunkgen-preserve-const-repack-20260814
carrier head: 6ef56dcedf9389816f7910667ef8ea99ae5a9c85
product baseline: 71afe476751deac24adabd1adb575fd2337b6e0a
run: 31786991508
job: 94725009294
artifact id: 9214023377
artifact sha256: 551f529cdfa38e5a21063605af6d074fa117639d1a87e66664cd03b735d91f9c
```

The workflow completed successfully.

## Minimal generator change

The baseline generator explicitly removed `const` from pointer pointees before emitting a repack wrapper. The candidate removes that special case and preserves the source pointee qualification:

```cpp
auto get_repack_wrapper_type_name = [&](clang::QualType type) {
  type = type.getLocalUnqualifiedType();
  return get_type_name(context, type.getTypePtr());
};
```

`repack_wrapper` already removes cv-qualification for its internal host-side storage. Preserving `const` in its public template type therefore retains mutable temporary storage while restoring the existing destructor rule that suppresses exit writeback through a const pointee.

## Runtime matrix

```text
native=0
fex=0
same_guest_allocator=1
same_host_allocator=1
identity_ok=1
```

Create-side repack:

```text
ALLOC_REPACK_BEGIN seq=1 guest_user=0x55ce3aea4024 host_user=0x55ce3aea4024 guest_alloc=0x55ce3aea17dc guest_realloc=0x55ce3aea17ed guest_free=0x55ce3aea17fe guest_internal_alloc=(nil) guest_internal_free=(nil)
ALLOC_REPACK_END seq=1 host_user=0x55ce3aea4024 host_alloc=0x7ffff7e3e090 host_realloc=0x7ffff7e3e0c0 host_free=0x7ffff7e3e0f0 host_internal_alloc=(nil) host_internal_free=(nil)
CB_ALLOC_ENTER a=0x55ce3aea4024 b=0x90 c=0x8
CB_ALLOC_RETURN a=0x55ce3aec7218 b=0x55ce3aec7200 c=0x1
```

Destroy-side repack sees the original guest allocator intact and resolves to the same native trampoline set:

```text
ALLOC_REPACK_BEGIN seq=2 guest_user=0x55ce3aea4024 host_user=0x55ce3aea4024 guest_alloc=0x55ce3aea17dc guest_realloc=0x55ce3aea17ed guest_free=0x55ce3aea17fe guest_internal_alloc=(nil) guest_internal_free=(nil)
ALLOC_REPACK_END seq=2 host_user=0x55ce3aea4024 host_alloc=0x7ffff7e3e090 host_realloc=0x7ffff7e3e0c0 host_free=0x7ffff7e3e0f0 host_internal_alloc=(nil) host_internal_free=(nil)
CB_FREE_ENTER a=0x55ce3aea4024 b=0x55ce3aec7218 c=0x55ce3aec7218
CB_FREE_HEADER a=0x55ce3aec7200 b=0x90 c=0x46584558414c4c4f
CB_FREE_RETURN a=0x55ce3aec7218 b=0x55ce3aec7200 c=0x55ce3aec7200
API_DESTROY_RETURN a=0x1 b=0x0 c=0x1
```

## Conclusion

This confirms the root cause recorded in `THUNKGEN_CONST_REPACK_CORRUPTION_ROOT_CAUSE_2026-08-14.md`: the create call was corrupting application-owned `const VkAllocationCallbacks` on thunk exit. Destroy was reading that prior corruption.

The correction belongs in generic thunkgen rather than Vulkan-specific callback code.

## Follow-up

Add a generator-level regression in `unittests/ThunkLibs/generator.cpp` that exercises a repackable `const A*` parameter and asserts the generated host unpacker instantiates `repack_wrapper<const A*>` (or equivalently preserves a const pointee). Run `thunkgen_tests` for both guest ABIs where the fixture supports it.

The workflow attempted to capture generated Vulkan source from an outdated path (`build/gen_64/...`) and therefore left that auxiliary text file empty. Runtime identity and callback assertions all passed, so this is a receipt-collection defect rather than a product-test defect. A generic generator test removes reliance on that auxiliary grep.
