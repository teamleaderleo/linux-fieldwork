# Thunkgen const-pointee repack result

Date: 2026-08-14
Status: runtime fix proven; generic unit validation in progress
Scope: owned FEX/fieldwork surfaces only

## Root cause

Thunkgen's generic repack path removed pointee `const` before selecting the host-side `repack_wrapper` type.

That matters because `repack_wrapper` uses pointee constness to decide whether converted host data may be copied back to guest memory on wrapper destruction.

For a function argument such as:

```cpp
const VkAllocationCallbacks* pAllocator
```

stripping pointee const made the wrapper behave as if the caller supplied writable `VkAllocationCallbacks*` storage. The Vulkan callback members do not have a valid automatic host->guest reverse conversion in that exit path, so a successful create call copied a converted structure back over the caller's allocator object and zeroed its guest callback fields.

The later destroy call then faithfully repacked the already-corrupted all-zero allocator structure. The destroy-side failure was therefore downstream of mutation performed by create.

## Minimal fix

Preserve the pointee's original const qualification when generating the `make_repack_wrapper<...>` type.

Clean owned-FEX source candidate:

```text
branch: linux-fieldwork/thunkgen-preserve-const-repack
head:   715ff36bff2fd9f2353ab31613dc41ae106f3938
parent: 71afe476751deac24adabd1adb575fd2337b6e0a
```

The candidate contains the product correction in `ThunkLibs/Generator/gen.cpp` plus a generic `StructRepacking` generator regression covering both guest ABIs.

## Hosted ARM64 runtime proof

Exact discriminator:

```text
branch:   ci/thunkgen-preserve-const-repack-20260814
head:     6ef56dcedf9389816f7910667ef8ea99ae5a9c85
run:      31786991508
job:      94725009294
result:   success
artifact: thunkgen-preserve-const-repack-31786991508
id:       9214023377
sha256:   551f529cdfa38e5a21063605af6d074fa117639d1a87e66664cd03b735d91f9c
```

The workflow requires:

```text
native=0
fex=0
same_guest_allocator=1
same_host_allocator=1
identity_ok=1
CB_FREE_ENTER
CB_FREE_RETURN
API_DESTROY_RETURN
```

The identity check compares the full guest allocator input set across create/destroy and the full converted native callback set across create/destroy. Both must remain bit-identical for the run to pass.

This is stronger than merely observing that the crash disappears: the caller's input stays intact, the host conversion remains compatible across calls, the native driver reaches the guest free callback, and destruction returns normally.

## Generic blast radius

The defect belongs to generic thunk repacking rather than Vulkan allocator semantics.

Any repackable `const T*` argument can be affected if the generated exit path treats the pointee as writable. Depending on the custom repack behavior, that can produce silent caller-memory mutation or a write fault when the input resides in read-only memory.

The Vulkan allocator case made the mutation unusually visible because callback members became zero and a later API call consumed the damaged object.

## Generic generator regression

A clean candidate test was added under the existing thunk generator `StructRepacking` suite. A CI-only branch is validating the test without adding workflow plumbing to the source candidate:

```text
candidate: linux-fieldwork/thunkgen-preserve-const-repack @ 715ff36b...
carrier:   ci/thunkgen-const-pointee-unit-20260814
```

Early carrier failures were build-environment/setup failures rather than product failures:

1. shallow checkout made an ancestry assertion unable to resolve the candidate parent;
2. x86-64 FEX configuration required the repository's explicit `ENABLE_X86_HOST_DEBUG=ON` CI mode;
3. the unit lane also needs thunk targets enabled.

The source candidate remains unchanged while those CI-only corrections are made.

Record the final unit run/job/artifact here once it completes.

## Product recommendation

Treat the const-preservation change as a standalone thunkgen correctness fix, independent of the executable-lifetime work.

The lifetime investigation discovered it because retained Vulkan allocation callbacks exposed a cross-call symptom, but the correction should be reviewed and tested as generic repack semantics:

> A generated wrapper for `const T*` may construct a converted host-side object, but it must not use wrapper teardown to copy that object back into the caller's const guest input.

## Relationship to callback lifetime

This fix removes one false lifetime-looking failure mode from Vulkan callback work. It does not change the actual executable-lifetime problem:

- callback trampolines may still outlive the guest generation that supplied their target;
- future entry still needs retirement/tombstoning;
- already-entered callbacks still need an execution lease if their owner can physically unload.

Keep those mechanisms separate in proposals and source review.
