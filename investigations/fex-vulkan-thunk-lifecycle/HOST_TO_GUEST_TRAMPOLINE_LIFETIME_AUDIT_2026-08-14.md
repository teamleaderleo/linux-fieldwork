# Host-to-guest trampoline lifetime audit — 2026-08-14

Status: demonstrated real-FEX lifetime failure class on current reviewed product source. This remains an adjacent failure class, not a claim that it is the immediate cause of the retained Vulkan teardown crash.

Reviewed and executed FEX product revision: `71afe476751deac24adabd1adb575fd2337b6e0a`.
Owned-FEX workflow run: `31741167700` (`Full thunk lifetime matrix ARM64`).
Carrier commit: `6534a832336b621bd76aa2d33dc8146f17cdfb71`.
Fieldwork fixture revision used by that run: `9eca19ac8743567ce2af7b4c82f2483d97c19b09`.

## Source result

FEX's host-to-guest callback path caches executable host trampolines in `ThunkHandler_impl::GuestcallToHostTrampoline` using a key made only from two raw guest addresses:

```text
{ GuestUnpacker, GuestTarget }
```

`MakeHostTrampolineForGuestFunction()` returns an existing cached trampoline on a key hit. When it creates a new trampoline, it allocates executable host memory and embeds a `TrampolineInstanceInfo` containing the same raw `GuestUnpacker` and `GuestTarget` values.

The reviewed `ThunkHandler_impl` source contains no per-guest-DSO or guest-mapping generation in the cache key and no guest-unload retirement operation for these entries. The map therefore survives ordinary guest DSO unloads until the owning thunk handler/process is destroyed.

Exact source paths at the reviewed revision:

- `Source/Tools/LinuxEmulation/Thunks.cpp`: `GuestcallInfo`, `GuestcallToHostTrampoline`, `MakeHostTrampolineForGuestFunction`, `AllocateHostTrampolineForGuestFunction`, and `CreateThunkHandler`.
- `ThunkLibs/include/common/Host.h`: `CallbackUnpack` and `MakeHostTrampolineForGuestFunctionAt` consume the cached host trampoline and eventually call through the embedded guest unpacker/target.

## Executed ARM64 discriminator

The existing full real-FEX thunk-pair fixture exercises both retained directions with one unloadable x86-64 guest DSO. It invokes the callback path successfully before unload, performs final `dlclose()`, proves that the old guest target and unpacker no longer have mappings, and invokes the retained host callback in a child.

Current-FEX run `31741167700` recorded, before unload:

```text
pre-unload host->guest callback  rv=10053 want=10053
```

After `dlclose()`:

```text
old target after dlclose           <old target> -> unmapped
old unpacker after dlclose         <old unpacker> -> unmapped
proof: all embedded guest executable addresses lost mappings
child stale first callback        signal=11 (Segmentation fault)
```

The same run also exercises a forced-different reload by reserving the old guest-DSO span `PROT_NONE`. The fresh DSO therefore receives a different guest executable address. In that case:

```text
reload invoker                    old=<generation-1> new=<different generation-2 address> DIFFERENT
child retained callback reload    signal=11 (Segmentation fault)
fresh/current callback            rv=10010053 want=10010053
child first callback after new    signal=11 (Segmentation fault)
child current callback after new  rv=10010093
child current callback after new  exit=0
```

This is the decisive split:

- the process-lived generation-1 host trampoline remains stale after a forced-different reload and faults;
- the newly created generation-2 callback trampoline reaches the fresh guest code successfully.

A pin control in the same run keeps the guest DSO resident and preserves the retained callback:

```text
pin policy: guest DSO remains loaded
pinned first callback            rv=10063
```

## Interpretation

The host trampoline itself is process-owned executable memory, but two addresses inside its instance data can belong to unloadable guest mappings. The executed current-FEX matrix demonstrates that this ownership mismatch is sufficient to create a stale callable host-to-guest bridge after final guest-DSO unload.

This is the mirror image of the dynamic-PFN bridge investigated for Finding B:

```text
Finding B dynamic PFN: host/native key H -> guest invoker T
callback trampoline:    host trampoline -> guest unpacker U -> guest target G
```

Both classes require an ownership rule that prevents a process-lived bridge from retaining executable targets after the guest mapping generation disappears.

## Vulkan relevance and evidence boundary

The Vulkan guest thunk initialization creates host-to-guest trampolines for its X11 callback helpers. In those trampolines, the guest unpacker is instantiated in the Vulkan guest thunk image while the guest target comes from guest `libX11.so.6` symbols. A final Vulkan guest-thunk unload can therefore invalidate the unpacker side while the host-side trampoline cache remains alive.

The executed synthetic real-FEX fixture proves the generic FEX callback-trampoline lifetime failure class; it does **not** prove that this path caused the retained `vulkaninfo` teardown fault. The saved terminal guest RIP in that failure resolves near a generated `CallHostFunction<...>` body, which still aligns more directly with the dynamic host-PFN-to-guest-invoker path.

The remaining callback-side engineering question is therefore cleanup/revocation semantics, not whether stale callback trampolines can actually fault. Useful follow-ups are unload-time retirement by guest load generation, same-address ABA controls, and an in-flight callback/unload race.
