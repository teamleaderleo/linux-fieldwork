# Host-to-guest trampoline lifetime audit — 2026-08-14

Status: bounded source-level finding. This is an adjacent lifetime hazard, not a claim about the immediate cause of the retained Vulkan teardown crash.

Reviewed FEX product revision: `71afe476751deac24adabd1adb575fd2337b6e0a`.

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

## Why this is lifetime-sensitive

The host trampoline itself is process-owned executable memory, but two addresses inside its instance data can belong to unloadable guest mappings. If either the guest unpacker or guest target is unmapped while the host trampoline remains reachable, a later host callback can transition toward stale guest code.

This is the mirror image of the dynamic-PFN bridge investigated for Finding B:

```text
Finding B dynamic PFN: host/native key H -> guest invoker T
callback trampoline:    host trampoline -> guest unpacker U -> guest target G
```

Both classes require an ownership rule that prevents a process-lived bridge from retaining executable targets after the guest mapping generation disappears.

## Vulkan relevance

The Vulkan guest thunk initialization creates host-to-guest trampolines for its X11 callback helpers. In those trampolines, the guest unpacker is instantiated in the Vulkan guest thunk image while the guest target comes from guest `libX11.so.6` symbols. A final Vulkan guest-thunk unload can therefore invalidate the unpacker side while the host-side trampoline cache remains alive.

This does **not** supersede the stronger immediate-cause evidence for the retained teardown failure. The saved terminal guest RIP in that failure resolves near a generated `CallHostFunction<...>` body, which aligns more directly with the dynamic host-PFN-to-guest-invoker path. The callback-trampoline cache should remain a separate adjacent lifetime lane until a runtime discriminator identifies it in a real failing transfer.

## Best runtime discriminator

A minimal real-FEX test should:

1. create one host-to-guest trampoline whose `GuestUnpacker` is inside a disposable guest DSO;
2. invoke it once while the DSO is mapped;
3. unload the DSO and verify the unpacker range is no longer mapped;
4. invoke the already-retained host trampoline again;
5. compare current behavior against a candidate that retires or revokes trampolines by guest mapping generation before unmap.

Useful controls are same-address reload, different-address reload, unrelated guest DSO unload, and a process-lifetime unpacker control.

Until that test runs, retain this as a source-proven stale-address ownership hazard rather than a demonstrated runtime crash class.
