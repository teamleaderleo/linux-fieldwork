# Real Vulkan PFN lifetime stock/candidate A/B

Date: 2026-08-14

## Result

A hosted ARM64 A/B now reproduces the guest-thunk unload failure with FEX's **real generated Vulkan guest/host thunks** and isolates the distinguishing change to the FEX runtime lifetime logic.

The generated Vulkan thunk binaries were byte-identical before and after the runtime candidate was applied:

```text
libvulkan-guest.so
59d28334967111971cf2eb9c15fa1dd611b7b36b1addd1465e5f32e70cbca618

libvulkan-host.so
2e93b9c3e26650df2ceed054ddb0bf1999495861db8a4ed9155adcbfb607cd0b
```

No thunk source or generated thunk binary changed between the stock and candidate phases. Only `FEX` / `FEXServer` were rebuilt after applying the research-only lifetime candidate.

Observed matrix:

```text
stock_hold=0
stock_close=139
stock_reload=139
candidate_hold=0
candidate_close=139
candidate_reload=0
```

GitHub Actions run: `31772339815`

Artifact: `vulkan-pfn-lifetime-ab-31772339815`

Artifact digest:

```text
sha256:6acfb52ded50890476f2b1c459ad6d6d4d6b133fbb4a7355d58443e30fb1a942
```

FEX source under test: `71afe476751deac24adabd1adb575fd2337b6e0a`.

External source identity, when needed: `https://redirect.github.com/FEX-Emu/FEX/commit/71afe476751deac24adabd1adb575fd2337b6e0a`.

## Probe path

The retained x86-64 probe does this with the generated Vulkan thunk:

1. `dlopen("libvulkan.so.1")`.
2. Obtain `vkGetInstanceProcAddr` from the guest Vulkan DSO.
3. Ask GIPA for `vkEnumerateInstanceVersion`.
4. Call the returned dynamic PFN successfully.
5. Final-close the guest Vulkan DSO, or keep an extra ref as a control.
6. For reload mode, reserve every former Vulkan guest mapping so the second load must move to a different guest generation.
7. Reopen Vulkan, obtain the dynamic PFN again, and call it.

The minimal hosted rootfs includes only the x86 X11 symbols required by the Vulkan guest thunk constructor (`XSync`, `XGetVisualInfo`, `XDisplayString`). This is the same bootstrap boundary already established in the hosted Vulkan X11 receipt.

## Stock behavior

Generation 1 registers:

```text
native H = 0x7ffff76c80f4
guest GIPA = 0x7ffff7ea22b0
guest invoker T1 = 0x7ffff7ea4400
```

The PFN works before close.

After final close, stock FEX has removed the guest Vulkan mappings. A direct stale PFN call exits 139, as expected for an invalid lifetime.

The stronger discriminator is changed-base reload. The old guest ranges are reserved, then generation 2 loads at a different guest address:

```text
old GIPA = 0x7ffff7ea22b0
new GIPA = 0x7ffff76712b0
old PFN  = 0x7ffff76c80f4
new PFN  = 0x7ffff76c80f4
same native PFN = 1
new guest invoker T2 = 0x7ffff7673400
```

Stock logs a new link from the same native `H` to `T2`, but the first call through that newly acquired PFN still crashes:

```text
PROBE acquired generation=2 ... same-pfn=1
PROBE call where=after-reload-new-pfn pfn=0x7ffff76c80f4
# exit 139
```

This is the important stock failure. It is not a stale application pointer: the program reacquires the PFN from generation 2 after a forced moved reload. The same native host function address is reused, while the guest thunk invoker moved.

## Candidate behavior

The research candidate makes the native host PFN a lifecycle-owned synthetic entry rather than a one-way registration.

On generation-1 final unload it records, in order:

