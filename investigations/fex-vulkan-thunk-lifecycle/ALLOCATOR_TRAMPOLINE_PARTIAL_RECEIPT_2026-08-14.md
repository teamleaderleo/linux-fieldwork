# Vulkan allocator trampoline mediation — partial runtime receipt — 2026-08-14

Status: **partial fidelity demonstrated; cross-call destruction still fails**.

Reviewed FEX source: `71afe476751deac24adabd1adb575fd2337b6e0a`.

## What changed experimentally

The owned-fork experiment makes `VkAllocationCallbacks` a normally repacked type and custom-repacks all six pointer-bearing members. Instead of host diagnostic stubs, non-NULL callback members are converted to FEX's existing cached host-to-guest callback trampolines.

Guest Vulkan initialization sends host setup code the five guest callback-unpacker addresses for:

- `PFN_vkAllocationFunction`
- `PFN_vkReallocationFunction`
- `PFN_vkFreeFunction`
- `PFN_vkInternalAllocationNotification`
- `PFN_vkInternalFreeNotification`

The host allocator repacker combines those unpackers with each application's guest callback targets using `MakeHostTrampolineForGuestFunctionAt(...)`.

`VkSystemAllocationScope` and `VkInternalAllocationType` are also registered with the generator because those enum arguments occur inside allocator callback signatures and must be packed for host-to-guest callbacks.

## Generic `vkCreateBuffer` result

Workflow:

```text
repository: teamleaderleo/FEX
workflow: Vulkan allocator trampoline mediation experiment
run: 31782468194
job: 94711018542
```

Native control completed create/destroy with allocator callbacks.

Under FEX:

```text
MARK instance result=0 ...
MARK device result=0 ...
MARK create-buffer-enter guest_alloc=...
MARK create-buffer-return result=0 buffer=... alloc=1 realloc=0 free=0
MARK destroy-buffer-enter
timeout: the monitored command dumped core
```

Matrix:

```text
native=0
fex=139
```

This proves more than safe interception:

- native Vulkan invoked the FEX host trampoline;
- FEX entered the x86 guest allocation callback;
- the guest callback returned a memory pointer;
- native Vulkan accepted that returned memory and `vkCreateBuffer` returned `VK_SUCCESS`.

The failure is later, during object destruction.

## Instance allocator result

Workflow:

```text
repository: teamleaderleo/FEX
workflow: Vulkan instance allocator mediation experiment
run: 31782468108
job: 94711017216
artifact: 9212315745
artifact SHA-256: 8c84b84e2a66e52f98ec38cd74ed10c90eb152b8cfb652aad65bdc30bf4e42a7
```

This experiment also changes the existing custom `vkCreateInstance` wrapper to pass the repacked allocator to native Vulkan instead of replacing it with NULL.

Native controls:

```text
native_direct=0
native_dynamic=0
```

Under FEX, instance creation completed and showed native-like allocator activity:

```text
MARK create-return result=0 instance=... alloc=165 realloc=4 free=141
```

That is important: allocation, reallocation, and many free callbacks all executed successfully during `vkCreateInstance`.

The later destroy failed in both routes:

```text
fex_direct=139
fex_dynamic=139
```

Direct:

```text
MARK destroy-enter
timeout: the monitored command dumped core
```

GIPA-obtained destroy:

```text
MARK gipa-destroy ptr=...
MARK destroy-enter
timeout: the monitored command dumped core
```

## Updated classification

The remaining failure is **not** well described as "the free callback signature is broken."

`vkCreateInstance` already completed 141 free callbacks through the same mediation machinery before create returned. The problem appears only when Vulkan later frees object-lifetime allocations during a separate API call.

Leading hypotheses now are therefore cross-call properties such as:

- persistent allocation pointer/state across guest→host round trips;
- allocator compatibility/identity across separately repacked `VkAllocationCallbacks` copies;
- guest heap state or pointer contents after native Vulkan retains allocator-owned memory;
- callback transition state at the later API boundary.

The FEX trampoline cache itself is persistent: `MakeHostTrampolineForGuestFunction` caches by `(GuestUnpacker, GuestTarget)` and returns the existing executable trampoline on later requests. No trampoline retirement occurs after the create call in the reviewed implementation. That makes simple trampoline deallocation unlikely.

## Next discriminator

A dedicated cross-call trace probe records:

```text
allocation enter / returned pointer / backing malloc pointer
reallocation enter / header / return
free enter / memory pointer / last allocation pointer
free header magic / backing pointer
free return
```

The probe deliberately keeps a magic value immediately before every returned allocation. This distinguishes:

1. crash before guest free entry;
2. changed pointer delivered to guest free;
3. corrupted allocation header/payload boundary;
4. crash inside guest `free()`;
5. successful guest free followed by a later native-side crash.

Owned workflow currently used for that discriminator:

```text
Vulkan allocator cross-call trace
run: 31783160020
```

## Boundary

Full allocator mediation is **not yet a product candidate**. The creation-side result is strong evidence that the existing callback bridge can carry allocator calls and returned memory correctly, but cross-call destruction must be understood first.

Do not convert all eight custom allocator wrappers from NULL suppression to allocator passthrough until the retained-allocation destruction case is fixed.
