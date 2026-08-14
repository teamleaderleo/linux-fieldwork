# Thunkgen const-pointee repack result

Date: 2026-08-14
Status: runtime fix and targeted generic regression proven
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

The clean candidate adds a `StructRepacking` regression for both guest ABIs. The CI-only carrier eventually reduced all setup noise and ran that targeted test directly from the configured `build/Bin/thunkgentest` path.

Targeted receipt:

```text
branch:   ci/thunkgen-const-pointee-unit-20260814
head:     ffc29f2b930ae6198ad619e2c8ab0074c700e7f5
run:      31793742608
job:      94746142932
artifact: thunkgen-const-pointee-unit-31793742608
id:       9216592294
sha256:   00e334bb6fb750581e741402f41598f8694531c161ced2aec374c9b703e3a65b
```

The targeted `StructRepacking` section succeeds:

```text
All tests passed (28 assertions in 1 test case)
```

The assertions cover X86_32 and X86_64 generation and require the generated host repack wrapper for the test argument to retain the `const` pointee qualification.

### Full-suite comparator

The same hosted x86 configuration reports four failures when the broader `thunkgen_tests` target is run:

```text
MultipleParameters.ThunkGen
DataLayoutPointers.ThunkGen
DataLayout.ThunkGen
Mapping guest integers to fixed-size.ThunkGen
73% tests passed, 4 tests failed out of 15
```

Those failures are not introduced by the const candidate. The exact unmodified parent `71afe476751deac24adabd1adb575fd2337b6e0a` reproduces that same four-test failure set in the same runner/configuration.

Baseline comparator:

```text
run:      31794090739
job:      94747215283
result:   success as comparator
artifact: thunkgen-baseline-suite-31794090739
id:       9216731040
sha256:   c73af30273d56d2ebf7ace607642d5b6ad1ae5c35069c4a0ece76e01fce2a7eb
```

The comparator succeeds only if the baseline contains all four named failures and the same `73% / 4 failed` summary. Therefore the candidate-specific validation result is:

```text
runtime Vulkan allocator discriminator: PASS
targeted generic StructRepacking regression: PASS
broader hosted-x86 thunkgen failure delta vs exact parent: NONE OBSERVED
```

The source candidate remained unchanged while the CI carrier was repaired.

## Product recommendation

Treat the const-preservation change as a standalone thunkgen correctness fix, independent of the executable-lifetime work.

The lifetime investigation discovered it because retained Vulkan allocation callbacks exposed a cross-call symptom, but the correction should be reviewed and tested as generic repack semantics:

> A generated wrapper for `const T*` may construct a converted host-side object, but it must not use wrapper teardown to copy that object back into the caller's const guest input.

The clean branch is now suitable for source review on that basis. A future upstream submission should use FEX's normal project CI rather than treating the hosted x86 full-suite comparator as a replacement for upstream CI.

## Relationship to callback lifetime

This fix removes one false lifetime-looking failure mode from Vulkan callback work. It does not change the actual executable-lifetime problem:

- callback trampolines may still outlive the guest generation that supplied their target;
- future entry still needs retirement/tombstoning;
- already-entered callbacks still need an execution lease if their owner can physically unload.

Keep those mechanisms separate in proposals and source review.