```text
DIAG_MULTI_DROP H=0x7ffff76c80f4 T=0x7ffff7ea4400 ...
DIAG_MULTI_RETIRE H=0x7ffff76c80f4 OLD=0x7ffff7ea4400 NEW=0
DIAG_LOCKED_DEFINITION H=0x7ffff76c80f4 handler=1
DIAG_MT_SHARED H=0x7ffff76c80f4 erased=1
DIAG_MT_THREAD H=0x7ffff76c80f4 ...
DIAG_REVOKED_H_INSTALL H=0x7ffff76c80f4
DIAG_LOCKED_RETIRE H=0x7ffff76c80f4 ...
```

A stale PFN call after final close still fails, but it fails through the synthetic revoked entry:

```text
DIAG_REVOKED_H_COMPILE H=0x7ffff76c80f4
# exit 139
```

That distinguishes controlled revocation from falling through to ordinary guest decoding of the native ARM64 address.

On generation-2 registration, the candidate invalidates the synthetic H entry again and reactivates the same native `H` against the moved guest invoker `T2`:

```text
DIAG_REVOKED_H_ACTIVATE H=0x7ffff76c80f4 T=0x7ffff7673400 ...
DIAG_MULTI_ACTIVE H=0x7ffff76c80f4 T=0x7ffff7673400
```

The newly acquired real Vulkan PFN then works:

```text
PROBE call where=after-reload-new-pfn pfn=0x7ffff76c80f4
PROBE return where=after-reload-new-pfn result=0 version=0x403113
```

Candidate reload exits `0`.

## What this proves

This A/B establishes a concrete generic FEX lifetime defect on the real Vulkan thunk path:

- A native dynamic PFN address can remain stable across guest thunk unload/reload.
- The corresponding guest `CallHostFunction` invoker can move to a different address on reload.
- Pristine FEX accepts the generation-2 registration but retains execution/cache state for the old synthetic native entry strongly enough that the newly reacquired generation-2 PFN still crashes.
- Exact retirement of the synthetic native H entry, including shared compiled state and every guest thread's hot cache, followed by reactivation to the new guest target, changes the same moved-reload case from exit `139` to exit `0`.
- The generated Vulkan guest and host thunk binaries are byte-identical across the A/B, so the discriminator belongs to FEX runtime lifetime handling rather than a changed thunk implementation.

This is stronger than the earlier M5 pinning result and stronger than the synthetic thunk reproducer because it exercises FEX's generated Vulkan thunk, real `vkGetInstanceProcAddr`, and a real dynamic Vulkan PFN.

## What remains unproved

The retained Apple M5 `vulkaninfo` crash still lacks a trace of its **immediate final caller/dispatch edge**. The M5 receipt proves execution reached an unmapped old Vulkan guest-thunk range and that pinning that DSO changes exit 139 to exit 0, but it did not record the native PFN H value or the first post-unload synthetic-entry hit.

Therefore the bounded statement is:

> The generated-Vulkan dynamic-PFN unload/reload lifetime bug is independently reproduced and repaired by the research candidate. This strongly supports the same lifetime mechanism as the explanation for the M5 teardown failure, but the original M5 final transfer was not directly captured.

The candidate is research-only diagnostic code. FEX's policy prohibits AI-generated contribution code; any upstream implementation must be independently derived and written by a human.

## Related required properties already proven separately

The broader repair needs more than deleting one CustomIR map entry:

- exact H invalidation must reach **all emulation threads**, not only the thread performing unload;
- shared compiled/direct-link state for H must be removed;
- final-owner retirement should leave H as a controlled synthetic revoked entry until a compatible owner reactivates it;
- multiple live claims for one H need retained ownership plus compatibility-aware promotion;
- host-to-guest callback trampolines need revocable lifetime state too;
- retirement cannot commit before a `munmap` that may fail without either prevalidation or rollback;
- the preferred callback design is an immutable escaped trampoline pointing to an FEX-owned descriptor whose LIVE/REVOKED state can be changed atomically.

No upstream FEX interaction was made.