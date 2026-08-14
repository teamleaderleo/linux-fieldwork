# FEX Vulkan allocator const-repack audit

## Scope

This note records an adjacent FEX thunk-generator bug found while testing whether Vulkan `VkAllocationCallbacks` can be mediated through FEX rather than discarded.

Exact FEX source under test:

- `71afe476751deac24adabd1adb575fd2337b6e0a`

Owned experimental carrier:

- `teamleaderleo/FEX`
- branch `linux-fieldwork/vulkan-procaddr-native-first-experiment`

This is separate from the original three-entry Vulkan dynamic custom-routing mismatch, although allocator mediation was reached through the same investigation.

## Short result

A generic repacked parameter declared as a pointer to const data can be treated as writable by generated FEX host-unpack code.

For the Vulkan experiment, the concrete sequence is:

1. the x86 guest passes a valid `const VkAllocationCallbacks*`;
2. FEX repacks it to a temporary host-layout allocator and replaces guest callback pointers with host-callable trampolines;
3. the native Vulkan create call succeeds and calls the guest allocator;
4. on scope exit, generated repack cleanup copies the temporary host representation back over the application-owned guest allocator;
5. the callback-bearing members are not reconstructed by that ordinary host-to-guest copy, so the guest allocator becomes zeroed;
6. a later Vulkan destroy call sees an all-zero allocator and fails before the guest free callback can run.

A Vulkan-only causal control that suppresses this writeback makes both buffer and event create/destroy lifetimes complete successfully under FEX.

## Evidence progression

### 1. Central allocator interception works

A single custom-repacked `VkAllocationCallbacks` type can intercept generic Vulkan commands. This avoids per-command wrappers for the large generic allocator-taking surface.

The experiment custom-repacks all pointer-bearing members:

- `pUserData`
- `pfnAllocation`
- `pfnReallocation`
- `pfnFree`
- `pfnInternalAllocation`
- `pfnInternalFree`

The guest sends five callback-unpacker entrypoints to the host during thunk initialization. The host combines each application callback address with its corresponding unpacker and uses FEX's existing host-to-guest trampoline cache.

### 2. Creation-side callback fidelity works

The mediated generic `vkCreateBuffer` path successfully:

- enters the x86 allocation callback from native ARM Vulkan;
- passes allocator arguments correctly;
- receives a `void*` result back from the guest callback;
- uses the returned guest allocation as the native Vulkan object's backing storage;
- returns `VK_SUCCESS` to the guest.

Instance-side experiments also exercised allocation, reallocation, and same-call free callbacks in volume. This rules out a blanket callback-ABI or callback-return limitation.

### 3. Original cross-call failure

Representative buffer trace, run `31783500800`:

- native: `0`
- FEX: `139`

FEX reached `API_DESTROY_ENTER` but never entered the guest `pfnFree` body.

A no-free negative control, run `31783815574`, replaced guest free with a function that only records entry and returns. FEX still exited `139` before entering that function. Therefore guest libc `free()` was not the failure owner.

A host-side wrapper around `pfnFree`, run `31783908732`, was also never entered. Therefore the failure occurred before the allocator free callback transition.

### 4. Fully populated `VkEvent` control reproduces the same class

The event probe supplies a complete allocation/reallocation/free trio.

Run `31785498877`:

- native event create/destroy succeeds;
- FEX event create succeeds through the guest allocator;
- FEX fails after `EVENT_DESTROY_ENTER` and before `EVENT_FREE_ENTER`.

Artifact:

- `allocator-event-31785498877`
- artifact id `9213437054`
- SHA-256 `9dc1fa8d1ddabae20bfe7f7157d8a90f806f7e220ea7dbe577fd7b3c001dd6ad`

This shows the cross-call failure is not peculiar to `VkBuffer` teardown.

### 5. Direct repack trace identifies guest-input corruption

Run `31785903507` instrumented `fex_custom_repack_entry(VkAllocationCallbacks)` on both calls.

Create-side source allocator:

```text
REPACK_ENTER guest_user=<non-null>
  guest_alloc=<guest callback>
  guest_realloc=<guest callback>
  guest_free=<guest callback>
```

Create-side host allocator:

```text
REPACK_EXIT host_user=<same user data>
  host_alloc=<host trampoline>
  host_realloc=<host trampoline>
  host_free=<host trampoline>
```

The allocation callback then runs and create returns successfully.

On the later destroy call, before any new trampoline work:

```text
REPACK_ENTER guest_user=(nil)
  guest_alloc=0x0
  guest_realloc=0x0
  guest_free=0x0
  guest_internal_alloc=0x0
  guest_internal_free=0x0
```

Artifact:

- `allocator-repack-trace-31785903507`
- artifact id `9213595262`
- SHA-256 `9dadbe56ada94299f2b96716a54890db6af9b2a67de4db301542ff43de6b9e56`

