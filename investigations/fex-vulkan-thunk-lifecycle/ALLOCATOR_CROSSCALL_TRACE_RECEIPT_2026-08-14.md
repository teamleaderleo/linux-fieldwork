# Vulkan allocator cross-call trace receipt — 2026-08-14

Status: **runtime boundary narrowed: failure occurs before guest free callback body entry.**

Reviewed FEX source: `71afe476751deac24adabd1adb575fd2337b6e0a`.
Allocator mediation experiment: type-level `VkAllocationCallbacks` repacking plus FEX host-to-guest trampolines.

## Purpose

Earlier mediation runs proved that allocator callbacks can work during Vulkan create calls but later destruction crashes. This trace distinguishes pointer corruption / guest heap failure from an earlier callback-transition or native-side failure.

The probe places a header immediately before each allocation returned to Vulkan:

```text
base pointer
allocation size
magic = 0x46584558414c4c4f
```

It logs allocation, reallocation, and free callback entry/return as well as the Vulkan create/destroy boundaries.

## Workflow

Owned fork:

```text
repository: teamleaderleo/FEX
workflow: Vulkan allocator cross-call trace
run: 31783500800
job: 94714162281
carrier head: 9ca70cfeff4e891d6a61aa7c64f90e5feb30f1f3
product source: 71afe476751deac24adabd1adb575fd2337b6e0a
```

The first workflow attempt stopped while compiling the diagnostic probe because `-Werror=use-after-free` rejected printing a pointer variable after `free()`. The corrected probe converts the address to `uintptr_t` before free. That was harness-only and did not alter the FEX experiment.

## Native control

Native ARM64 completes the full pair:

```text
API_CREATE_ENTER
CB_ALLOC_ENTER
CB_ALLOC_RETURN
API_CREATE_RETURN
API_DESTROY_ENTER
CB_FREE_ENTER
CB_FREE_HEADER
CB_FREE_RETURN
API_DESTROY_RETURN
```

The free callback sees the exact pointer returned by allocation, the header magic remains valid, and the backing allocation is released normally.

## FEX result

Under the mediated x86-64 guest path:

```text
API_CREATE_ENTER
CB_ALLOC_ENTER
CB_ALLOC_RETURN
API_CREATE_RETURN result=0
API_DESTROY_ENTER
timeout: the monitored command dumped core
```

Final matrix:

```text
native=0
fex=139
```

Most importantly, **there is no `CB_FREE_ENTER` marker under FEX**.

The pointer recorded immediately before destroy is still the same allocation pointer returned by the guest allocation callback during create. Therefore this receipt rules out several hypotheses as the first failure:

- the application-visible allocation pointer did not change across the create/destroy round trip;
- the crash is not observed inside the guest `free()` call;
- the trace never reaches the guest-side header/magic validation on the later free callback.

## Current split

The first failure is now one of two places:

1. native Vulkan faults before it calls the allocator's `pfnFree`; or
2. native Vulkan calls the host trampoline, but FEX faults during host-to-guest transition before the guest `free_cb` body begins.

Two independent discriminators are running/queued from this result:

### Host-side free wrapper

Wrap only the mediated `pfnFree` with a host function that prints before and after invoking the FEX guest trampoline.

Useful outcomes:

```text
no HOST_FREE_WRAPPER_ENTER
  -> native fault occurs before callback invocation

HOST_FREE_WRAPPER_ENTER but no CB_FREE_ENTER
  -> fault is inside host-to-guest trampoline transition

CB_FREE_ENTER
  -> original trace missed a later guest-side boundary; continue through header/free markers
```

Owned workflow:

```text
Vulkan allocator host free trampoline trace
run: 31783908732
```

### Guest no-free negative control

Use the same mediated guest `pfnFree`, but have its body record the pointer and return without calling libc `free()`.

If destroy completes, callback transition works and actual guest-heap release is implicated. If it still crashes before the marker, the failure is earlier than guest `free()`.

Owned workflow:

```text
Vulkan allocator no-free negative control
run: 31783815574
```

## Conclusion at this checkpoint

Full allocator mediation remains promising for create-side fidelity, but the retained-allocation destroy path is not solved. The failure boundary has moved from a broad "destroy crashes" statement to a precise pre-guest-free boundary.

Do not promote the staged all-custom-wrapper allocator pass-through experiment until this boundary is resolved.
