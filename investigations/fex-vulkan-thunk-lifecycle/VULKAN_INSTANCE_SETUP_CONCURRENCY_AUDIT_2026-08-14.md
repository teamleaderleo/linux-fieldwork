# Vulkan instance setup concurrency and ownership audit — 2026-08-14

Status: source-level correctness findings on current reviewed FEX. No runtime failure is claimed by this note.

Reviewed FEX product revision: `71afe476751deac24adabd1adb575fd2337b6e0a`.

## Source shape

`ThunkLibs/libvulkan/Host.cpp` contains process-global state:

```cpp
static bool SetupInstance {};
static std::mutex SetupMutex {};
```

`DoSetupWithInstance(VkInstance instance)` takes `SetupMutex`, writes process-global Vulkan loader slots such as `fexldr_ptr_libvulkan_vkGetDeviceProcAddr` and `fexldr_ptr_libvulkan_vkCreateDevice`, and then sets `SetupInstance = true` for a non-null instance. The function itself carries:

```text
TODO: Support use of multiple instances
```

The custom host `vkGetInstanceProcAddr` entrypoint reads the same flag outside the mutex:

```cpp
if (!SetupInstance && a_0) {
  DoSetupWithInstance(a_0);
}
```

Exact FEX source:

- `ThunkLibs/libvulkan/Host.cpp` at `71afe476751deac24adabd1adb575fd2337b6e0a`.

## Finding 1 — unsynchronized process-global flag

The read of `SetupInstance` in `vkGetInstanceProcAddr` is not protected by `SetupMutex` and the flag is not atomic. The write is performed while holding `SetupMutex`.

Vulkan's threading model allows commands to be called concurrently from multiple host threads except where parameters or parameter components are explicitly declared externally synchronized. The `vkGetInstanceProcAddr` reference has no Host Synchronization requirement for its `VkInstance` parameter.

Therefore two legal concurrent guest calls to FEX's `vkGetInstanceProcAddr` can execute an unsynchronized C++ read/write pair on `SetupInstance`.

This is a source-level C++ data race regardless of whether the underlying Vulkan loader happens to return identical function addresses on a particular machine.

Official Vulkan references:

- https://docs.vulkan.org/spec/latest/chapters/fundamentals.html — Threading Behavior.
- https://docs.vulkan.org/refpages/latest/refpages/source/vkGetInstanceProcAddr.html — command reference and valid usage.

## Finding 2 — first-instance process-global loader-slot ownership

The first non-null instance that reaches setup populates process-global slots and sets `SetupInstance = true`. Later non-null instances normally skip `DoSetupWithInstance` entirely.

That is a stronger semantic concern than the flag race itself. Vulkan defines the `instance` argument to `vkGetInstanceProcAddr` as the instance with which the returned function pointer is compatible, and states that returned dispatchable command pointers must only be called with that instance or one of its children. The specification also explicitly describes loaders supporting multiple Vulkan implementations by returning dispatch code that can reach different real implementations for different dispatchable objects.

FEX's one-time global setup therefore assumes that one instance's queried `vkGetDeviceProcAddr` / `vkCreateDevice` pointers are suitable process-wide for all later instances. The source provides no per-instance owner identity, no compatible-claim set, and no refresh when a different instance becomes relevant.

This should be analyzed using the same ownership vocabulary as the retained same-H multi-owner work:

```text
current setup model:
  global slot -> pointer obtained from first instance

more explicit model:
  instance/load-generation claim -> compatible dispatch pointer / ABI identity
```

The same-H multi-owner experiment demonstrates that collapsing multiple live owners into one global owner record can lose necessary lifetime information. It does not itself prove a Vulkan multi-instance failure, but it argues against treating process-global first-owner state as a safe generic invariant.

Official Vulkan initialization reference:

- https://docs.vulkan.org/spec/latest/chapters/initialization.html — `vkGetInstanceProcAddr` compatibility and multiple-implementation dispatch semantics.

## Best runtime discriminators

A useful runtime test should avoid relying only on pointer inequality, because a conforming loader may legitimately return the same dispatch stub for multiple instances.

Higher-value variants are:

1. **Concurrent first setup:** create two valid instances, synchronize two guest threads to enter `vkGetInstanceProcAddr` before setup has completed, and instrument exact setup-entry/exit ownership. This can expose duplicate/conflicting global-slot initialization and gives a concrete concurrency trace. A ThreadSanitizer-style host build would be a secondary control if practical.
2. **Different instance capabilities:** create instances with deliberately different enabled instance-extension sets and query extension commands whose availability differs. Verify that FEX return/null behavior and any custom-loader slot used by the returned wrapper follow the queried instance rather than the first setup instance.
3. **Multiple implementation/dispatch context:** where the loader environment can expose genuinely different underlying dispatch paths, query through both instances and invoke only with the matching instance/children. This is the strongest semantic discriminator but is less portable than the first two.

## Evidence boundary

Source-proven:

- `SetupInstance` is a non-atomic process-global flag.
- its read and write are not consistently protected by `SetupMutex`.
- setup mutates process-global function-pointer slots.
- only the first non-null instance normally performs setup.
- FEX source explicitly acknowledges missing multi-instance support.
- Vulkan permits concurrent command calls absent an explicit external-synchronization rule and gives `vkGetInstanceProcAddr` instance-scoped pointer compatibility semantics.

Not yet demonstrated:

- a user-visible FEX crash or wrong dispatch caused by this race;
- a particular two-instance configuration that returns observably wrong Vulkan results;
- whether common Linux loaders mask the global-slot ownership defect by returning stable process-wide dispatch stubs.