This proves the application allocator itself was modified between the two API calls.

## Generator mechanism

`repack_wrapper<T, GuestT>` in `ThunkLibs/include/common/Host.h` is designed to preserve const-input semantics.

Internally it strips const only from storage:

```cpp
using PointeeT = std::remove_cv_t<std::remove_pointer_t<T>>;
std::optional<host_layout<PointeeT>> data;
```

Its destructor intentionally avoids automatic host-to-guest copyback when the original wrapper type points to const data:

```cpp
if constexpr (!std::is_const_v<std::remove_pointer_t<T>>) {
  *orig_arg.get_pointer() = to_guest(*data);
}
```

However, `ThunkLibs/Generator/gen.cpp` currently strips pointee constness before instantiating that wrapper. For repackable pointer parameters it emits the wrapper type using `get_type_name_with_nonconst_pointee(param_type)`.

Consequently a source parameter equivalent to:

```cpp
const A*
```

is represented by a mutable repack wrapper equivalent to:

```cpp
repack_wrapper<A*, ...>
```

instead of preserving:

```cpp
repack_wrapper<const A*, ...>
```

The wrapper destructor therefore believes automatic copyback is allowed.

This is a generic ThunkGen constness issue. Vulkan is the runtime reproducer because `VkAllocationCallbacks` contains several custom-repacked pointer members whose temporary host values must never be written back into an input-only application struct.

## Causal A/B: suppress only allocator writeback

A Vulkan-only causal control changes the allocator custom-exit hook from returning `false` to returning `true`.

That tells `repack_wrapper` custom exit handling is complete and suppresses its ordinary automatic copyback. No generic generator behavior is changed in this control.

Run `31786720593`:

```text
buffer=0
event=0
```

Buffer destroy now shows the original guest allocator intact on the second call:

```text
REPACK_ENTER guest_user=<original non-null value>
  guest_alloc=<original guest callback>
  guest_realloc=<original guest callback>
  guest_free=<original guest callback>
```

FEX rebuilds/reuses the host trampolines, then reaches:

```text
CB_FREE_ENTER
CB_FREE_HEADER
CB_FREE_RETURN
API_DESTROY_RETURN
```

The event path similarly reaches:

```text
EVENT_FREE_ENTER
EVENT_FREE_RETURN
EVENT_DESTROY_RETURN
PASS event allocator lifetime
```

Artifact:

- `allocator-no-writeback-31786720593`
- artifact id `9213899971`
- SHA-256 `f3c6b0ad0615e2b56789bb5be709f5feeebd3085e99b9f25073ba1cd35bfcf05`

This is the causal proof that erroneous exit writeback owns the observed cross-call failure.

## Preferred generic fix

The current preferred fix is to preserve the source parameter's pointee constness when generating `make_repack_wrapper<...>`.

Experimental change:

```cpp
make_repack_wrapper<get_type_name(context, param_type.getTypePtr())>(...)
```

rather than using the helper that deliberately strips pointee constness.

This keeps the existing wrapper design:

- non-const internal host storage remains available for repacking;
- a mutable source pointer can still receive exit copyback;
- a pointer-to-const source retains enough type information for the wrapper destructor to skip automatic writeback.

A synthetic generator regression is being developed alongside this fix. It declares a function taking `const A*`, where a member of `A` requires custom repacking, and verifies that the generated repack wrapper retains constness.

## Validation boundary at this checkpoint

Proven:

- the allocator callback bridge works on create;
- the same type-level policy reaches generic Vulkan allocator-taking commands;
- the guest `VkAllocationCallbacks` is valid at create and zeroed before the later destroy call;
- suppressing automatic writeback alone keeps the allocator intact and makes both buffer and event lifetimes pass;
- therefore the observed cross-call crash is caused by erroneous writeback to an input-only allocator.

Source-level diagnosis:

- generated repack-wrapper emission strips pointee constness before `repack_wrapper` can apply its existing const-input guard;
- this explains the runtime mutation and is broader than Vulkan.

Still pending at this checkpoint:

- the generic const-preserving generator patch must pass its focused generator regression;
- the generic patch must independently make the Vulkan buffer/event runtime matrix pass without the Vulkan-only no-writeback workaround;
- a clean source-only candidate branch should be created only after those gates pass.

## Reopen conditions

Reopen the generic diagnosis if a focused generated-code trace shows `const A*` already reaches `repack_wrapper` with pointee constness preserved on the exact source under test.

Reopen the causal classification if the generic fix leaves the guest allocator unchanged but the cross-call Vulkan failures return.

Reopen allocator-fidelity scope if additional Vulkan callback signatures require unsupported asynchronous callback behavior, materially different pointer return semantics, or a driver/API contract incompatible with FEX's host-to-guest callback bridge.

This note does not alter the separate dynamic `custom_host_impl` registration finding or the separate thunk-unload/exit-139 investigation.
